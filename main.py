import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import multiprocessing
from PIL import Image
from sorter import process_images

class DuplicateManagerWindow(ctk.CTkToplevel):
    def __init__(self, master, duplicate_pairs):
        super().__init__(master)
        self.title("Duplicate Manager")
        self.geometry("800x600")
        self.duplicate_pairs = duplicate_pairs
        
        self.title_label = ctk.CTkLabel(self, text="Review Duplicates", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.vars = []
        
        self.loading_label = ctk.CTkLabel(self.scroll_frame, text="Loading thumbnails...")
        self.loading_label.pack(pady=20)
        
        self.after(100, self.load_items)
        
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)
        
        self.delete_btn = ctk.CTkButton(self.btn_frame, text="Delete Selected", fg_color="#C62828", hover_color="#B71C1C", command=self.delete_selected)
        self.delete_btn.pack(side="left", padx=10)
        
        self.close_btn = ctk.CTkButton(self.btn_frame, text="Done", command=self.destroy)
        self.close_btn.pack(side="left", padx=10)

    def load_items(self):
        self.loading_label.destroy()
        for orig, dup in self.duplicate_pairs:
            row_frame = ctk.CTkFrame(self.scroll_frame)
            row_frame.pack(fill="x", pady=5, padx=5)
            
            orig_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            orig_frame.pack(side="left", fill="both", expand=True, padx=5)
            ctk.CTkLabel(orig_frame, text="Original Kept:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(orig_frame, text=os.path.basename(orig)).pack(anchor="w")
            self.add_thumbnail(orig_frame, orig)
            
            dup_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            dup_frame.pack(side="left", fill="both", expand=True, padx=5)
            
            var = ctk.BooleanVar(value=True)
            self.vars.append((var, dup, row_frame))
            
            cb = ctk.CTkCheckBox(dup_frame, text="Delete Duplicate", variable=var, text_color="#C62828")
            cb.pack(anchor="w", pady=(0, 5))
            ctk.CTkLabel(dup_frame, text=os.path.basename(dup)).pack(anchor="w")
            self.add_thumbnail(dup_frame, dup)

    def add_thumbnail(self, parent, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}:
            try:
                img = Image.open(path)
                img.thumbnail((150, 150))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                lbl = ctk.CTkLabel(parent, image=ctk_img, text="")
                lbl.image = ctk_img
                lbl.pack(anchor="w", pady=5)
            except Exception:
                ctk.CTkLabel(parent, text="[Image Error]").pack(anchor="w")
        else:
            try:
                size_mb = os.path.getsize(path) / (1024 * 1024)
                ctk.CTkLabel(parent, text=f"Size: {size_mb:.2f} MB").pack(anchor="w")
            except Exception:
                ctk.CTkLabel(parent, text="[File Error]").pack(anchor="w")

    def delete_selected(self):
        deleted_count = 0
        for var, dup_path, frame in list(self.vars):
            if var.get():
                try:
                    os.remove(dup_path)
                    frame.destroy()
                    self.vars.remove((var, dup_path, frame))
                    deleted_count += 1
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete {os.path.basename(dup_path)}: {e}")
        messagebox.showinfo("Deleted", f"Successfully deleted {deleted_count} duplicates.")

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Image Sorter & Duplicate Finder")
        self.geometry("600x550")
        
        self.source_dir = ""
        self.target_dir = ""
        self.abort_requested = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # Title
        self.title_label = ctk.CTkLabel(self, text="Media Sorter", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(20, 10))
        
        # Source Selection
        self.src_frame = ctk.CTkFrame(self)
        self.src_frame.pack(pady=10, padx=20, fill="x")
        
        self.src_btn = ctk.CTkButton(self.src_frame, text="Select Source Folder", command=self.select_source)
        self.src_btn.pack(side="left", padx=10, pady=10)
        
        self.src_label = ctk.CTkLabel(self.src_frame, text="No folder selected", text_color="gray")
        self.src_label.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        # Target Selection
        self.tgt_frame = ctk.CTkFrame(self)
        self.tgt_frame.pack(pady=10, padx=20, fill="x")
        
        self.tgt_btn = ctk.CTkButton(self.tgt_frame, text="Select Destination Folder", command=self.select_target)
        self.tgt_btn.pack(side="left", padx=10, pady=10)
        
        self.tgt_label = ctk.CTkLabel(self.tgt_frame, text="No folder selected", text_color="gray")
        self.tgt_label.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        # Media Filter
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.pack(pady=5, padx=20, fill="x")
        
        self.media_type_label = ctk.CTkLabel(self.filter_frame, text="Process Types:")
        self.media_type_label.pack(side="left", padx=10, pady=10)
        
        self.process_images_var = ctk.BooleanVar(value=True)
        self.process_images_cb = ctk.CTkCheckBox(self.filter_frame, text="Images", variable=self.process_images_var)
        self.process_images_cb.pack(side="left", padx=10, pady=10)
        
        self.process_videos_var = ctk.BooleanVar(value=True)
        self.process_videos_cb = ctk.CTkCheckBox(self.filter_frame, text="Videos", variable=self.process_videos_var)
        self.process_videos_cb.pack(side="left", padx=10, pady=10)
        
        self.process_audio_var = ctk.BooleanVar(value=True)
        self.process_audio_cb = ctk.CTkCheckBox(self.filter_frame, text="Audio", variable=self.process_audio_var)
        self.process_audio_cb.pack(side="left", padx=10, pady=10)
        
        # Sorting Options
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, padx=20, fill="x")
        
        self.sort_label = ctk.CTkLabel(self.options_frame, text="Sort by:")
        self.sort_label.pack(side="left", padx=10, pady=10)
        
        self.sort_var = ctk.StringVar(value="Year and Month")
        self.sort_dropdown = ctk.CTkOptionMenu(self.options_frame, values=["Year and Month", "Year Only"], variable=self.sort_var)
        self.sort_dropdown.pack(side="left", padx=10, pady=10)
        
        self.save_stats_var = ctk.BooleanVar(value=True)
        self.save_stats_cb = ctk.CTkCheckBox(self.options_frame, text="Save Stats Log", variable=self.save_stats_var)
        self.save_stats_cb.pack(side="left", padx=10, pady=10)
        
        self.copy_unsupported_var = ctk.BooleanVar(value=False)
        self.copy_unsupported_cb = ctk.CTkCheckBox(self.options_frame, text="Copy Unsupported", variable=self.copy_unsupported_var)
        self.copy_unsupported_cb.pack(side="left", padx=10, pady=10)
        
        self.delete_originals_var = ctk.BooleanVar(value=False)
        self.delete_originals_cb = ctk.CTkCheckBox(self.options_frame, text="Move Files (Delete Originals)", variable=self.delete_originals_var, text_color="#C62828")
        self.delete_originals_cb.pack(side="left", padx=10, pady=10)
        
        # Advanced Options
        self.adv_options_frame = ctk.CTkFrame(self)
        self.adv_options_frame.pack(pady=5, padx=20, fill="x")
        
        self.unified_tree_var = ctk.BooleanVar(value=False)
        self.unified_tree_cb = ctk.CTkCheckBox(self.adv_options_frame, text="Unified Media Tree", variable=self.unified_tree_var)
        self.unified_tree_cb.pack(side="left", padx=10, pady=10)
        
        self.sort_location_var = ctk.BooleanVar(value=False)
        self.sort_location_cb = ctk.CTkCheckBox(self.adv_options_frame, text="Sort by Location (GPS)", variable=self.sort_location_var)
        self.sort_location_cb.pack(side="left", padx=10, pady=10)
        
        self.loc_format_var = ctk.StringVar(value="Year/Month/Location")
        self.loc_format_1 = ctk.CTkRadioButton(self.adv_options_frame, text="Year/Location", variable=self.loc_format_var, value="Year/Month/Location")
        self.loc_format_2 = ctk.CTkRadioButton(self.adv_options_frame, text="Location/Year", variable=self.loc_format_var, value="Location/Year/Month")
        self.loc_format_1.pack(side="left", padx=5)
        self.loc_format_2.pack(side="left", padx=5)
        
        # Action Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=(20, 10))
        
        self.run_btn = ctk.CTkButton(self.btn_frame, text="Start Sorting", font=ctk.CTkFont(weight="bold"), height=40, command=self.start_sorting)
        self.run_btn.pack(side="left", padx=10)
        
        self.abort_btn = ctk.CTkButton(self.btn_frame, text="Abort", font=ctk.CTkFont(weight="bold"), height=40, fg_color="#C62828", hover_color="#B71C1C", state="disabled", command=self.request_abort)
        self.abort_btn.pack(side="left", padx=10)
        
        # Progress
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(pady=(10, 5), padx=20, fill="x")
        self.progress_bar.set(0)
        
        self.timer_label = ctk.CTkLabel(self, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self.timer_label.pack(pady=(0, 5))
        
        self.file_progress_bar = ctk.CTkProgressBar(self)
        self.file_progress_bar.pack(pady=(5, 5), padx=20, fill="x")
        self.file_progress_bar.set(0)
        
        self.file_timer_label = ctk.CTkLabel(self, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self.file_timer_label.pack(pady=(0, 5))
        
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.pack(pady=(0, 20))
        
    def select_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_dir = folder
            self.src_label.configure(text=folder, text_color=("black", "white"))
            
    def select_target(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.target_dir = folder
            self.tgt_label.configure(text=folder, text_color=("black", "white"))
            
    def request_abort(self):
        self.abort_requested = True
        self.status_label.configure(text="Aborting... Please wait.")
        self.abort_btn.configure(state="disabled")
        
    def update_progress(self, progress, status_text, elapsed_str="", eta_str=""):
        self.after(0, self._do_update_progress, progress, status_text, elapsed_str, eta_str)
        
    def _do_update_progress(self, progress, status_text, elapsed_str, eta_str):
        self.progress_bar.set(progress)
        self.status_label.configure(text=status_text)
        if elapsed_str or eta_str:
            self.timer_label.configure(text=f"Elapsed: {elapsed_str} | ETA: {eta_str}")
        else:
            self.timer_label.configure(text="")
            
    def update_file_progress(self, percent, speed_str):
        self.after(0, self._do_update_file_progress, percent, speed_str)
        
    def _do_update_file_progress(self, percent, speed_str):
        self.file_progress_bar.set(percent)
        if speed_str:
            self.file_timer_label.configure(text=f"File Progress: {int(percent * 100)}% | Speed: {speed_str}")
        else:
            self.file_timer_label.configure(text="")
        
    def show_summary(self, stats, was_aborted):
        title = "Process Aborted" if was_aborted else "Success"
        msg = f"Sorting {'aborted' if was_aborted else 'completed'}!\n\n"
        
        images = stats.get('images_sorted', 0)
        videos = stats.get('videos_sorted', 0)
        audios = stats.get('audios_sorted', 0)
        total_sorted = images + videos + audios
        
        msg += f"Total Files Sorted: {total_sorted}\n"
        msg += f"  - Images Sorted: {images}\n"
        msg += f"  - Videos Sorted: {videos}\n"
        msg += f"  - Audios Sorted: {audios}\n"
        msg += f"Duplicates Found & Segregated: {stats.get('duplicates', 0)}\n"
        msg += f"Unsupported Files Skipped: {stats.get('skipped_files', 0)}\n"
        msg += f"Unsupported Files Copied: {stats.get('unsupported_copied', 0)}\n"
        
        unsupported_types = stats.get('unsupported_types', {})
        if unsupported_types:
            msg += "  (Breakdown: " + ", ".join(f"{ext}: {count}" for ext, count in unsupported_types.items()) + ")\n"
            
        msg += f"Errors: {stats.get('failed', 0)}"
        
        if stats.get('failed_files'):
            msg += "\n\nFailed Files:\n"
            for f in stats['failed_files'][:5]:
                msg += f"- {f}\n"
            if len(stats['failed_files']) > 5:
                msg += f"...and {len(stats['failed_files']) - 5} more."
                
        if self.save_stats_var.get() and self.target_dir:
            try:
                log_path = os.path.join(self.target_dir, "sort_summary.txt")
                with open(log_path, "w") as f:
                    f.write(msg)
                msg += f"\n\n(Stats saved to {log_path})"
            except Exception as e:
                msg += f"\n\n(Failed to save stats: {e})"
                
        messagebox.showinfo(title, msg)
        
        if stats.get('duplicate_pairs'):
            DuplicateManagerWindow(self, stats['duplicate_pairs'])
        
    def sorting_thread(self, sort_by_month, copy_unsupported, unified_tree, sort_by_location, location_format, delete_originals, process_images_flag, process_videos_flag, process_audio_flag):
        try:
            stats = process_images(
                self.source_dir, 
                self.target_dir, 
                sort_by_month=sort_by_month, 
                progress_callback=self.update_progress,
                abort_flag=lambda: self.abort_requested,
                copy_unsupported=copy_unsupported,
                unified_tree=unified_tree,
                sort_by_location=sort_by_location,
                location_format=location_format,
                delete_originals=delete_originals,
                file_progress_callback=self.update_file_progress,
                process_images_flag=process_images_flag,
                process_videos_flag=process_videos_flag,
                process_audio_flag=process_audio_flag
            )
            
            # Use after() to show messagebox on main thread
            self.after(0, self.show_summary, stats, self.abort_requested)
            
        except Exception as e:
            self.after(0, messagebox.showerror, "Error", f"An error occurred: {str(e)}")
        finally:
            self.after(0, self.reset_ui)
            
    def reset_ui(self):
        self.run_btn.configure(state="normal")
        self.abort_btn.configure(state="disabled")
        self.abort_requested = False
        
    def start_sorting(self):
        if not self.source_dir or not os.path.exists(self.source_dir):
            messagebox.showwarning("Missing Information", "Please select a valid source folder.")
            return
            
        if not self.target_dir or not os.path.exists(self.target_dir):
            messagebox.showwarning("Missing Information", "Please select a valid destination folder.")
            return
            
        if self.source_dir == self.target_dir:
            messagebox.showwarning("Invalid Selection", "Source and destination folders cannot be the same.")
            return
            
        sort_by_month = self.sort_var.get() == "Year and Month"
        copy_unsup = self.copy_unsupported_var.get()
        unified_tree = self.unified_tree_var.get()
        sort_by_location = self.sort_location_var.get()
        location_format = self.loc_format_var.get()
        delete_originals = self.delete_originals_var.get()
        
        proc_img = self.process_images_var.get()
        proc_vid = self.process_videos_var.get()
        proc_aud = self.process_audio_var.get()
        
        if not (proc_img or proc_vid or proc_aud):
            messagebox.showwarning("Missing Information", "Please select at least one media type to process.")
            return
            
        self.abort_requested = False
        self.run_btn.configure(state="disabled")
        self.abort_btn.configure(state="normal")
        
        self.progress_bar.set(0)
        self.file_progress_bar.set(0)
        self.file_timer_label.configure(text="")
        self.status_label.configure(text="Processing...")
        
        # Run in separate thread to keep UI responsive
        threading.Thread(target=self.sorting_thread, args=(sort_by_month, copy_unsup, unified_tree, sort_by_location, location_format, delete_originals, proc_img, proc_vid, proc_aud), daemon=True).start()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
