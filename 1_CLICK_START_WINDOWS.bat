@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title Coreteron Instagram Suite - Windows 1-Click Launcher

echo ==================================================================
echo          CORETERON INSTAGRAM SUITE - WINDOWS 1-CLICK LAUNCHER
echo ==================================================================
echo.

call setup_and_run.bat

if %errorlevel% neq 0 (
    echo.
    echo [-] Application stopped with exit code %errorlevel%.
)
echo.
echo Press any key to close this window...
pause >nul
