@echo off
setlocal
cd /d "%~dp0"
title NEXUS - restaurer une version
chcp 65001 >nul

rem Le panel doit etre ferme (sinon ses fichiers sont en cours d'utilisation)
netstat -ano | find "127.0.0.1:8000" | find "LISTENING" >nul
if not errorlevel 1 (
    echo.
    echo   Le panel est encore ouvert. Ferme sa fenetre noire, puis relance ce script.
    echo.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    echo   Environnement introuvable : lance d'abord lancer.bat une fois.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" version.py
echo.
pause