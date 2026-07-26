@echo off
echo Cleaning up old builds...
rmdir /s /q build
rmdir /s /q dist
del /q ImageSorter.spec
echo.
echo Installing dependencies...
python -m pip install -r requirements.txt
echo.
echo Building executable with PyInstaller...
"C:\Users\t-cla\AppData\Roaming\Python\Python312\Scripts\pyinstaller.exe" --noconfirm --onedir --windowed --name "ImageSorter" --collect-data reverse_geocoder "main.py"
echo.
echo Build complete. Check the "dist\ImageSorter" folder for the executable.
