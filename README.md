# 🗂️ Media Sorter Pro

A smart, cross-platform media organization tool that sorts your images, videos, and audio files by chronological timelines or GPS locations, while seamlessly detecting and handling duplicates.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-green)
![OS](https://img.shields.io/badge/OS-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## ✨ Features

- **🔍 Preview / Dry Run Mode**: See exactly what *would* happen before a single file is moved. A rich, color-coded preview window lists every planned operation (Sort ✅, Duplicate 🔁, Skip ⏭). Click "Proceed" to launch the real sort instantly.
- **⚡ Optional Multi-threaded Hashing**: Enable parallel hash computation to dramatically speed up duplicate detection on large libraries. Uses up to 8 CPU threads simultaneously.
- **💾 Remembers Your Folders**: The app automatically saves and restores your last used source and output folders — no need to re-select them every session.
- **📁 Folder Stats at a Glance**: After selecting a source folder, the app instantly shows you the file count and total size (e.g. *1,247 files • 4.2 GB*).
- **Smart Chronological Sorting**: Automatically organizes files into folders by Year and Month. It extracts precise creation dates directly from internal EXIF metadata (for images) or filesystem dates (for videos and audio).
- **Location Geocoding**: Option to sort images into location-based folders (e.g. `2026/07_July/Paris/`) using GPS coordinates embedded in EXIF data and completely offline reverse-geocoding.
- **Unified Media Tree**: Choose to combine photos and videos taken on the same day into the exact same folder, or keep them strictly separated into "Images" and "Videos" directories.
- **Intelligent Duplicate Detection**: Employs visual perceptual AI hashing (`imagehash`) for images and SHA-256 fingerprinting for videos/audio to catch duplicates, even if their filenames or metadata have changed.
- **Quality-Based Deduplication**: When a duplicate is detected, the app automatically compares them and guarantees the highest-resolution or least-compressed version is kept as the definitive "Original". Lower-quality versions are gracefully moved to a dedicated `Duplicates/` folder.
- **Interactive Duplicate Manager**: A sleek, non-blocking post-sorting interface that lets you review duplicates side-by-side. Shows **real image thumbnails** and even **video frame previews** (via ffmpeg). Delete duplicates in bulk with one click.
- **Live Console Logging**: A real-time built-in terminal window shows you exactly what the application is doing under the hood, file by file. Clear it anytime with the Clear Log button.
- **Premium Dark/Light UI**: A modern, responsive, two-column interface built with CustomTkinter. Toggle between dark and light mode from the header with one click.
- **Native HEIC Support**: Fully supports Apple HEIC/HEIF images across all platforms out-of-the-box.

---

## 🚀 Quick Start for Windows

If you are on Windows and prefer not to install Python, you can simply download the standalone executable:

1. Go to the **Releases** page of this GitHub repository.
2. Download the latest `.exe` file.
3. Double-click the file to launch the Graphical User Interface (GUI) — no installation required!

---

## 🛠️ Installation (macOS, Linux, & Windows Source)

To run the application from its source code on any operating system, follow these steps:

### Prerequisites
- [Python 3.8+](https://www.python.org/downloads/) installed on your system.
- [ffmpeg](https://ffmpeg.org/download.html) installed and available on your system PATH (required for video thumbnails in the Duplicate Manager).
- `git` installed (optional, but recommended).

### 1. Clone the repository
```bash
git clone https://github.com/DonDavis-vibe/Media-Sorter-Duplicate-finder.git
cd Media-Sorter-Duplicate-finder
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the App
```bash
python main.py
```

*(Note for Linux/macOS users: Depending on your environment, you may need to use `python3` and `pip3` instead of `python` and `pip`.)*

---

## 🖥️ How to Use the App

Once the GUI is open:

1. **Source Directory**: Click **Browse Source** to select the messy folder containing your raw, unsorted media. The app will instantly display the file count and total size.
2. **Target Directory**: Click **Browse Output** to select an empty folder where your clean, organized timeline will be built.
3. **Media Types**: Check the boxes for what you want to process (Images, Videos, Audio). Anything unchecked will be ignored.
4. **Sorting Structure**: Choose between *Year and Month* or *Year Only* grouping. Optionally enable **Geocoding** to sort by GPS location.
5. **Advanced Options**:
   - **⚡ Multi-threaded Hashing** — Enable for faster processing on large libraries (hundreds to thousands of files).
   - **🔍 Preview Mode** — Enable this first to get a risk-free preview of every planned operation before committing.
   - **Move Files** — If checked, files are *moved* (deleted from source) rather than *copied*. **Use with caution!**
6. Click **▶ Start Sorting**.
   - If **Preview Mode** is on, a preview window opens. Review the plan, then click **▶ Proceed with Sort** to run it for real.
7. After sorting completes, the **Duplicate Manager** automatically opens if duplicates were found, letting you review and delete them safely.

---

## 📦 Compiling Your Own Executable

You can use PyInstaller to compile this Python script into a standalone executable for your own operating system.

### Windows
Simply run the included batch script:
```cmd
build.bat
```

### macOS and Linux
Run the included bash script. You may need to make it executable first:
```bash
chmod +x build.sh
./build.sh
```
*(On macOS, this will generate a `.app` bundle inside the `dist/` directory that you can move to your Applications folder.)*

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
