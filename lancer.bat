@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title NEXUS

rem --- Pas encore installe ? On lance l'installation (environnement Python + configuration) ---
if not exist ".venv\Scripts\python.exe" (
    echo NEXUS n'est pas encore installe : lancement de installer.bat...
    call installer.bat
    if not exist ".venv\Scripts\python.exe" exit /b 1
)

rem --- Trouver Python : py, python, puis les dossiers d'installation habituels ---
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>&1 && set "PY=python"
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PY="%%D\python.exe""
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set "PY="%%D\python.exe""
if not defined PY (
    echo [ERREUR] Python 3 est introuvable.
    echo Installez-le depuis https://www.python.org/downloads/ en cochant "Add python.exe to PATH".
    pause
    exit /b 1
)
echo Python utilise : %PY%

rem --- Environnement virtuel local, cree au premier lancement ---
if not exist ".venv\Scripts\python.exe" (
    echo Creation de l'environnement virtuel...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer .venv
        pause
        exit /b 1
    )
)

echo Installation / verification des dependances...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] L'installation des dependances a echoue.
    pause
    exit /b 1
)

rem --- Premiere configuration (mot de passe du deck, Discord) si elle n'a pas encore ete faite ---
if not exist "config.json" ".venv\Scripts\python.exe" configurer.py

rem --- LibreHardwareMonitor (temperatures CPU / disques), demarre en administrateur ---
set "LHM=%~dp0LibreHardwareMonitor\LibreHardwareMonitor.exe"
if exist "%LHM%" if not exist "%~dp0LibreHardwareMonitor\LibreHardwareMonitor.config" copy /y "%~dp0outils\LibreHardwareMonitor.config" "%~dp0LibreHardwareMonitor\" >nul
if exist "%LHM%" (
    tasklist /fi "imagename eq LibreHardwareMonitor.exe" 2>nul | find /i "LibreHardwareMonitor.exe" >nul
    if errorlevel 1 (
        echo Demarrage de LibreHardwareMonitor : acceptez la fenetre administrateur de Windows...
        powershell -NoProfile -Command "try { Start-Process -FilePath $env:LHM -WorkingDirectory (Split-Path $env:LHM) -Verb RunAs -ErrorAction Stop } catch { Write-Host '[AVERTISSEMENT] LibreHardwareMonitor non demarre : temperatures CPU indisponibles.' }"
    ) else (
        echo LibreHardwareMonitor tourne deja.
    )
) else (
    echo [INFO] LibreHardwareMonitor absent : temperatures CPU indisponibles. Voir README.md
)

rem --- Serveur ; NEXUS ouvre lui-meme le navigateur des qu'il est pret (une seule fois) ---
rem --- Il redemarre tout seul s'il s'arrete de facon inattendue (5 fois max) ---
echo.
echo Demarrage de NEXUS... le navigateur s'ouvrira tout seul quand il sera pret.
echo Garde cette fenetre ouverte : la fermer arrete NEXUS.
echo.
set "NEXUS_OPEN_BROWSER=1"
rem NEXUS_LANCEUR : app.py sait que ce script le relance (mises a jour, acces telephone)
set "NEXUS_LANCEUR=1"
set /a RESTARTS=0
:serveur
rem Mise a jour preparee depuis le panel : mise en place, test de demarrage, restauration auto si echec
if exist "maj\en_cours.json" ".venv\Scripts\python.exe" maj_demarrage.py
".venv\Scripts\python.exe" app.py
set "RC=%errorlevel%"
set "NEXUS_OPEN_BROWSER=0"
if %RC% EQU 0 goto fin
rem Code 4 : port deja utilise (message explicite affiche par NEXUS) : inutile de reessayer
if %RC% EQU 4 goto fin
rem Code 3 : redemarrage demande par NEXUS (ex. activation de l'acces telephone)
if %RC% EQU 3 (
    echo.
    echo Redemarrage de NEXUS...
    goto serveur
)
set /a RESTARTS+=1
if %RESTARTS% GEQ 5 goto trop
echo.
echo [ATTENTION] Le serveur s'est arrete de facon inattendue. Redemarrage %RESTARTS%/4 dans 3 s...
ping -n 4 127.0.0.1 >nul
goto serveur

:trop
echo [ERREUR] Le serveur s'est arrete 5 fois de suite. Lis le message d'erreur au-dessus
echo (fais une capture d'ecran de cette fenetre pour demander de l'aide).

:fin
echo.
echo Le serveur s'est arrete.
pause