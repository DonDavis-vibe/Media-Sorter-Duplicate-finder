@echo off
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Building executable with PyInstaller...
pyinstaller --noconfirm --onedir --windowed --name "ImageSorter" "main.py"
echo.
echo Build complete. Check the "dist\ImageSorter" folder for the executable.
pause
