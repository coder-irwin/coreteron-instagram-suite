@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
setlocal enabledelayedexpansion

cd /d "%~dp0"
title Coreteron Instagram Automation Suite

echo ==================================================================
echo     CORETERON INSTAGRAM SUITE - AUTONOMOUS INSTALLER (WINDOWS)
echo ==================================================================
echo Working directory: %~dp0
echo.

REM 1. Detect Python Interpreter
set "PYTHON_CMD="

REM Check py launcher
where py >nul 2>&1
if !errorlevel! equ 0 set "PYTHON_CMD=py"

REM Check python in PATH
if "!PYTHON_CMD!"=="" (
    where python >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_CMD=python"
)

REM Check common local and system install directories
if "!PYTHON_CMD!"=="" (
    if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
    if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
    if exist "C:\Program Files\Python311\python.exe" set "PYTHON_CMD=C:\Program Files\Python311\python.exe"
    if exist "C:\Program Files\Python312\python.exe" set "PYTHON_CMD=C:\Program Files\Python312\python.exe"
    if exist "C:\Program Files\Python310\python.exe" set "PYTHON_CMD=C:\Program Files\Python310\python.exe"
)

REM 2. Auto-Install Python 3.11 if completely missing (no admin rights needed)
if "!PYTHON_CMD!"=="" (
    echo [!] Python is not detected on your system.
    echo [*] Downloading and installing official Python 3.11 in background...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host 'Downloading Python 3.11...'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile 'python_setup.exe'; Write-Host 'Installing Python (silent, no admin required)...'; Start-Process -FilePath 'python_setup.exe' -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0' -Wait; Remove-Item 'python_setup.exe'"
    
    if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
        set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
    ) else if exist "C:\Program Files\Python311\python.exe" (
        set "PYTHON_CMD=C:\Program Files\Python311\python.exe"
    ) else (
        where python >nul 2>&1
        if !errorlevel! equ 0 set "PYTHON_CMD=python"
    )
)

if "!PYTHON_CMD!"=="" (
    echo [-] Python installation could not be completed automatically.
    echo [!] Please install Python manually from: https://www.python.org/downloads/
    echo [!] Make sure to check the box: 'Add python.exe to PATH'
    pause
    exit /b 1
)

echo [+] Python interpreter:
"!PYTHON_CMD!" --version
echo.

REM 3. Create Isolated Virtual Environment
if not exist ".venv" (
    echo [+] Creating isolated virtual environment (.venv)...
    "!PYTHON_CMD!" -m venv .venv
)

REM 4. Locate Virtual Environment Executables
set "VENV_PYTHON=.venv\Scripts\python.exe"
if not exist "!VENV_PYTHON!" (
    set "VENV_PYTHON=!PYTHON_CMD!"
)

REM 5. Install / Update Dependencies
echo [+] Verifying and installing required packages...
"!VENV_PYTHON!" -m pip install -q --upgrade pip setuptools wheel
"!VENV_PYTHON!" -m pip install -q -r requirements.txt

REM 6. Install Playwright Chromium Browser
echo [+] Checking Playwright Chromium browser binary...
"!VENV_PYTHON!" -m playwright install chromium

REM 7. Ensure .env exists
if not exist ".env" (
    if exist ".env.example" (
        echo [+] Setting default configuration from .env.example...
        copy .env.example .env >nul
    )
)

REM 8. Launch Dashboard and Open Browser
echo ==================================================================
echo [+] Launching Web Dashboard at http://127.0.0.1:5050 ...
echo ==================================================================
echo.

start "" "http://127.0.0.1:5050"
"!VENV_PYTHON!" app.py

if !errorlevel! neq 0 (
    echo.
    echo [-] Application stopped with an exit code: !errorlevel!
    pause
)
