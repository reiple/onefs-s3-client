@echo off
setlocal

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

python -m PyInstaller ^
  --clean ^
  --onefile ^
  --name onefs-s3 ^
  src\main.py
if errorlevel 1 exit /b 1

copy /Y config.json.example dist\config.json.example >nul
echo Build completed: dist\onefs-s3.exe
