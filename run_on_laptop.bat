@echo off
title MovieBox Mesh Host
cd /d "%~dp0"
echo ==================================================
echo 🎬 Starting MovieBox Mesh on Dell Latitude...
echo ==================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Python is not found. Please install Python from python.org
        pause
        exit /b 1
    ) else (
        python3 mesh_node.py
    )
) else (
    python mesh_node.py
)
pause
