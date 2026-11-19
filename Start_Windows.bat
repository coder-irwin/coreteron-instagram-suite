@echo off
REM ==============================================================================
REM Coreteron Instagram Suite - 1-Click Windows Launcher
REM Double-click this file to start the application. Zero Git required!
REM ==============================================================================

cd /d "%~dp0"
title Coreteron Instagram Automation Suite

echo ==================================================================
echo     [+] STARTING CORETERON INSTAGRAM SUITE (WINDOWS)              
echo ==================================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [-] Python is not detected in your system PATH.
    echo [!] Please download Python from: https://www.python.org/downloads/
    echo [!] IMPORTANT: Check the box "Add python.exe to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo [+] Python detected:
python --version

REM Create virtual environment if missing
if not exist ".venv" (
    echo [+] Creating virtual environment (.venv)...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies
echo [+] Verifying package dependencies...
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

REM Install Chromium browser
echo [+] Checking Playwright Chromium browser...
python -m playwright install chromium

echo ==================================================================
echo [+] Launching Web Dashboard at http://127.0.0.1:5050 ...
echo ==================================================================

python run_app.py

if %errorlevel% neq 0 (
    echo.
    echo [-] Application stopped with an error code: %errorlevel%
    pause
)

