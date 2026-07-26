import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import json
import subprocess
import tempfile
import multiprocessing
from PIL import Image
from sorter import process_images

# ── Config persistence ────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_config.json")

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ── Helpers ───────────────────────────────────────────────────────────────────
def format_size(num_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"

def count_files_and_size(folder):
    """Return (count, total_bytes) for all files recursively in folder."""
    total_files = 0
    total_bytes = 0
    try:
        for root, _, files in os.walk(folder):
            for f in files:
                total_files += 1
                try:
                    total_bytes += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
    except Exception:
        pass
    return total_files, total_bytes


# ── Dry Run Preview Window ────────────────────────────────────────────────────
class DrySortPreviewWindow(ctk.CTkToplevel):
    ACTION_COLORS = {
        'sort':            '#4CAF50',   # green
        'duplicate':       '#FF9800',   # orange
        'skip':            '#9E9E9E',   # gray
        'copy_unsupported':'#2196F3',   # blue
    }
    ACTION_LABELS = {
        'sort':            '✅ Sort',
        'duplicate':       '🔁 Duplicate',
        'skip':            '⏭ Skip',
        'copy_unsupported':'📋 Copy',
    }

    def __init__(self, master, stats, proceed_callback):
        super().__init__(master)
        self.title("Sort Preview — Dry Run")
        self.geometry("950x680")
        self.proceed_callback = proceed_callback
        self.resizable(True, True)

        ops = stats.get('planned_operations', [])
        total = len(ops)
        sorted_count = stats.get('images_sorted', 0) + stats.get('videos_sorted', 0) + stats.get('audios_sorted', 0)
        dup_count    = stats.get('duplicates', 0)
        skip_count   = stats.get('skipped_files', 0)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(hdr, text="🔍 Sort Preview", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        # Summary pills
        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.pack(fill="x", padx=20, pady=(0, 10))
        pills = [
            (f"📁 {total} total files",        "#424242"),
            (f"✅ {sorted_count} will be sorted", "#2E7D32"),
            (f"🔁 {dup_count} duplicates",      "#E65100"),
            (f"⏭ {skip_count} skipped",         "#616161"),
        ]
        for text, color in pills:
            lbl = ctk.CTkLabel(summary_frame, text=text,
                               fg_color=color, corner_radius=8,
                               font=ctk.CTkFont(size=12, weight="bold"),
                               padx=10, pady=4)
            lbl.pack(side="left", padx=(0, 8))

        # Column headers
        col_frame = ctk.CTkFrame(self, fg_color="gray20", corner_radius=0)
        col_frame.pack(fill="x", padx=20)
        for text, width in [("File Name", 280), ("Type", 70), ("Action", 110), ("Destination", 420)]:
            ctk.CTkLabel(col_frame, text=text, font=ctk.CTkFont(weight="bold"),
                         width=width, anchor="w").pack(side="left", padx=8, pady=6)

        # Scrollable rows
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        for op in ops:
            action   = op.get('action', 'skip')
            color    = self.ACTION_COLORS.get(action, '#9E9E9E')
            row = ctk.CTkFrame(scroll, fg_color="gray17", corner_radius=6)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=op['filename'],    width=280, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left", padx=8, pady=5)
            ctk.CTkLabel(row, text=op.get('type','?').capitalize(), width=70, anchor="w",
                         font=ctk.CTkFont(size=11), text_color="gray70").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=self.ACTION_LABELS.get(action, action), width=110, anchor="w",
                         text_color=color, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=4)
            ctk.CTkLabel(row, text=op.get('dest_label',''), width=420, anchor="w",
                         font=ctk.CTkFont(size=11), text_color="gray80").pack(side="left", padx=4)

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="▶  Proceed with Sort",
                      font=ctk.CTkFont(size=15, weight="bold"),
                      height=42, width=220,
                      fg_color="#2E7D32", hover_color="#1B5E20",
                      command=self._proceed).pack(side="left", padx=10)

        ctk.CTkButton(btn_frame, text="✕  Cancel",
                      font=ctk.CTkFont(size=15, weight="bold"),
                      height=42, width=130,
                      fg_color="#424242", hover_color="#212121",
                      command=self.destroy).pack(side="left", padx=10)

    def _proceed(self):
        self.destroy()
        if self.proceed_callback:
            self.proceed_callback()


