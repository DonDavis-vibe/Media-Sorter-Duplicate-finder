import os
import shutil
import hashlib
import time
from datetime import datetime
from PIL import Image, ExifTags
import imagehash
from pillow_heif import register_heif_opener
import tinytag
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import reverse_geocoder as rg

# Register HEIF opener to support HEIC/HEIF files
register_heif_opener()

SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic', '.heif', '.tiff', '.webp'}
SUPPORTED_VIDEOS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
SUPPORTED_AUDIO = {'.mp3', '.wav', '.aac', '.flac', '.m4a', '.ogg', '.wma', '.amr', '.opus'}

def get_lat_lon(exif_data):
    if not exif_data:
        return None, None
    if "GPSInfo" in exif_data:
        gps_info = exif_data["GPSInfo"]
        def convert_to_degrees(value):
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        
        try:
            if 2 in gps_info and 1 in gps_info and 4 in gps_info and 3 in gps_info:
                lat = convert_to_degrees(gps_info[2])
                if gps_info[1] != "N":
                    lat = 0 - lat
                lon = convert_to_degrees(gps_info[4])
                if gps_info[3] != "E":
                    lon = 0 - lon
                return lat, lon
        except Exception:
            pass
    return None, None

def get_location_name(lat, lon):
    if lat is None or lon is None:
        return None
    try:
        results = rg.search((lat, lon), mode=1)
        if results:
            res = results[0]
            city = res.get('name', '')
            country = res.get('cc', '')
            if city and country:
                return f"{country}_{city}"
            elif city:
                return city
            elif country:
                return country
    except Exception:
        pass
    return None

def get_file_date_and_location(file_path, is_image=True):
    date_dt = None
    location = None
    if is_image:
        try:
            with Image.open(file_path) as img:
                # _getexif() is reliable for getting the nested GPSInfo dict
                exif_full = getattr(img, '_getexif', lambda: None)()
                if exif_full:
                    exif_data = {}
                    for tag_id, value in exif_full.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[tag] = value
                    
                    if 'DateTimeOriginal' in exif_data:
                        date_str = exif_data['DateTimeOriginal']
                        try:
                            date_dt = datetime.strptime(str(date_str), '%Y:%m:%d %H:%M:%S')
                        except Exception:
                            pass
                            
                    lat, lon = get_lat_lon(exif_data)
                    location = get_location_name(lat, lon)
        except Exception:
            pass
    else:
        # Try Hachoir for video
        try:
            parser = createParser(file_path)
            if parser:
                with parser:
                    metadata = extractMetadata(parser)
                    if metadata and metadata.has('creation_date'):
                        date_dt = metadata.get('creation_date')
        except Exception:
            pass
            
        # Fallback to tinytag for audio or if hachoir fails
        if date_dt is None:
            try:
                tag = tinytag.TinyTag.get(file_path)
                year = tag.year
                if year:
                    if len(str(year)) == 4:
                        date_dt = datetime.strptime(str(year), "%Y")
            except Exception:
                pass
    
    # Fallback to file creation time
    if date_dt is None:
        try:
            stat = os.stat(file_path)
            date_dt = datetime.fromtimestamp(stat.st_ctime)
        except Exception:
            date_dt = datetime.now()
            
    return date_dt, location

def get_image_hash(file_path):
    try:
        with Image.open(file_path) as img:
            return imagehash.phash(img)
    except Exception:
        return None

def get_image_quality(file_path):
    try:
        with Image.open(file_path) as img:
            return img.size[0] * img.size[1]
    except Exception:
        return 0

def get_file_hash(file_path):
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def copy_file_with_progress(src, dst, callback=None, abort_flag=None):
    total_size = os.path.getsize(src)
    copied = 0
    start_time = time.time()
    last_update_time = 0
    
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        while True:
            if abort_flag and abort_flag():
                fdst.close()
                os.remove(dst)
                raise Exception("Copy aborted by user")
                
            buf = fsrc.read(1024 * 1024) # 1 MB chunks
            if not buf:
                break
            fdst.write(buf)
            copied += len(buf)
            
            now = time.time()
            if callback and (now - last_update_time > 0.1 or copied == total_size):
                last_update_time = now
                elapsed = now - start_time
                speed = copied / elapsed if elapsed > 0 else 0
                if speed > 1024 * 1024:
                    speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                elif speed > 1024:
                    speed_str = f"{speed / 1024:.1f} KB/s"
                else:
                    speed_str = f"{speed:.0f} B/s"
                
                percent = copied / total_size if total_size > 0 else 1.0
                callback(percent, speed_str)
                
    shutil.copystat(src, dst)

