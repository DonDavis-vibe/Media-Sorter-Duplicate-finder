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
        self.geometry("850x650")
        self.duplicate_pairs = duplicate_pairs
        
        self.title_label = ctk.CTkLabel(self, text="Review Duplicates", font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.pack(pady=15)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.vars = []
        
        self.loading_label = ctk.CTkLabel(self.scroll_frame, text="Processing thumbnails in background...", font=ctk.CTkFont(slant="italic"))
        self.loading_label.pack(pady=20)
        
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=15)
        
        self.delete_btn = ctk.CTkButton(self.btn_frame, text="Delete Selected", font=ctk.CTkFont(weight="bold"), fg_color="#C62828", hover_color="#B71C1C", command=self.delete_selected)
        self.delete_btn.pack(side="left", padx=10)
        
        self.close_btn = ctk.CTkButton(self.btn_frame, text="Done", command=self.destroy)
        self.close_btn.pack(side="left", padx=10)
        
        # Start background thread for thumbnail generation
        threading.Thread(target=self.load_items_bg, daemon=True).start()

    def load_items_bg(self):
        for orig, dup in self.duplicate_pairs:
            # Generate thumbnails in background
            orig_img = self.get_thumbnail_image(orig)
            dup_img = self.get_thumbnail_image(dup)
            
            # Send UI update to main thread
            self.after(0, self.add_row_ui, orig, dup, orig_img, dup_img)
            
        self.after(0, self.finish_loading_ui)

    def finish_loading_ui(self):
        try:
            self.loading_label.destroy()
        except:
            pass

    def add_row_ui(self, orig, dup, orig_img_obj, dup_img_obj):
        row_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        row_frame.pack(fill="x", pady=8, padx=5)
        
        # Original File Side
        orig_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        orig_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(orig_frame, text="Original Kept:", font=ctk.CTkFont(weight="bold"), text_color="#4CAF50").pack(anchor="w")
        ctk.CTkLabel(orig_frame, text=os.path.basename(orig), font=ctk.CTkFont(size=12)).pack(anchor="w")
        
        if isinstance(orig_img_obj, ctk.CTkImage):
            lbl = ctk.CTkLabel(orig_frame, image=orig_img_obj, text="")
            lbl.image = orig_img_obj
            lbl.pack(anchor="w", pady=5)
        else:
            ctk.CTkLabel(orig_frame, text=orig_img_obj).pack(anchor="w", pady=10)
            
        # Divider
        divider = ctk.CTkFrame(row_frame, width=2, fg_color="gray30")
        divider.pack(side="left", fill="y", pady=10)
        
        # Duplicate File Side
        dup_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        dup_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        var = ctk.BooleanVar(value=True)
        self.vars.append((var, dup, row_frame))
        
        cb = ctk.CTkCheckBox(dup_frame, text="Delete Duplicate", variable=var, text_color="#C62828", font=ctk.CTkFont(weight="bold"))
        cb.pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(dup_frame, text=os.path.basename(dup), font=ctk.CTkFont(size=12)).pack(anchor="w")
        
        if isinstance(dup_img_obj, ctk.CTkImage):
            lbl2 = ctk.CTkLabel(dup_frame, image=dup_img_obj, text="")
            lbl2.image = dup_img_obj
            lbl2.pack(anchor="w", pady=5)
        else:
            ctk.CTkLabel(dup_frame, text=dup_img_obj).pack(anchor="w", pady=10)

    def get_thumbnail_image(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}:
            try:
                img = Image.open(path)
                img.thumbnail((150, 150))
                return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            except Exception:
                return "[Image Error]"
        else:
            try:
                size_mb = os.path.getsize(path) / (1024 * 1024)
                return f"Size: {size_mb:.2f} MB"
            except Exception:
                return "[File Error]"

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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Media Sorter Pro")
        self.geometry("900x800")
        self.minsize(800, 700)
        
        self.source_dir = ""
        self.target_dir = ""
        self.abort_requested = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Allow log box to expand
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title_label = ctk.CTkLabel(header_frame, text="Media Sorter Pro", font=ctk.CTkFont(size=28, weight="bold"))
        title_label.pack(side="left")
        
        self.status_label = ctk.CTkLabel(header_frame, text="Ready", text_color="#4CAF50", font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="right")
        
        # Main Settings Container (2 columns)
        settings_container = ctk.CTkFrame(self, fg_color="transparent")
        settings_container.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        settings_container.grid_columnconfigure((0, 1), weight=1)
        
        # --- Left Column: Directories & Media Types ---
        left_panel = ctk.CTkFrame(settings_container, corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(left_panel, text="Directories", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        
        # Source
        src_btn = ctk.CTkButton(left_panel, text="Browse Source", command=self.select_source, width=120)
        src_btn.pack(padx=15, pady=5, anchor="w")
        self.src_label = ctk.CTkLabel(left_panel, text="No source selected...", text_color="gray", font=ctk.CTkFont(slant="italic"))
        self.src_label.pack(padx=15, pady=(0, 10), anchor="w")
        
        # Target
        tgt_btn = ctk.CTkButton(left_panel, text="Browse Output", command=self.select_target, width=120)
        tgt_btn.pack(padx=15, pady=5, anchor="w")
        self.tgt_label = ctk.CTkLabel(left_panel, text="No output selected...", text_color="gray", font=ctk.CTkFont(slant="italic"))
        self.tgt_label.pack(padx=15, pady=(0, 10), anchor="w")
        
        # Divider
        ctk.CTkFrame(left_panel, height=2, fg_color="gray30").pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(left_panel, text="Media Types", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(0, 5))
        media_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        media_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.process_images_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(media_frame, text="Images", variable=self.process_images_var).pack(side="left", padx=(0, 10))
        
        self.process_videos_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(media_frame, text="Videos", variable=self.process_videos_var).pack(side="left", padx=10)
        
        self.process_audio_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(media_frame, text="Audio", variable=self.process_audio_var).pack(side="left", padx=10)

        # --- Right Column: Sorting Options & Advanced ---
        right_panel = ctk.CTkFrame(settings_container, corner_radius=15)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(right_panel, text="Sorting Structure", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.sort_var = ctk.StringVar(value="Year and Month")
        ctk.CTkOptionMenu(right_panel, values=["Year and Month", "Year Only"], variable=self.sort_var).pack(anchor="w", padx=15, pady=5)
        
        self.unified_tree_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="Unified Media Tree (Mix photos & videos)", variable=self.unified_tree_var).pack(anchor="w", padx=15, pady=5)
        
        self.sort_location_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="Enable Geocoding (Sort by GPS location)", variable=self.sort_location_var).pack(anchor="w", padx=15, pady=5)
        
        loc_fmt_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        loc_fmt_frame.pack(fill="x", padx=35, pady=5)
        self.loc_format_var = ctk.StringVar(value="Year/Month/Location")
        ctk.CTkRadioButton(loc_fmt_frame, text="Year/Location", variable=self.loc_format_var, value="Year/Month/Location").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(loc_fmt_frame, text="Location/Year", variable=self.loc_format_var, value="Location/Year/Month").pack(side="left")
        
        # Divider
        ctk.CTkFrame(right_panel, height=2, fg_color="gray30").pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(right_panel, text="Advanced Actions", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(0, 5))
        
        self.copy_unsupported_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="Copy Unsupported Files", variable=self.copy_unsupported_var).pack(anchor="w", padx=15, pady=5)
        
        self.delete_originals_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="Move Files (Delete source originals)", variable=self.delete_originals_var, text_color="#C62828").pack(anchor="w", padx=15, pady=(5, 15))

        # Progress Section
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=15)
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)
        
        self.timer_label = ctk.CTkLabel(progress_frame, text="", font=ctk.CTkFont(size=12))
        self.timer_label.pack()
        
        self.file_progress_bar = ctk.CTkProgressBar(progress_frame, height=8, progress_color="#4CAF50")
        self.file_progress_bar.pack(fill="x", pady=5)
        self.file_progress_bar.set(0)
        
        self.file_timer_label = ctk.CTkLabel(progress_frame, text="", font=ctk.CTkFont(size=11, text_color="gray"))
        self.file_timer_label.pack()
        
        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="n", pady=5)
        
        self.run_btn = ctk.CTkButton(btn_frame, text="▶ Start Sorting", font=ctk.CTkFont(size=16, weight="bold"), height=45, width=200, command=self.start_sorting)
        self.run_btn.pack(side="left", padx=10)
        
        self.abort_btn = ctk.CTkButton(btn_frame, text="⏹ Abort", font=ctk.CTkFont(size=16, weight="bold"), height=45, width=150, fg_color="#C62828", hover_color="#B71C1C", state="disabled", command=self.request_abort)
        self.abort_btn.pack(side="left", padx=10)
        
        # Log Text Box
        self.log_textbox = ctk.CTkTextbox(self, corner_radius=10, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_textbox.grid(row=4, column=0, sticky="nsew", padx=20, pady=(10, 20))
        self.log_textbox.insert("0.0", "Welcome to Media Sorter Pro. Select folders and start sorting!\n")
        self.log_textbox.configure(state="disabled")
        
    def select_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_dir = folder
            self.src_label.configure(text=folder, text_color=("black", "white"), font=ctk.CTkFont(slant="roman"))
            
    def select_target(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.target_dir = folder
            self.tgt_label.configure(text=folder, text_color=("black", "white"), font=ctk.CTkFont(slant="roman"))
            
    def request_abort(self):
        self.abort_requested = True
        self.status_label.configure(text="Aborting...", text_color="#FF9800")
        self.abort_btn.configure(state="disabled")
        self.append_log("[WARNING] Abort requested by user. Cleaning up...")
        
    def append_log(self, msg):
        def _update():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", msg + "\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _update)

    def update_progress(self, progress, status_text, elapsed_str="", eta_str=""):
        self.after(0, self._do_update_progress, progress, status_text, elapsed_str, eta_str)
        
    def _do_update_progress(self, progress, status_text, elapsed_str, eta_str):
        self.progress_bar.set(progress)
        self.status_label.configure(text="Processing...", text_color="#2196F3")
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
        msg += f"Duplicates Found: {stats.get('duplicates', 0)}\n"
        msg += f"Unsupported Files Skipped: {stats.get('skipped_files', 0)}\n"
        msg += f"Unsupported Files Copied: {stats.get('unsupported_copied', 0)}\n"
        
        unsupported_types = stats.get('unsupported_types', {})
        if unsupported_types:
            msg += "  (Breakdown: " + ", ".join(f"{ext}: {count}" for ext, count in unsupported_types.items()) + ")\n"
            
        msg += f"Errors: {stats.get('failed', 0)}"
        
        self.append_log(f"--- Process finished ---")
        self.append_log(f"Sorted {total_sorted} files. Found {stats.get('duplicates', 0)} duplicates.")
                
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
                process_audio_flag=process_audio_flag,
                log_callback=self.append_log
            )
            
            # Use after() to show messagebox on main thread
            self.after(0, self.show_summary, stats, self.abort_requested)
            
        except Exception as e:
            self.append_log(f"[ERROR] {str(e)}")
            self.after(0, messagebox.showerror, "Error", f"An error occurred: {str(e)}")
        finally:
            self.after(0, self.reset_ui)
            
    def reset_ui(self):
        self.run_btn.configure(state="normal")
        self.abort_btn.configure(state="disabled")
        self.abort_requested = False
        self.status_label.configure(text="Ready", text_color="#4CAF50")
        
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
        
        self.append_log(f"\n--- Starting new sort job ---")
        
        # Run in separate thread to keep UI responsive
        threading.Thread(target=self.sorting_thread, args=(sort_by_month, copy_unsup, unified_tree, sort_by_location, location_format, delete_originals, proc_img, proc_vid, proc_aud), daemon=True).start()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
