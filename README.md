# 🗂️ Media Sorter Pro

A smart, cross-platform media organization tool that sorts your images, videos, and audio files by chronological timelines or GPS locations, while seamlessly detecting and handling duplicates.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-green)
![OS](https://img.shields.io/badge/OS-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## ✨ Features

- **🔍 Preview / Dry Run Mode**: See exactly what *would* happen before a single file is moved. A rich, color-coded preview window lists every planned operation (Sort ✅, Duplicate 🔁, Skip ⏭). Click "Proceed" to launch the real sort instantly.
- **⚡ Optional Multi-threaded Hashing**: Enable parallel hash computation to speed up duplicate detection on large libraries. Uses up to 8 CPU threads simultaneously.
- **💾 Remembers Your Folders**: The app automatically saves and restores your last used source and output folders — no need to re-select them every session.
- **📁 Folder Stats at a Glance**: After selecting a source folder, the app instantly shows the file count and total size (e.g. *1,247 files • 4.2 GB*).
- **Smart Chronological Sorting**: Automatically organizes files into folders by Year and Month using EXIF metadata for images and filesystem dates for videos/audio.
- **Location Geocoding**: Sort images into location-based folders (e.g. `2026/07_July/Paris/`) using GPS coordinates from EXIF data — completely offline.
- **Unified Media Tree**: Combine photos and videos into one shared timeline, or keep them in separate "Images" and "Videos" directories.
- **Intelligent Duplicate Detection**: Perceptual AI hashing (`imagehash`) for images and SHA-256 fingerprinting for videos/audio — catches duplicates even across renames.
- **Quality-Based Deduplication**: When a duplicate is found, the highest-resolution version is kept as the original. Lower-quality copies are moved to a `Duplicates/` folder.
- **Interactive Duplicate Manager**: Review duplicates side-by-side with real **image thumbnails** and **video frame previews** (via ffmpeg). Delete in bulk with one click.
- **Live Console Logging**: A real-time terminal window shows exactly what is happening, file by file. Clear it anytime with the Clear Log button.
- **Dark / Light Mode**: Toggle between dark and light themes from the header with one click.
- **Native HEIC Support**: Fully supports Apple HEIC/HEIF images across all platforms.

---

## 🚀 Getting Started

### Prerequisites
- [Python 3.8+](https://www.python.org/downloads/)
- [ffmpeg](https://ffmpeg.org/download.html) on your system PATH (needed for video thumbnails in the Duplicate Manager)

### Run from source (Windows / macOS / Linux)
```bash
git clone https://github.com/DonDavis-vibe/Media-Sorter-Duplicate-finder.git
cd Media-Sorter-Duplicate-finder
pip install -r requirements.txt
python main.py
```
*(Linux/macOS: use `python3` and `pip3` if your system requires it.)*

### Compile a standalone executable

You'll need Python **once** to compile. The result runs on any PC without Python installed.

**Windows:**
```cmd
build.bat
```
The app will appear in `dist\ImageSorter\` — double-click `ImageSorter.exe` to launch.

**macOS / Linux:**
```bash
chmod +x build.sh
./build.sh
```
*(On macOS, this produces a `.app` bundle in `dist/` you can drag to your Applications folder.)*

---

## 🖥️ How to Use

1. **Browse Source** — select the messy folder containing your raw media. The app will show the file count and total size instantly.
2. **Browse Output** — select an empty folder where the sorted timeline will be created.
3. **Media Types** — tick Images, Videos, and/or Audio depending on what you want to process.
4. **Sorting Structure** — choose *Year and Month* or *Year Only*. Optionally enable Geocoding to sort by GPS location.
5. **Advanced Options**:
   - **⚡ Multi-threaded Hashing** — faster duplicate detection for large libraries.
   - **🔍 Preview Mode** — tick this first for a risk-free preview of every planned operation.
   - **Move Files** — moves files from source instead of copying them. **Use with caution!**
6. Click **▶ Start Sorting**.
   - In Preview Mode, review the plan and click **▶ Proceed with Sort** to run it for real.
7. If duplicates are found, the **Duplicate Manager** opens automatically so you can review and delete them.

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
