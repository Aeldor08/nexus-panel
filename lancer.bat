@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title NEXUS
rem  lancer.bat          : NEXUS demarre en arriere-plan, avec son icone pres de l'horloge (pas de fenetre noire)
rem  lancer.bat console  : l'ancienne fenetre noire (depannage : messages du serveur en direct)
rem  NEXUS utilise son propre Python (dossier runtime\) : il ne depend pas du Python installe sur Windows.
set "PYTHONNOUSERSITE=1"
set "PYTHONPATH="
set "PYTHONHOME="
rem L'icone vient de demander l'installation du Python prive : on la laisse se fermer d'abord
if "%NEXUS_ATTENDRE%"=="1" ping -n 3 127.0.0.1 >nul
set "NEXUS_ATTENDRE="

call :trouver
if not defined NX_PY (
    echo NEXUS n'est pas encore installe : lancement de installer.bat...
    call installer.bat
    call :trouver
    if not defined NX_PY exit /b 1
)

rem --- Python prive de NEXUS : installe une fois (telechargement verifie), refait seulement si sa version change ---
call :python_prive
call :trouver

rem --- Dependances : seulement si requirements.txt a change depuis la derniere installation ---
call :dependances
if errorlevel 1 (
    pause
    exit /b 1
)

rem --- Premiere configuration (mot de passe du deck, Discord) si elle n'a pas encore ete faite ---
if not exist "config.json" "%NX_PY%" configurer.py

if /i "%~1"=="console" goto console
if not exist "%NX_PYW%" goto console
rem --- NEXUS en arriere-plan : l'icone pres de l'horloge fait le reste (mises a jour, redemarrages, journal) ---
set "NEXUS_DEPUIS_LANCEUR=1"
start "" "%NX_PYW%" nexus.pyw
echo NEXUS demarre : son icone apparait pres de l'horloge, le navigateur s'ouvrira tout seul.
exit /b 0

rem ##CALAGE## Ne pas deplacer : quand une mise a jour remplace ce fichier pendant qu'une ancienne fenetre
rem NEXUS l'execute, cmd.exe continue de lire a l'octet ou il en etait (3480, juste apres la ligne
rem maj_demarrage.py). La ligne 'call :app' doit donc commencer a l'octet 3480 : ces lignes servent de cale
rem (verifie par outils\tests\test_superviseur.py).
rem ----------------------------------------------------------------------------------------------
rem ----------------------------------------------------------------------------------------------
rem ----------------------------------------------------------------------------------------------
rem ----------------------------------------------------------------------------------------------
rem ----------------------------------------------------------------------------------------------
rem ----------------------------------------------------------------------------------------------
rem ----------------------------------------------------------------------------------------------
rem --------------------
rem ===================== Mode console (ancienne fenetre noire) =====================
:console
call :lhm
echo.
echo Demarrage de NEXUS... le navigateur s'ouvrira tout seul quand il sera pret.
echo Garde cette fenetre ouverte : la fermer arrete NEXUS.
echo.
set "NEXUS_OPEN_BROWSER=1"
rem NEXUS_LANCEUR : app.py sait que ce script le relance (mises a jour, acces telephone)
set "NEXUS_LANCEUR=1"
set /a RESTARTS=0
:serveur
rem (ce repere sert aussi a une ancienne fenetre NEXUS qui redemarre apres une mise a jour : rien avant ne compte)
call :trouver
rem Mise a jour preparee depuis le panel : mise en place, test de demarrage, restauration auto si echec
if exist "maj\en_cours.json" "%NX_PY%" maj_demarrage.py
call :app
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
exit /b 0

rem ===================== Sous-programmes =====================
:trouver
rem Le Python de NEXUS : runtime\ (Python prive), sinon l'ancienne installation .venv\
set "NX_PY="
set "NX_PYW="
set "NX_ENV="
if exist "runtime\python.exe" (
    set "NX_PY=runtime\python.exe"
    set "NX_PYW=runtime\pythonw.exe"
    set "NX_ENV=runtime"
    exit /b 0
)
if exist ".venv\Scripts\python.exe" (
    set "NX_PY=.venv\Scripts\python.exe"
    set "NX_PYW=.venv\Scripts\pythonw.exe"
    set "NX_ENV=.venv"
)
exit /b 0

:app
call :trouver
"%NX_PY%" app.py
exit /b %errorlevel%

:python_prive
powershell -NoProfile -ExecutionPolicy Bypass -File "outils\installer_python.ps1" -SiBesoin
if not errorlevel 1 exit /b 0
echo.
echo [AVERTISSEMENT] Le Python prive de NEXUS n'a pas pu etre installe (message au-dessus).
if exist "runtime\python.exe" (
    echo NEXUS continue avec son Python actuel ; nouvel essai au prochain lancement.
) else (
    echo NEXUS continue avec l'ancienne installation ^(.venv^) ; nouvel essai au prochain lancement.
)
ping -n 6 127.0.0.1 >nul
exit /b 0

:dependances
fc /b requirements.txt "%NX_ENV%\requirements.installe" >nul 2>&1
if not errorlevel 1 exit /b 0
echo Installation / verification des dependances...
"%NX_PY%" -m pip install --disable-pip-version-check --no-warn-script-location -q -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] L'installation des dependances a echoue ^(connexion Internet ?^).
    exit /b 1
)
copy /y requirements.txt "%NX_ENV%\requirements.installe" >nul
exit /b 0

:lhm
rem LibreHardwareMonitor (temperatures CPU / disques), demarre en administrateur
set "LHM=%~dp0LibreHardwareMonitor\LibreHardwareMonitor.exe"
if exist "%LHM%" if not exist "%~dp0LibreHardwareMonitor\LibreHardwareMonitor.config" copy /y "%~dp0outils\LibreHardwareMonitor.config" "%~dp0LibreHardwareMonitor\" >nul
if not exist "%LHM%" (
    echo [INFO] LibreHardwareMonitor absent : temperatures CPU indisponibles. Voir README.md
    exit /b 0
)
tasklist /fi "imagename eq LibreHardwareMonitor.exe" 2>nul | find /i "LibreHardwareMonitor.exe" >nul
if not errorlevel 1 (
    echo LibreHardwareMonitor tourne deja.
    exit /b 0
)
echo Demarrage de LibreHardwareMonitor : acceptez la fenetre administrateur de Windows...
powershell -NoProfile -Command "try { Start-Process -FilePath $env:LHM -WorkingDirectory (Split-Path $env:LHM) -Verb RunAs -ErrorAction Stop } catch { Write-Host '[AVERTISSEMENT] LibreHardwareMonitor non demarre : temperatures CPU indisponibles.' }"
exit /b 0
