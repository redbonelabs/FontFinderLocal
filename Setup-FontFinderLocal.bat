@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
for /d %%D in (".python\cpython-3.13.*-windows-x86_64-none") do (
  if exist "%%~fD\python.exe" (
    "%%~fD\python.exe" -m venv .venv
    if not errorlevel 1 goto install
  )
)
py -3.13 -m venv .venv
if errorlevel 1 (
  echo Install Python 3.13 with the Windows Python launcher, then run this script again.
  pause
  exit /b 1
)
:install
".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your internet connection.
  pause
  exit /b 1
)
echo Setup complete. Run Start-FontFinderLocal.bat.
pause
