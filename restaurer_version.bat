@echo off
setlocal
cd /d "%~dp0"
title NEXUS - restaurer une version
chcp 65001 >nul

rem Le panel doit etre ferme (sinon ses fichiers sont en cours d'utilisation)
netstat -ano | find "127.0.0.1:8000" | find "LISTENING" >nul
if not errorlevel 1 (
    echo.
    echo   Le panel est encore ouvert. Quitte-le ^(clic droit sur son icone pres de l'horloge ^> Quitter NEXUS,
    echo   ou ferme sa fenetre noire^), puis relance ce script.
    echo.
    pause
    exit /b 1
)
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if exist "runtime\python.exe" set "PY=runtime\python.exe"
set "PYTHONNOUSERSITE=1"
if not defined PY (
    echo   Environnement introuvable : lance d'abord lancer.bat une fois.
    pause
    exit /b 1
)
"%PY%" version.py
echo.
pause