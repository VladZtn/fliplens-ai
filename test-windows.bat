@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup-windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pytest -q
echo.
cd /d "%~dp0frontend"
echo Type-checking the frontend...
call npx tsc --noEmit -p .
if errorlevel 1 (echo Frontend type check FAILED) else (echo Frontend type check passed)
pause
