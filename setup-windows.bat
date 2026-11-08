@echo off
setlocal
title FlipLens setup
cd /d "%~dp0"
echo.
echo ===== FlipLens AI - Windows setup =====
echo.

rem ---- 1. Find Python 3.11+ ----
set "PY="
for %%V in (3.13 3.12 3.14 3.11) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [ERROR] Python 3.11 or newer was not found.
  echo Install it from https://www.python.org/downloads/windows/
  echo and tick "Add python.exe to PATH" in the installer, then run this file again.
  pause
  exit /b 1
)
for /f "delims=" %%I in ('%PY% --version') do echo Using %%I

rem ---- 2. Check Node.js ----
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js was not found.
  echo Install the LTS version from https://nodejs.org/ and run this file again.
  pause
  exit /b 1
)
for /f "delims=" %%I in ('node --version') do echo Using Node %%I
echo.

rem ---- 3. Backend: Python virtual environment ----
echo [1/2] Backend: creating Python environment and installing packages...
cd /d "%~dp0backend"
if exist ".venv" if not exist ".venv\Scripts\python.exe" (
  echo Removing a virtual environment built for another system...
  rmdir /s /q ".venv"
)
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
if not exist ".env" copy ".env.example" ".env" >nul
echo.

rem ---- 4. Frontend: Node packages ----
echo [2/2] Frontend: installing Node packages...
cd /d "%~dp0frontend"
if exist "node_modules" if not exist "node_modules\.bin\next.cmd" (
  echo Removing node_modules built for another system...
  rmdir /s /q "node_modules"
)
if exist ".next" rmdir /s /q ".next"
call npm ci
if errorlevel 1 (
  echo npm ci failed, trying npm install...
  call npm install
  if errorlevel 1 goto :fail
)
if not exist ".env.local" copy ".env.local.example" ".env.local" >nul

echo.
echo ===== Setup complete =====
echo Next: put your keys in backend\.env, then double-click start-windows.bat
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Setup stopped because a step failed. Scroll up to see the error.
pause
exit /b 1
