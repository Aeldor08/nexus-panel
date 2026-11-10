@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "NX_DIR=%~dp0"
title NEXUS - installation

echo.
echo  ==========================================================
echo    NEXUS - installation
echo  ==========================================================
echo.

rem --- 1. Trouver Python 3 : py, python, puis les dossiers d'installation habituels ---
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>&1 && set "PY=python"
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PY="%%D\python.exe""
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set "PY="%%D\python.exe""
if not defined PY goto nopython

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 goto oldpython
echo [OK] Python trouve : %PY%

rem --- 2. Environnement virtuel (.venv) : une copie de Python rien que pour NEXUS ---
if exist ".venv\Scripts\python.exe" (
    echo [OK] Environnement virtuel deja present
) else (
    echo Creation de l'environnement virtuel .venv ...
    %PY% -m venv .venv
    if errorlevel 1 goto novenv
    echo [OK] Environnement virtuel cree
)

rem --- 3. Dependances (FastAPI, psutil, discord.py...) ---
echo.
echo Installation des dependances (1 a 3 minutes la premiere fois)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip >nul 2>&1
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto nopip
echo [OK] Dependances installees

rem --- 4. LibreHardwareMonitor (facultatif) : on prepare sa configuration s'il est la ---
call :lhmconfig

rem --- 5. Verification du materiel (GPU NVIDIA, LibreHardwareMonitor) ---
echo.
".venv\Scripts\python.exe" -c "import stats; [print(l) for l in stats.Sensors().hardware_report(wait_lhm=1)]"

rem --- 6. Premiere configuration (mot de passe, Discord) ---
if not exist "config.json" (
    ".venv\Scripts\python.exe" configurer.py
) else (
    echo.
    echo [OK] config.json existe deja ^(pour le modifier : configurer.bat^)
)

rem --- 7. Raccourci sur le Bureau ---
echo.
choice /c ON /n /m "Creer un raccourci NEXUS sur le Bureau ? [O = oui / N = non] "
if errorlevel 2 goto done
powershell -NoProfile -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'NEXUS.lnk')); $s.TargetPath=(Join-Path $env:NX_DIR 'lancer.bat'); $s.WorkingDirectory=$env:NX_DIR; $s.IconLocation=(Join-Path $env:NX_DIR 'panel.ico'); $s.Description='NEXUS - tableau de bord du PC'; $s.Save(); Write-Host '[OK] Raccourci NEXUS cree sur le Bureau'"

:done
echo.
echo  ==========================================================
echo    Installation terminee !
echo    Pour ouvrir NEXUS : double-clic sur lancer.bat
echo    ^(ou sur le raccourci NEXUS du Bureau^)
echo  ==========================================================
echo.
pause
exit /b 0

:lhmconfig
if not exist "LibreHardwareMonitor\LibreHardwareMonitor.exe" (
    echo [INFO] LibreHardwareMonitor absent : facultatif, voir l'etape 5 du README.
    exit /b 0
)
if not exist "LibreHardwareMonitor\LibreHardwareMonitor.config" (
    copy /y "outils\LibreHardwareMonitor.config" "LibreHardwareMonitor\LibreHardwareMonitor.config" >nul
    echo [OK] LibreHardwareMonitor configure ^(serveur web local sur le port 8085^)
) else (
    echo [OK] LibreHardwareMonitor present
)
exit /b 0

:nopython
echo [ERREUR] Python 3 est introuvable sur ce PC.
echo.
echo  1. Va sur https://www.python.org/downloads/ et clique sur "Download Python".
echo  2. Lance le fichier telecharge et COCHE la case "Add python.exe to PATH" en bas,
echo     puis clique sur "Install Now".
echo  3. Ferme cette fenetre et relance installer.bat.
echo.
pause
exit /b 1

:oldpython
echo [ERREUR] Ta version de Python est trop ancienne : NEXUS a besoin de Python 3.10 ou plus recent.
echo Installe la derniere version depuis https://www.python.org/downloads/ puis relance installer.bat.
pause
exit /b 1

:novenv
echo [ERREUR] Impossible de creer l'environnement virtuel .venv
echo Verifie que le dossier n'est pas en lecture seule ^(ou deplace NEXUS dans Documents^).
pause
exit /b 1

:nopip
echo [ERREUR] L'installation des dependances a echoue.
echo Verifie ta connexion Internet puis relance installer.bat.
pause
exit /b 1
