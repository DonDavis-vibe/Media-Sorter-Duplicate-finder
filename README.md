# 🗂️ Image Sorter & Duplicate Finder

A smart, cross-platform media organization tool that sorts your images, videos, and audio files by chronological timelines or GPS locations, while seamlessly detecting and handling duplicates.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-green)
![OS](https://img.shields.io/badge/OS-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## ✨ Features

- **Smart Chronological Sorting**: Automatically organizes files into folders by Year and Month. It extracts precise creation dates directly from internal EXIF metadata (for images) or filesystem dates (for videos and audio).
- **Location Geocoding**: Option to sort images into location-based folders (e.g. `2026/07_July/Paris/`) using GPS coordinates embedded in EXIF data and completely offline reverse-geocoding.
- **Unified Media Tree**: Choose to combine photos and videos taken on the same day into the exact same folder, or keep them strictly separated into "Images" and "Videos" directories.
- **Intelligent Duplicate Detection**: Employs visual perceptual AI hashing (`imagehash`) for images and MD5 fingerprinting for videos/audio to catch duplicates, even if their filenames or metadata have changed.
- **Quality-Based Deduplication**: When a duplicate is detected, the app automatically compares them and guarantees the highest-resolution or least-compressed version is kept as the definitive "Original". Lower-quality versions are gracefully moved to a dedicated `Duplicates/` folder.
- **Interactive Duplicate Manager**: A sleek, non-blocking post-sorting interface that lets you review duplicates side-by-side with the original file, preview thumbnails dynamically in the background, and manually delete them in bulk.
- **Live Console Logging**: A real-time built-in terminal window that shows you exactly what the application is doing under the hood, file by file.
- **Stunning "Pro" UI**: A dark-mode, responsive, two-column interface built with CustomTkinter for a premium native look and feel.
- **Native HEIC Support**: Fully supports Apple HEIC/HEIF images across all platforms out-of-the-box.

---

## 🚀 Quick Start for Windows

If you are on Windows and prefer not to install Python, you can simply download the standalone executable:

1. Go to the **Releases** page of this GitHub repository.
2. Download the latest `.exe` file.
3. Double-click the file to launch the Graphical User Interface (GUI)—no installation required!

---

## 🛠️ Installation (macOS, Linux, & Windows Source)

To run the application from its source code on any operating system, follow these steps:

### Prerequisites
- [Python 3.8+](https://www.python.org/downloads/) installed on your system.
- `git` installed (optional, but recommended).

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/image_sorter.git
cd image_sorter
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
1. **Source Directory**: Select the messy folder containing your raw, unsorted media.
2. **Target Directory**: Select an empty folder where you want your clean, organized timeline to be built.
3. **Media Types**: Check the boxes for what you want to process (Images, Videos, Audio). Anything unchecked will be ignored.
4. **Sort by Month**: When enabled, files are grouped like `2026/07_July`. When disabled, they are grouped purely by year (`2026`).
5. **Include Location in Path**: Organizes images as `Year/Month/Location` based on GPS data.
6. **Unified Tree**: Combines all media types into the same timeline folders.
7. **Delete Originals**: If checked, files will be *moved* from the Source Directory rather than *copied*. **Use with caution!**
8. Click **Start Sorting**. 
9. After the progress bar finishes, the **Duplicate Manager** will automatically open if any duplicates were found, allowing you to review and delete them safely.

---

## 📦 Compiling Your Own Executable

You can use PyInstaller to compile this Python script into a standalone executable app for your own operating system. This is great for sharing the app with friends or running it without opening a terminal.

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
*(On macOS, this will generate a `.app` bundle inside the `dist/` directory that you can move to your Applications folder).*

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
