#!/bin/bash
echo "Starting PyInstaller build for Image Sorter..."
echo "Make sure you have installed requirements with: pip install -r requirements.txt"
echo "---"

# Remove old builds
rm -rf build/ dist/ ImageSorter.spec

# Build the executable
pyinstaller --noconfirm --onedir --windowed --name "ImageSorter" --collect-data reverse_geocoder "main.py"

echo "---"
echo "Build complete! You can find the executable app in the 'dist' folder."
