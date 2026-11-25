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

rem --- 1. Python prive de NEXUS (dossier runtime\) : rien a installer sur Windows, aucune dependance au Python du PC ---
set "PYTHONNOUSERSITE=1"
set "PYTHONPATH="
set "PYTHONHOME="
powershell -NoProfile -ExecutionPolicy Bypass -File "outils\installer_python.ps1" -SiBesoin
if errorlevel 1 goto noruntime
set "PY_NX=runtime\python.exe"

rem --- 2. Dependances a jour (deja installees par l'etape 1, sauf si requirements.txt a change depuis) ---
fc /b requirements.txt "runtime\requirements.installe" >nul 2>&1
if errorlevel 1 (
    echo Installation des dependances...
    "%PY_NX%" -m pip install --disable-pip-version-check --no-warn-script-location -q -r requirements.txt
    if errorlevel 1 goto nopip
    copy /y requirements.txt "runtime\requirements.installe" >nul
)
echo [OK] Python prive et dependances prets

rem --- 3. LibreHardwareMonitor (facultatif) : on prepare sa configuration s'il est la ---
call :lhmconfig

rem --- 4. Verification du materiel (GPU NVIDIA, LibreHardwareMonitor) ---
echo.
"%PY_NX%" -c "import stats; [print(l) for l in stats.Sensors().hardware_report(wait_lhm=1)]"

rem --- 5. Premiere configuration (mot de passe, Discord) ---
if not exist "config.json" (
    "%PY_NX%" configurer.py
) else (
    echo.
    echo [OK] config.json existe deja ^(pour le modifier : configurer.bat^)
)

rem --- 6. Raccourci sur le Bureau ---
echo.
choice /c ON /n /m "Creer un raccourci NEXUS sur le Bureau ? [O = oui / N = non] "
if errorlevel 2 goto done
powershell -NoProfile -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'NEXUS.lnk')); $s.TargetPath=(Join-Path $env:NX_DIR 'runtime\pythonw.exe'); $s.Arguments='nexus.pyw'; $s.WorkingDirectory=$env:NX_DIR; $s.IconLocation=(Join-Path $env:NX_DIR 'panel.ico'); $s.Description='NEXUS - tableau de bord du PC'; $s.Save(); Write-Host '[OK] Raccourci NEXUS cree sur le Bureau'"

:done
echo.
echo  ==========================================================
echo    Installation terminee !
echo    Pour ouvrir NEXUS : raccourci NEXUS du Bureau ^(ou lancer.bat^)
echo    NEXUS tourne en arriere-plan : son icone est pres de l'horloge
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

:noruntime
echo.
echo [ERREUR] Le Python prive de NEXUS n'a pas pu etre installe ^(message au-dessus^).
echo Verifie ta connexion Internet ^(NEXUS telecharge Python 14 Mo sur nuget.org, une seule fois^)
echo et que le dossier n'est pas en lecture seule, puis relance installer.bat.
pause
exit /b 1

:nopip
echo [ERREUR] L'installation des dependances a echoue.
echo Verifie ta connexion Internet puis relance installer.bat.
pause
exit /b 1