# ── Duplicate Manager Window ──────────────────────────────────────────────────
class DuplicateManagerWindow(ctk.CTkToplevel):
    def __init__(self, master, duplicate_pairs):
        super().__init__(master)
        self.title("Duplicate Manager")
        self.geometry("850x650")
        self.duplicate_pairs = duplicate_pairs

        self.title_label = ctk.CTkLabel(self, text="Review Duplicates",
                                        font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.pack(pady=15)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.vars = []

        self.loading_label = ctk.CTkLabel(self.scroll_frame,
                                          text="Processing thumbnails in background...",
                                          font=ctk.CTkFont(slant="italic"))
        self.loading_label.pack(pady=20)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=15)

        self.delete_btn = ctk.CTkButton(
            self.btn_frame, text="Delete Selected",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#C62828", hover_color="#B71C1C",
            command=self.delete_selected)
        self.delete_btn.pack(side="left", padx=10)

        self.close_btn = ctk.CTkButton(self.btn_frame, text="Done", command=self.destroy)
        self.close_btn.pack(side="left", padx=10)

        threading.Thread(target=self.load_items_bg, daemon=True).start()

    def load_items_bg(self):
        for orig, dup in self.duplicate_pairs:
            orig_img = self.get_thumbnail_image(orig)
            dup_img  = self.get_thumbnail_image(dup)
            self.after(0, self.add_row_ui, orig, dup, orig_img, dup_img)
        self.after(0, self.finish_loading_ui)

    def finish_loading_ui(self):
        try:
            self.loading_label.destroy()
        except Exception:
            pass

    def add_row_ui(self, orig, dup, orig_img_obj, dup_img_obj):
        row_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        row_frame.pack(fill="x", pady=8, padx=5)

        # Original side
        orig_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        orig_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(orig_frame, text="Original Kept:",
                     font=ctk.CTkFont(weight="bold"), text_color="#4CAF50").pack(anchor="w")
        ctk.CTkLabel(orig_frame, text=os.path.basename(orig),
                     font=ctk.CTkFont(size=12)).pack(anchor="w")
        self._render_thumb(orig_frame, orig_img_obj)

        # Divider
        ctk.CTkFrame(row_frame, width=2, fg_color="gray30").pack(side="left", fill="y", pady=10)

        # Duplicate side
        dup_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        dup_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        var = ctk.BooleanVar(value=True)
        self.vars.append((var, dup, row_frame))

        cb = ctk.CTkCheckBox(dup_frame, text="Delete Duplicate", variable=var,
                             text_color="#C62828", font=ctk.CTkFont(weight="bold"))
        cb.pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(dup_frame, text=os.path.basename(dup),
                     font=ctk.CTkFont(size=12)).pack(anchor="w")
        self._render_thumb(dup_frame, dup_img_obj)

    def _render_thumb(self, parent, img_obj):
        if isinstance(img_obj, ctk.CTkImage):
            lbl = ctk.CTkLabel(parent, image=img_obj, text="")
            lbl.image = img_obj
            lbl.pack(anchor="w", pady=5)
        else:
            ctk.CTkLabel(parent, text=str(img_obj)).pack(anchor="w", pady=10)

    def get_thumbnail_image(self, path):
        ext = os.path.splitext(path)[1].lower()

        # ── Image thumbnail ───────────────────────────────────────────────────
        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}:
            try:
                img = Image.open(path)
                img.thumbnail((150, 150))
                return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            except Exception:
                return "[Image Error]"

        # ── Video thumbnail via ffmpeg ─────────────────────────────────────────
        elif ext in {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}:
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                result = subprocess.run(
                    ['ffmpeg', '-i', path, '-ss', '00:00:01', '-vframes', '1', '-y', tmp_path],
                    capture_output=True, timeout=15
                )
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    img = Image.open(tmp_path)
                    img.thumbnail((150, 150))
                    img = img.copy()  # Pull into memory before file deletion
                    return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            except Exception:
                pass
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            # Fallback: show file size
            try:
                return f"🎬 {format_size(os.path.getsize(path))}"
            except Exception:
                return "🎬 Video"

        # ── Audio / other ─────────────────────────────────────────────────────
        else:
            try:
                return f"🎵 {format_size(os.path.getsize(path))}"
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


