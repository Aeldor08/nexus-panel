@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title NEXUS - construction (exe, installeur, portable)
rem Double-clic : construit tout dans dist\ (voir outils\build.py). Options transmises telles quelles, par ex. :
rem   Creer-NEXUS-Portable.bat --sans-installeur      (portable seulement, Inno Setup 6 non requis)

set "PY="
if exist ".venv-build\Scripts\python.exe" set "PY=.venv-build\Scripts\python.exe"
if not defined PY (
    py -3.12 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY=py -3.12"
)
if not defined PY (
    py -3.11 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY=py -3.11"
)
if not defined PY (
    echo [ERREUR] Python 3.11 ou 3.12 est introuvable : installe-le depuis python.org.
    pause
    exit /b 1
)

%PY% outils\build.py %*
if errorlevel 1 (
    echo.
    echo [ERREUR] La construction a echoue : lis le message ci-dessus.
    pause
    exit /b 1
)
echo.
start "" explorer "dist"
pause
