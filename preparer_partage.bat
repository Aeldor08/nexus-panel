@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title NEXUS - preparer une copie a partager
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>&1 && set "PY=python"
if not defined PY (
    echo [ERREUR] Python introuvable : lance d'abord installer.bat
    pause
    exit /b 1
)
%PY% outils\preparer_partage.py
echo.
pause
