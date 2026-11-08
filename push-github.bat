@echo off
setlocal
cd /d "%~dp0"
title FlipLens - push to GitHub

where git >nul 2>&1
if errorlevel 1 (
  echo Git is not installed. Get it from https://git-scm.com/download/win and run this again.
  pause
  exit /b 1
)

if not exist ".git" (
  echo Connecting this folder to github.com/VladZtn/fliplens-ai ...
  git init -q
  git remote add origin https://github.com/VladZtn/fliplens-ai.git
)

git fetch -q origin
if errorlevel 1 (
  echo Could not reach GitHub. Check your internet connection and GitHub sign-in.
  pause
  exit /b 1
)

rem First run only: keep the GitHub history and put this folder on top of it.
git rev-parse --verify -q HEAD >nul 2>&1
if errorlevel 1 git reset -q --soft origin/main

git config user.name >nul 2>&1 || git config user.name "VladZtn"
git config user.email >nul 2>&1 || git config user.email "zolotonosha.itsmart@gmail.com"

git add -A

rem Safety check: never commit a real .env file (only .env.example is allowed).
git diff --cached --name-only --diff-filter=ACMR | findstr /R /I "\.env$ \.env\.local$ \.env\.production$ \.env\.development$" >nul
if not errorlevel 1 (
  echo.
  echo [STOPPED] A file with API keys is about to be committed:
  git diff --cached --name-only --diff-filter=ACMR | findstr /R /I "\.env"
  git reset -q
  echo Nothing was committed or pushed.
  pause
  exit /b 1
)

echo.
echo Changes to push (A = added, M = changed, D = removed):
git diff --cached --name-status
echo.
echo Safety check passed: no .env files with keys are included.
set /p CONFIRM=Push to GitHub now? Type y and press Enter: 
if /i not "%CONFIRM%"=="y" (
  git reset -q
  echo Cancelled. Nothing was pushed.
  pause
  exit /b 0
)

git commit -q -m "Selling fees, accurate eBay pricing, free tier, new UI, Windows scripts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01MESrmjjQ9U5zPavnkoaWiP"
if errorlevel 1 (
  echo Nothing new to commit.
)
git push origin HEAD:main
if errorlevel 1 (
  echo.
  echo Push failed. If a GitHub sign-in window appeared, sign in and run this file again.
  pause
  exit /b 1
)
echo.
echo Done: https://github.com/VladZtn/fliplens-ai
pause
