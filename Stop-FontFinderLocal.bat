@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Project virtual environment is missing.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m app.startup --stop
if errorlevel 1 pause