def process_images(source_dir, target_dir, sort_by_month=True, progress_callback=None, abort_flag=None, copy_unsupported=False, unified_tree=False, sort_by_location=False, location_format="Year/Month/Location", delete_originals=False, file_progress_callback=None, process_images_flag=True, process_videos_flag=True, process_audio_flag=True):
    seen_image_hashes = [] # List of dicts: {"hash": img_hash, "path": dest_path}
    seen_video_hashes = {}
    seen_audio_hashes = {}
    files_to_process = []
    
    stats = {
        'images_sorted': 0,
        'videos_sorted': 0,
        'audios_sorted': 0,
        'duplicates': 0,
        'skipped_files': 0,
        'unsupported_copied': 0,
        'unsupported_types': {},
        'failed': 0,
        'failed_files': [],
        'duplicate_pairs': []
    }
    
    # Gather files
    for root, _, files in os.walk(source_dir):
        for file in files:
            files_to_process.append(os.path.join(root, file))
                
    total_files = len(files_to_process)
    if total_files == 0:
        if progress_callback:
            progress_callback(1.0, "No media found.", "00:00:00", "00:00:00")
        return stats
        
    start_time = time.time()
        
    for index, file_path in enumerate(files_to_process):
        if abort_flag and abort_flag():
            if progress_callback:
                elapsed = time.time() - start_time
                elapsed_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
                progress_callback((index) / total_files, "Sorting Aborted.", elapsed_str, "N/A")
            break
            
        ext = os.path.splitext(file_path)[1].lower()
        is_video = ext in SUPPORTED_VIDEOS
        is_image = ext in SUPPORTED_IMAGES
        is_audio = ext in SUPPORTED_AUDIO
        
        if not process_images_flag:
            is_image = False
        if not process_videos_flag:
            is_video = False
        if not process_audio_flag:
            is_audio = False
            
        filename = os.path.basename(file_path)
        
        if not is_video and not is_image and not is_audio:
            ext_name = ext if ext else "no_extension"
            stats['unsupported_types'][ext_name] = stats['unsupported_types'].get(ext_name, 0) + 1
            
            if copy_unsupported:
                dest_folder = os.path.join(target_dir, "Unsupported")
                os.makedirs(dest_folder, exist_ok=True)
                dest_path = os.path.join(dest_folder, filename)
                
                counter = 1
                name, ext_original = os.path.splitext(filename)
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_folder, f"{name}_{counter}{ext_original}")
                    counter += 1
                
                try:
                    copy_file_with_progress(file_path, dest_path, file_progress_callback, abort_flag)
                    stats['unsupported_copied'] += 1
                    if delete_originals:
                        os.remove(file_path)
                except Exception as e:
                    stats['failed'] += 1
                    stats['failed_files'].append(f"{filename}: {str(e)}")
            else:
                stats['skipped_files'] += 1
        else:
            is_duplicate = False
            original_info = None
            is_better = False
            f_hash = None
            img_hash = None
            pixels = 0
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            if is_video:
                f_hash = get_file_hash(file_path)
                if f_hash is not None and f_hash in seen_video_hashes:
                    is_duplicate = True
                    original_info = seen_video_hashes[f_hash]
                    is_better = file_size > original_info["size"]
            elif is_audio:
                f_hash = get_file_hash(file_path)
                if f_hash is not None and f_hash in seen_audio_hashes:
                    is_duplicate = True
                    original_info = seen_audio_hashes[f_hash]
                    is_better = file_size > original_info["size"]
            else:
                img_hash = get_image_hash(file_path)
                pixels = get_image_quality(file_path)
                if img_hash is not None:
                    for seen in seen_image_hashes:
                        if (img_hash - seen["hash"]) <= 6:
                            is_duplicate = True
                            original_info = seen
                            is_better = pixels > original_info["pixels"] or (pixels == original_info["pixels"] and file_size > original_info["size"])
                            break
                    
            date_dt, location = get_file_date_and_location(file_path, is_image=is_image)
            year_str = str(date_dt.year)
            month_str = f"{date_dt.month:02d}_{date_dt.strftime('%B')}"
            
            if is_duplicate and not is_better:
                dest_folder = os.path.join(target_dir, "Duplicates")
                stats['duplicates'] += 1
            else:
                if unified_tree:
                    base_folder = target_dir
                else:
                    if is_video:
                        base_folder = os.path.join(target_dir, "Videos")
                    elif is_audio:
                        base_folder = os.path.join(target_dir, "Audio")
                    else:
                        base_folder = target_dir
                
                path_parts = [base_folder]
                if sort_by_location and location:
                    if location_format == "Location/Year/Month":
                        path_parts.append(location)
                        path_parts.append(year_str)
                        if sort_by_month:
                            path_parts.append(month_str)
                    else:
                        path_parts.append(year_str)
                        if sort_by_month:
                            path_parts.append(month_str)
                        path_parts.append(location)
                else:
                    path_parts.append(year_str)
                    if sort_by_month:
                        path_parts.append(month_str)
                        
                dest_folder = os.path.join(*path_parts)
                    
            os.makedirs(dest_folder, exist_ok=True)
            
            dest_path = os.path.join(dest_folder, filename)
            
            counter = 1
            name, ext_original = os.path.splitext(filename)
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_folder, f"{name}_{counter}{ext_original}")
                counter += 1
                
            try:
                copy_file_with_progress(file_path, dest_path, file_progress_callback, abort_flag)
                if is_duplicate:
                    if is_better:
                        dup_dest_folder = os.path.join(target_dir, "Duplicates")
                        os.makedirs(dup_dest_folder, exist_ok=True)
                        old_path = original_info["path"]
                        
                        if os.path.exists(old_path):
                            old_base = os.path.basename(old_path)
                            old_name, old_ext = os.path.splitext(old_base)
                            old_dup_path = os.path.join(dup_dest_folder, old_base)
                            old_counter = 1
                            while os.path.exists(old_dup_path):
                                old_dup_path = os.path.join(dup_dest_folder, f"{old_name}_{old_counter}{old_ext}")
                                old_counter += 1
                            
                            shutil.move(old_path, old_dup_path)
                            stats['duplicate_pairs'].append((dest_path, old_dup_path))
                            
                            for i, (orig, dup) in enumerate(stats['duplicate_pairs']):
                                if orig == old_path:
                                    stats['duplicate_pairs'][i] = (dest_path, dup)
                        
                        original_info["path"] = dest_path
                        original_info["size"] = file_size
                        if is_image:
                            original_info["pixels"] = pixels
                    else:
                        stats['duplicate_pairs'].append((original_info["path"], dest_path))
                else:
                    if is_video:
                        stats['videos_sorted'] += 1
                        if f_hash is not None:
                            seen_video_hashes[f_hash] = {"path": dest_path, "size": file_size}
                    elif is_audio:
                        stats['audios_sorted'] += 1
                        if f_hash is not None:
                            seen_audio_hashes[f_hash] = {"path": dest_path, "size": file_size}
                    else:
                        stats['images_sorted'] += 1
                        if img_hash is not None:
                            seen_image_hashes.append({"hash": img_hash, "path": dest_path, "pixels": pixels, "size": file_size})
                if delete_originals:
                    os.remove(file_path)
            except Exception as e:
                stats['failed'] += 1
                stats['failed_files'].append(f"{filename}: {str(e)}")
            
        if progress_callback:
            progress = (index + 1) / total_files
            elapsed = time.time() - start_time
            if index > 0:
                time_per_file = elapsed / (index + 1)
                eta = time_per_file * (total_files - (index + 1))
                eta_str = time.strftime('%H:%M:%S', time.gmtime(eta))
            else:
                eta_str = "Calculating..."
            elapsed_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
            
            progress_callback(progress, f"Processed {index + 1}/{total_files}: {filename}", elapsed_str, eta_str)
            
    if not (abort_flag and abort_flag()) and progress_callback:
        total_elapsed = time.time() - start_time
        elapsed_str = time.strftime('%H:%M:%S', time.gmtime(total_elapsed))
        progress_callback(1.0, "Finished processing all media!", elapsed_str, "00:00:00")
        
    return stats