# ── Main Application ──────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Media Sorter Pro")
        self.geometry("940x860")
        self.minsize(820, 720)

        self.source_dir     = ""
        self.target_dir     = ""
        self.abort_requested = False
        self._config        = load_config()

        self.create_widgets()

        # Restore last used folders
        last_src = self._config.get("last_source", "")
        last_tgt = self._config.get("last_target", "")
        if last_src and os.path.exists(last_src):
            self.source_dir = last_src
            self.src_label.configure(text=last_src, text_color=("black", "white"),
                                     font=ctk.CTkFont(slant="roman"))
            self._update_folder_info(last_src, self.src_info_label)
        if last_tgt and os.path.exists(last_tgt):
            self.target_dir = last_tgt
            self.tgt_label.configure(text=last_tgt, text_color=("black", "white"),
                                     font=ctk.CTkFont(slant="roman"))

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Log box expands

        # ── Header ────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        ctk.CTkLabel(header_frame, text="Media Sorter Pro",
                     font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")

        # Dark / Light toggle
        self._appearance_mode = ctk.StringVar(value="Dark")
        mode_btn = ctk.CTkButton(header_frame, text="☀ Light Mode", width=110,
                                 fg_color="gray30", hover_color="gray40",
                                 command=self._toggle_appearance)
        mode_btn.pack(side="right", padx=(10, 0))
        self._mode_btn = mode_btn

        self.status_label = ctk.CTkLabel(header_frame, text="● Ready",
                                         text_color="#4CAF50",
                                         font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="right")

        # ── Two-column settings ───────────────────────────────────────────────
        settings_container = ctk.CTkFrame(self, fg_color="transparent")
        settings_container.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        settings_container.grid_columnconfigure((0, 1), weight=1)

        # Left panel
        left_panel = ctk.CTkFrame(settings_container, corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(left_panel, text="Directories",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))

        src_btn = ctk.CTkButton(left_panel, text="📂 Browse Source",
                                command=self.select_source, width=140)
        src_btn.pack(padx=15, pady=5, anchor="w")
        self.src_label = ctk.CTkLabel(left_panel, text="No source selected…",
                                      text_color="gray", font=ctk.CTkFont(slant="italic"),
                                      wraplength=320)
        self.src_label.pack(padx=15, pady=(0, 2), anchor="w")
        self.src_info_label = ctk.CTkLabel(left_panel, text="",
                                           text_color="#64B5F6", font=ctk.CTkFont(size=11))
        self.src_info_label.pack(padx=15, pady=(0, 8), anchor="w")

        tgt_btn = ctk.CTkButton(left_panel, text="📂 Browse Output",
                                command=self.select_target, width=140)
        tgt_btn.pack(padx=15, pady=5, anchor="w")
        self.tgt_label = ctk.CTkLabel(left_panel, text="No output selected…",
                                      text_color="gray", font=ctk.CTkFont(slant="italic"),
                                      wraplength=320)
        self.tgt_label.pack(padx=15, pady=(0, 15), anchor="w")

        ctk.CTkFrame(left_panel, height=2, fg_color="gray30").pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(left_panel, text="Media Types",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(0, 5))
        media_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        media_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.process_images_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(media_frame, text="Images",
                        variable=self.process_images_var).pack(side="left", padx=(0, 10))
        self.process_videos_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(media_frame, text="Videos",
                        variable=self.process_videos_var).pack(side="left", padx=10)
        self.process_audio_var  = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(media_frame, text="Audio",
                        variable=self.process_audio_var).pack(side="left", padx=10)

        # Right panel
        right_panel = ctk.CTkFrame(settings_container, corner_radius=15)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(right_panel, text="Sorting Structure",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))

        self.sort_var = ctk.StringVar(value="Year and Month")
        ctk.CTkOptionMenu(right_panel,
                          values=["Year and Month", "Year Only"],
                          variable=self.sort_var).pack(anchor="w", padx=15, pady=5)

        self.unified_tree_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="Unified Media Tree (Mix photos & videos)",
                        variable=self.unified_tree_var).pack(anchor="w", padx=15, pady=5)

        self.sort_location_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="Enable Geocoding (Sort by GPS location)",
                        variable=self.sort_location_var).pack(anchor="w", padx=15, pady=5)

        loc_fmt_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        loc_fmt_frame.pack(fill="x", padx=35, pady=5)
        self.loc_format_var = ctk.StringVar(value="Year/Month/Location")
        ctk.CTkRadioButton(loc_fmt_frame, text="Year/Location",
                           variable=self.loc_format_var,
                           value="Year/Month/Location").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(loc_fmt_frame, text="Location/Year",
                           variable=self.loc_format_var,
                           value="Location/Year/Month").pack(side="left")

        ctk.CTkFrame(right_panel, height=2, fg_color="gray30").pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(right_panel, text="Advanced",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(0, 5))

        self.copy_unsupported_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="Copy Unsupported Files",
                        variable=self.copy_unsupported_var).pack(anchor="w", padx=15, pady=5)

        self.delete_originals_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="Move Files (Delete source originals)",
                        variable=self.delete_originals_var,
                        text_color="#EF9A9A").pack(anchor="w", padx=15, pady=5)

        self.use_multithreading_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="⚡ Multi-threaded Hashing (faster for large libraries)",
                        variable=self.use_multithreading_var).pack(anchor="w", padx=15, pady=5)

        self.dry_run_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_panel, text="🔍 Preview Mode (dry run — no files moved)",
                        variable=self.dry_run_var,
                        text_color="#64B5F6").pack(anchor="w", padx=15, pady=(5, 15))

        # ── Progress section ──────────────────────────────────────────────────
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)

        self.timer_label = ctk.CTkLabel(progress_frame, text="",
                                        font=ctk.CTkFont(size=12))
        self.timer_label.pack()

        self.file_progress_bar = ctk.CTkProgressBar(progress_frame, height=8,
                                                     progress_color="#4CAF50")
        self.file_progress_bar.pack(fill="x", pady=5)
        self.file_progress_bar.set(0)

        self.file_timer_label = ctk.CTkLabel(progress_frame, text="",
                                             font=ctk.CTkFont(size=11),
                                             text_color="gray")
        self.file_timer_label.pack()

        # ── Action buttons ────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="n", pady=5)

        self.run_btn = ctk.CTkButton(
            btn_frame, text="▶  Start Sorting",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45, width=200, command=self.start_sorting)
        self.run_btn.pack(side="left", padx=10)

        self.abort_btn = ctk.CTkButton(
            btn_frame, text="⏹  Abort",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45, width=130,
            fg_color="#C62828", hover_color="#B71C1C",
            state="disabled", command=self.request_abort)
        self.abort_btn.pack(side="left", padx=10)

        clear_btn = ctk.CTkButton(
            btn_frame, text="🗑 Clear Log",
            font=ctk.CTkFont(size=13),
            height=45, width=110,
            fg_color="gray30", hover_color="gray40",
            command=self.clear_log)
        clear_btn.pack(side="left", padx=10)

        # ── Live log console ──────────────────────────────────────────────────
        self.log_textbox = ctk.CTkTextbox(
            self, corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=11))
        self.log_textbox.grid(row=4, column=0, sticky="nsew", padx=20, pady=(5, 20))
        self.log_textbox.insert("0.0",
            "Welcome to Media Sorter Pro.\n"
            "Tip: Enable '🔍 Preview Mode' to see what would happen before sorting.\n")
        self.log_textbox.configure(state="disabled")

    # ── Appearance toggle ─────────────────────────────────────────────────────
    def _toggle_appearance(self):
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("Light")
            self._mode_btn.configure(text="🌙 Dark Mode")
        else:
            ctk.set_appearance_mode("Dark")
            self._mode_btn.configure(text="☀ Light Mode")

    # ── Folder selection ──────────────────────────────────────────────────────
    def _update_folder_info(self, folder, label_widget):
        """Show file count and size in a small label below the path."""
        def _scan():
            count, size = count_files_and_size(folder)
            label_widget.after(0, lambda: label_widget.configure(
                text=f"{count:,} files  •  {format_size(size)}"))
        threading.Thread(target=_scan, daemon=True).start()

    def select_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_dir = folder
            self.src_label.configure(text=folder, text_color=("black", "white"),
                                     font=ctk.CTkFont(slant="roman"))
            self.src_info_label.configure(text="Counting files…")
            self._update_folder_info(folder, self.src_info_label)
            cfg = load_config()
            cfg["last_source"] = folder
            save_config(cfg)

    def select_target(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.target_dir = folder
            self.tgt_label.configure(text=folder, text_color=("black", "white"),
                                     font=ctk.CTkFont(slant="roman"))
            cfg = load_config()
            cfg["last_target"] = folder
            save_config(cfg)

    # ── Log helpers ───────────────────────────────────────────────────────────
    def append_log(self, msg):
        def _update():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", msg + "\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _update)

    def clear_log(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")

    # ── Progress updates ──────────────────────────────────────────────────────
    def update_progress(self, progress, status_text, elapsed_str="", eta_str=""):
        self.after(0, self._do_update_progress, progress, status_text, elapsed_str, eta_str)

    def _do_update_progress(self, progress, status_text, elapsed_str, eta_str):
        self.progress_bar.set(progress)
        self.status_label.configure(text="● Processing…", text_color="#2196F3")
        if elapsed_str or eta_str:
            self.timer_label.configure(text=f"Elapsed: {elapsed_str}  |  ETA: {eta_str}")
        else:
            self.timer_label.configure(text="")

    def update_file_progress(self, percent, speed_str):
        self.after(0, self._do_update_file_progress, percent, speed_str)

    def _do_update_file_progress(self, percent, speed_str):
        self.file_progress_bar.set(percent)
        if speed_str:
            self.file_timer_label.configure(
                text=f"File: {int(percent * 100)}%  |  Speed: {speed_str}")
        else:
            self.file_timer_label.configure(text="")

    # ── Summary / Abort ───────────────────────────────────────────────────────
    def request_abort(self):
        self.abort_requested = True
        self.status_label.configure(text="● Aborting…", text_color="#FF9800")
        self.abort_btn.configure(state="disabled")
        self.append_log("[WARNING] Abort requested. Cleaning up…")

    def show_summary(self, stats, was_aborted):
        title = "Process Aborted" if was_aborted else "✅ Success"
        action_word = "aborted" if was_aborted else "completed"

        images   = stats.get('images_sorted', 0)
        videos   = stats.get('videos_sorted', 0)
        audios   = stats.get('audios_sorted', 0)
        total    = images + videos + audios

        msg  = f"Sorting {action_word}!\n\n"
        msg += f"Total Files Sorted: {total}\n"
        msg += f"  — Images: {images}\n"
        msg += f"  — Videos: {videos}\n"
        msg += f"  — Audio:  {audios}\n"
        msg += f"Duplicates Found: {stats.get('duplicates', 0)}\n"
        msg += f"Unsupported Skipped: {stats.get('skipped_files', 0)}\n"
        msg += f"Unsupported Copied:  {stats.get('unsupported_copied', 0)}\n"

        types = stats.get('unsupported_types', {})
        if types:
            msg += "  (" + ", ".join(f"{e}: {c}" for e, c in types.items()) + ")\n"
        msg += f"Errors: {stats.get('failed', 0)}"

        self.append_log("--- Process finished ---")
        self.append_log(f"Sorted {total} files. Found {stats.get('duplicates', 0)} duplicates.")

        messagebox.showinfo(title, msg)

        if stats.get('duplicate_pairs'):
            DuplicateManagerWindow(self, stats['duplicate_pairs'])

    # ── Sorting logic ─────────────────────────────────────────────────────────
    def _build_sort_kwargs(self, dry_run=False):
        return dict(
            sort_by_month       = self.sort_var.get() == "Year and Month",
            copy_unsupported    = self.copy_unsupported_var.get(),
            unified_tree        = self.unified_tree_var.get(),
            sort_by_location    = self.sort_location_var.get(),
            location_format     = self.loc_format_var.get(),
            delete_originals    = self.delete_originals_var.get() and not dry_run,
            process_images_flag = self.process_images_var.get(),
            process_videos_flag = self.process_videos_var.get(),
            process_audio_flag  = self.process_audio_var.get(),
            use_multithreading  = self.use_multithreading_var.get(),
            dry_run             = dry_run,
        )

    def sorting_thread(self, dry_run=False):
        try:
            stats = process_images(
                self.source_dir,
                self.target_dir,
                progress_callback      = self.update_progress,
                abort_flag             = lambda: self.abort_requested,
                file_progress_callback = self.update_file_progress,
                log_callback           = self.append_log,
                **self._build_sort_kwargs(dry_run=dry_run)
            )

            if dry_run:
                self.after(0, self._show_dry_run_preview, stats)
            else:
                self.after(0, self.show_summary, stats, self.abort_requested)

        except Exception as e:
            self.append_log(f"[ERROR] {e}")
            self.after(0, messagebox.showerror, "Error", f"An error occurred:\n{e}")
        finally:
            self.after(0, self.reset_ui)

    def _show_dry_run_preview(self, stats):
        def proceed():
            self._launch_sort(dry_run=False)
        DrySortPreviewWindow(self, stats, proceed_callback=proceed)

    def reset_ui(self):
        self.run_btn.configure(state="normal")
        self.abort_btn.configure(state="disabled")
        self.abort_requested = False
        self.status_label.configure(text="● Ready", text_color="#4CAF50")

    def _launch_sort(self, dry_run=False):
        self.abort_requested = False
        self.run_btn.configure(state="disabled")
        self.abort_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.file_progress_bar.set(0)
        self.file_timer_label.configure(text="")

        label = "[PREVIEW] Starting dry run preview…" if dry_run else "--- Starting new sort job ---"
        self.append_log(f"\n{label}")

        threading.Thread(target=self.sorting_thread, args=(dry_run,), daemon=True).start()

    def start_sorting(self):
        if not self.source_dir or not os.path.exists(self.source_dir):
            messagebox.showwarning("Missing Information", "Please select a valid source folder.")
            return
        if not self.target_dir or not os.path.exists(self.target_dir):
            messagebox.showwarning("Missing Information", "Please select a valid destination folder.")
            return
        if self.source_dir == self.target_dir:
            messagebox.showwarning("Invalid Selection",
                                   "Source and destination folders cannot be the same.")
            return
        if not (self.process_images_var.get() or
                self.process_videos_var.get() or
                self.process_audio_var.get()):
            messagebox.showwarning("Missing Information",
                                   "Please select at least one media type to process.")
            return

        is_dry = self.dry_run_var.get()
        self._launch_sort(dry_run=is_dry)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
