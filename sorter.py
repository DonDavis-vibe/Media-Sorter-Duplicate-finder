import os
import shutil
import hashlib
import time
import logging
from datetime import datetime
from PIL import Image, ExifTags
import imagehash
from pillow_heif import register_heif_opener
import tinytag
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import reverse_geocoder as rg
from concurrent.futures import ThreadPoolExecutor, as_completed

# Register HEIF opener to support HEIC/HEIF files
register_heif_opener()

# Suppress noisy warnings from hachoir and tinytag parsers
logging.getLogger('hachoir').setLevel(logging.CRITICAL)
logging.getLogger('tinytag').setLevel(logging.CRITICAL)

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

def _compute_single_hash(args):
    """Worker function for parallel hash computation. Used by ThreadPoolExecutor."""
    file_path, ext, process_images_flag, process_videos_flag, process_audio_flag = args
    is_image = ext in SUPPORTED_IMAGES and process_images_flag
    is_video = ext in SUPPORTED_VIDEOS and process_videos_flag
    is_audio = ext in SUPPORTED_AUDIO and process_audio_flag
    
    result = {'path': file_path, 'img_hash': None, 'pixels': 0, 'f_hash': None}
    try:
        if is_image:
            result['img_hash'] = get_image_hash(file_path)
            result['pixels'] = get_image_quality(file_path)
        elif is_video or is_audio:
            result['f_hash'] = get_file_hash(file_path)
    except Exception:
        pass
    return result

