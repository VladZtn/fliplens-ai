@echo off
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Run setup-windows.bat first.
  pause
  exit /b 1
)
if not exist "frontend\node_modules\.bin\next.cmd" (
  echo Run setup-windows.bat first.
  pause
  exit /b 1
)
echo Starting FlipLens API on http://127.0.0.1:8000 ...
start "FlipLens API" /d "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
echo Starting FlipLens website on http://localhost:3000 ...
start "FlipLens Web" /d "%~dp0frontend" cmd /k "npm run dev"
echo Opening the browser in a few seconds. Close the two black windows to stop FlipLens.
timeout /t 8 /nobreak >nul
start "" "http://localhost:3000"
