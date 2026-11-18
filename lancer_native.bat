@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title NEXUS (fenetre native)

rem --- Pas encore installe ? On lance l'installation de base (Python + .venv) ---
if not exist ".venv\Scripts\python.exe" (
    echo NEXUS n'est pas encore installe : lancement de installer.bat...
    call installer.bat
    if not exist ".venv\Scripts\python.exe" exit /b 1
)

set "PY=.venv\Scripts\python.exe"

rem --- Dependances de base (si requirements.txt a change) ---
"%PY%" -c "import hashlib,pathlib,sys; p=pathlib.Path('requirements.txt'); m=pathlib.Path('.venv/.requirements.sha256'); sys.exit(0 if m.is_file() and m.read_text(encoding='utf-8').strip()==hashlib.sha256(p.read_bytes()).hexdigest() else 1)"
if errorlevel 1 (
    echo Installation des dependances de base...
    "%PY%" -m pip install --disable-pip-version-check -q -r requirements.txt
    if errorlevel 1 (
        echo [ERREUR] L'installation des dependances a echoue.
        pause
        exit /b 1
    )
    "%PY%" -c "import hashlib,pathlib; pathlib.Path('.venv/.requirements.sha256').write_text(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest(), encoding='utf-8')"
)

rem --- Dependances de la fenetre native (pywebview, pystray, winotify) ---
"%PY%" -c "import hashlib,pathlib,sys; p=pathlib.Path('requirements-native.txt'); m=pathlib.Path('.venv/.requirements-native.sha256'); sys.exit(0 if m.is_file() and m.read_text(encoding='utf-8').strip()==hashlib.sha256(p.read_bytes()).hexdigest() else 1)"
if errorlevel 1 (
    echo Installation des dependances de la fenetre native...
    "%PY%" -m pip install --disable-pip-version-check -q -r requirements-native.txt
    if errorlevel 1 (
        echo [ERREUR] L'installation des dependances natives a echoue.
        pause
        exit /b 1
    )
    "%PY%" -c "import hashlib,pathlib; pathlib.Path('.venv/.requirements-native.sha256').write_text(hashlib.sha256(pathlib.Path('requirements-native.txt').read_bytes()).hexdigest(), encoding='utf-8')"
)

rem --- Commandes en console (le resultat doit rester visible) ---
if /i "%~1"=="--install-autostart" goto console
if /i "%~1"=="--remove-autostart" goto console

rem --- Fenetre native : pythonw + start pour ne pas laisser de console ouverte ---
set "PYW=.venv\Scripts\pythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" nexus_launcher.py %*
    exit /b 0
)
"%PY%" nexus_launcher.py %*
if errorlevel 1 pause
exit /b 0

:console
"%PY%" nexus_launcher.py %*
if errorlevel 1 pause