def process_images(source_dir, target_dir, sort_by_month=True, progress_callback=None,
                   abort_flag=None, copy_unsupported=False, unified_tree=False,
                   sort_by_location=False, location_format="Year/Month/Location",
                   delete_originals=False, file_progress_callback=None,
                   process_images_flag=True, process_videos_flag=True, process_audio_flag=True,
                   log_callback=None, dry_run=False, use_multithreading=False):

    seen_image_hashes = []  # List of dicts: {"hash": img_hash, "path": dest_path, ...}
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
        'duplicate_pairs': [],
        'planned_operations': [],  # Populated only in dry_run mode
        'dry_run': dry_run,
    }

    def log(msg):
        if log_callback:
            log_callback(msg)

    prefix = "[PREVIEW] " if dry_run else ""
    log(f"{prefix}Scanning source directory: {source_dir}")

    # Gather all files recursively
    for root, _, files in os.walk(source_dir):
        for file in files:
            files_to_process.append(os.path.join(root, file))

    total_files = len(files_to_process)
    if total_files == 0:
        if progress_callback:
            progress_callback(1.0, "No media found.", "00:00:00", "00:00:00")
        log("No media files found to process.")
        return stats

    start_time = time.time()
    log(f"Found {total_files} files to process.")

    # --- Optional: Pre-compute all hashes in parallel ---
    precomputed_hashes = {}
    if use_multithreading and not dry_run:
        log("⚡ Multi-threading enabled — pre-computing hashes in parallel...")
        worker_args = [
            (fp, os.path.splitext(fp)[1].lower(),
             process_images_flag, process_videos_flag, process_audio_flag)
            for fp in files_to_process
        ]
        max_workers = min(8, (os.cpu_count() or 4))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_compute_single_hash, args): args[0] for args in worker_args}
            done_count = 0
            for future in as_completed(futures):
                if abort_flag and abort_flag():
                    break
                try:
                    result = future.result()
                    precomputed_hashes[result['path']] = result
                except Exception:
                    pass
                done_count += 1
                # Report hash progress as 0–30% of total progress bar
                if progress_callback and done_count % max(1, total_files // 20) == 0:
                    frac = done_count / total_files * 0.3
                    progress_callback(frac, f"Hashing {done_count}/{total_files} files...", "", "")
        log(f"Hash pre-computation complete ({max_workers} threads).")

    # --- Main processing loop ---
    for index, file_path in enumerate(files_to_process):
        if abort_flag and abort_flag():
            if progress_callback:
                elapsed = time.time() - start_time
                elapsed_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
                progress_callback(index / total_files, "Aborted.", elapsed_str, "N/A")
            log("Process aborted by user.")
            break

        ext = os.path.splitext(file_path)[1].lower()
        is_video = ext in SUPPORTED_VIDEOS
        is_image = ext in SUPPORTED_IMAGES
        is_audio = ext in SUPPORTED_AUDIO

        if not process_images_flag: is_image = False
        if not process_videos_flag: is_video = False
        if not process_audio_flag:  is_audio = False

        filename = os.path.basename(file_path)

        # ── Unsupported file ──────────────────────────────────────────────────
        if not is_video and not is_image and not is_audio:
            ext_name = ext if ext else "no_extension"
            stats['unsupported_types'][ext_name] = stats['unsupported_types'].get(ext_name, 0) + 1

            if copy_unsupported:
                dest_folder = os.path.join(target_dir, "Unsupported")
                dest_path   = os.path.join(dest_folder, filename)
                if dry_run:
                    log(f"[PREVIEW] Would copy: {filename} → Unsupported/")
                    stats['unsupported_copied'] += 1
                    stats['planned_operations'].append({
                        'filename': filename, 'source': file_path,
                        'action': 'copy_unsupported', 'dest_label': 'Unsupported/',
                        'type': 'unsupported',
                    })
                else:
                    os.makedirs(dest_folder, exist_ok=True)
                    counter = 1
                    name, ext_orig = os.path.splitext(filename)
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(dest_folder, f"{name}_{counter}{ext_orig}")
                        counter += 1
                    try:
                        log(f"Copying unsupported: {filename} → Unsupported/")
                        copy_file_with_progress(file_path, dest_path, file_progress_callback, abort_flag)
                        stats['unsupported_copied'] += 1
                        if delete_originals:
                            os.remove(file_path)
                    except Exception as e:
                        stats['failed'] += 1
                        stats['failed_files'].append(f"{filename}: {e}")
                        log(f"Error copying {filename}: {e}")
            else:
                stats['skipped_files'] += 1
                if dry_run:
                    stats['planned_operations'].append({
                        'filename': filename, 'source': file_path,
                        'action': 'skip', 'dest_label': '— (Skipped)',
                        'type': 'unsupported',
                    })
                else:
                    log(f"Skipped unsupported: {filename}")

        # ── Supported media file ──────────────────────────────────────────────
        else:
            is_duplicate = False
            original_info = None
            is_better = False
            f_hash = None
            img_hash = None
            pixels = 0
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            # Use pre-computed hash if available, else compute on the spot
            precomp = precomputed_hashes.get(file_path)

            if is_video:
                f_hash = precomp['f_hash'] if precomp else get_file_hash(file_path)
                if f_hash and f_hash in seen_video_hashes:
                    is_duplicate = True
                    original_info = seen_video_hashes[f_hash]
                    is_better = file_size > original_info["size"]
            elif is_audio:
                f_hash = precomp['f_hash'] if precomp else get_file_hash(file_path)
                if f_hash and f_hash in seen_audio_hashes:
                    is_duplicate = True
                    original_info = seen_audio_hashes[f_hash]
                    is_better = file_size > original_info["size"]
            else:  # image
                img_hash = precomp['img_hash'] if precomp else get_image_hash(file_path)
                pixels   = precomp['pixels']   if precomp else get_image_quality(file_path)
                if img_hash is not None:
                    for seen in seen_image_hashes:
                        if (img_hash - seen["hash"]) <= 6:
                            is_duplicate = True
                            original_info = seen
                            is_better = pixels > original_info["pixels"] or (
                                pixels == original_info["pixels"] and file_size > original_info["size"])
                            break

            date_dt, location = get_file_date_and_location(file_path, is_image=is_image)
            year_str  = str(date_dt.year)
            month_str = f"{date_dt.month:02d}_{date_dt.strftime('%B')}"

            # Determine destination folder
            if is_duplicate and not is_better:
                dest_folder = os.path.join(target_dir, "Duplicates")
                action      = 'duplicate'
                dest_label  = 'Duplicates/'
                stats['duplicates'] += 1
                if not dry_run:
                    log(f"Found lower-quality duplicate: {filename} → Duplicates/")
            else:
                if unified_tree:
                    base_folder = target_dir
                else:
                    if is_video:      base_folder = os.path.join(target_dir, "Videos")
                    elif is_audio:    base_folder = os.path.join(target_dir, "Audio")
                    else:             base_folder = target_dir

                path_parts = [base_folder]
                if sort_by_location and location:
                    if location_format == "Location/Year/Month":
                        path_parts.extend([location, year_str])
                        if sort_by_month: path_parts.append(month_str)
                    else:
                        path_parts.append(year_str)
                        if sort_by_month: path_parts.append(month_str)
                        path_parts.append(location)
                else:
                    path_parts.append(year_str)
                    if sort_by_month: path_parts.append(month_str)

                dest_folder = os.path.join(*path_parts)
                action      = 'sort'
                dest_label  = os.path.relpath(dest_folder, target_dir)

            dest_path  = os.path.join(dest_folder, filename)
            media_type = 'image' if is_image else ('video' if is_video else 'audio')

            # ── DRY RUN: record operation, don't touch the filesystem ────────
            if dry_run:
                stats['planned_operations'].append({
                    'filename': filename, 'source': file_path,
                    'action': action, 'dest_label': dest_label,
                    'type': media_type, 'date': date_dt.strftime('%Y-%m-%d'),
                })
                # Still update hash tables so duplicate detection is accurate
                if action != 'duplicate':
                    if is_video and f_hash:
                        seen_video_hashes[f_hash] = {"path": dest_path, "size": file_size}
                    elif is_audio and f_hash:
                        seen_audio_hashes[f_hash] = {"path": dest_path, "size": file_size}
                    elif is_image and img_hash:
                        seen_image_hashes.append({"hash": img_hash, "path": dest_path, "pixels": pixels, "size": file_size})
                    if is_image:  stats['images_sorted'] += 1
                    elif is_video: stats['videos_sorted'] += 1
                    elif is_audio: stats['audios_sorted'] += 1

            # ── REAL SORT: copy/move files ───────────────────────────────────
            else:
                os.makedirs(dest_folder, exist_ok=True)
                counter = 1
                name, ext_orig = os.path.splitext(filename)
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_folder, f"{name}_{counter}{ext_orig}")
                    counter += 1

                try:
                    copy_file_with_progress(file_path, dest_path, file_progress_callback, abort_flag)

                    if is_duplicate:
                        if is_better:
                            log(f"Found higher-quality duplicate: {filename}. Replacing previous original.")
                            dup_dest_folder = os.path.join(target_dir, "Duplicates")
                            os.makedirs(dup_dest_folder, exist_ok=True)
                            old_path = original_info["path"]
                            if os.path.exists(old_path):
                                old_base = os.path.basename(old_path)
                                old_name, old_ext = os.path.splitext(old_base)
                                old_dup_path = os.path.join(dup_dest_folder, old_base)
                                old_c = 1
                                while os.path.exists(old_dup_path):
                                    old_dup_path = os.path.join(dup_dest_folder, f"{old_name}_{old_c}{old_ext}")
                                    old_c += 1
                                shutil.move(old_path, old_dup_path)
                                stats['duplicate_pairs'].append((dest_path, old_dup_path))
                                for i, (orig, dup) in enumerate(stats['duplicate_pairs']):
                                    if orig == old_path:
                                        stats['duplicate_pairs'][i] = (dest_path, dup)
                            original_info["path"] = dest_path
                            original_info["size"] = file_size
                            if is_image: original_info["pixels"] = pixels
                        else:
                            stats['duplicate_pairs'].append((original_info["path"], dest_path))
                    else:
                        log(f"Sorted: {filename} → {os.path.relpath(dest_path, target_dir)}")
                        if is_video:
                            stats['videos_sorted'] += 1
                            if f_hash: seen_video_hashes[f_hash] = {"path": dest_path, "size": file_size}
                        elif is_audio:
                            stats['audios_sorted'] += 1
                            if f_hash: seen_audio_hashes[f_hash] = {"path": dest_path, "size": file_size}
                        else:
                            stats['images_sorted'] += 1
                            if img_hash: seen_image_hashes.append({"hash": img_hash, "path": dest_path, "pixels": pixels, "size": file_size})

                    if delete_originals:
                        os.remove(file_path)
                        log(f"Deleted original: {filename}")

                except Exception as e:
                    stats['failed'] += 1
                    stats['failed_files'].append(f"{filename}: {e}")
                    log(f"Error processing {filename}: {e}")

        # ── Progress update ───────────────────────────────────────────────────
        if progress_callback:
            # If multithreading was used, hashing occupied 0–30%, so main loop is 30–100%
            base = 0.3 if (use_multithreading and not dry_run and precomputed_hashes) else 0.0
            scale = 1.0 - base
            progress = base + ((index + 1) / total_files) * scale
            elapsed = time.time() - start_time
            if index > 0:
                time_per_file = elapsed / (index + 1)
                eta = time_per_file * (total_files - (index + 1))
                eta_str = time.strftime('%H:%M:%S', time.gmtime(eta))
            else:
                eta_str = "Calculating..."
            elapsed_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
            progress_callback(progress, f"Processed {index + 1}/{total_files}: {filename}", elapsed_str, eta_str)

    # ── Completion ────────────────────────────────────────────────────────────
    if not (abort_flag and abort_flag()) and progress_callback:
        total_elapsed = time.time() - start_time
        elapsed_str = time.strftime('%H:%M:%S', time.gmtime(total_elapsed))
        if dry_run:
            progress_callback(1.0, "Preview complete!", elapsed_str, "00:00:00")
            log(f"[PREVIEW] Done — {len(stats['planned_operations'])} operations planned.")
        else:
            progress_callback(1.0, "Finished processing all media!", elapsed_str, "00:00:00")
            log("Process completed successfully.")

    return stats
