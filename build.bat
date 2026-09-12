@echo off
setlocal

REM Windows 로컬 빌드. GitHub Actions 와 동일한 spec 을 사용한다.
REM CI 산출물과 완전히 같은 바이너리를 원하면 Python 3.12 x64 를 사용할 것.

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

python -m PyInstaller --clean --noconfirm packaging\onefs-s3.spec
if errorlevel 1 exit /b 1

copy /Y config.json.example dist\config.json.example >nul
echo Build completed: dist\onefs-s3.exe
