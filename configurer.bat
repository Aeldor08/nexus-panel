@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title NEXUS - configuration
if not exist ".venv\Scripts\python.exe" (
    echo NEXUS n'est pas encore installe : lance d'abord installer.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" configurer.py
echo.
echo Si NEXUS est ouvert, ferme sa fenetre noire et relance-le pour appliquer les changements.
pause
