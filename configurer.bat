@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title NEXUS - configuration
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if exist "runtime\python.exe" set "PY=runtime\python.exe"
set "PYTHONNOUSERSITE=1"
if not defined PY (
    echo NEXUS n'est pas encore installe : lance d'abord installer.bat
    pause
    exit /b 1
)
"%PY%" configurer.py
echo.
echo Si NEXUS est ouvert, redemarre-le pour appliquer les changements
echo ^(clic droit sur son icone pres de l'horloge ^> Redemarrer NEXUS^).
pause
