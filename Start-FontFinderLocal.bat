@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run: run Setup-FontFinderLocal.bat to install dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.startup
if errorlevel 1 (
  echo Startup failed. Run Setup-FontFinderLocal.bat or see data\fontfinder.log.
  pause
  exit /b 1
)
