@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title NEXUS - creer la version portable

echo.
echo  NEXUS - creation de la version portable
echo  ======================================
echo.

rem --- Python de build : systeme 3.11/3.12, sinon Python prive de NEXUS ---
set "PY="
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=py -3.11"
if not defined PY (
    py -3.12 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY=py -3.12"
)
if not defined PY (
    python -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    if exist "runtime\python.exe" set "PY=runtime\python.exe"
)
if not defined PY (
    echo [ERREUR] Python est introuvable.
    echo Lance d'abord installer.bat pour installer le Python prive de NEXUS,
    echo ou installe Python 3.11/3.12 depuis python.org.
    echo.
    pause
    exit /b 1
)

rem --- Environnement de build separe (ne touche pas au Python prive runtime\) ---
if not exist ".venv-build\Scripts\python.exe" (
    echo Creation de l'environnement de build .venv-build...
    %PY% -m venv .venv-build
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer .venv-build.
        pause
        exit /b 1
    )
)
set "BUILD=.venv-build\Scripts\python.exe"

rem --- Dependances de build : installees seulement si les requirements changent ---
"%BUILD%" -c "import hashlib,pathlib,sys; p=pathlib.Path('requirements-native.txt'); q=pathlib.Path('requirements.txt'); m=pathlib.Path('.venv-build/.requirements.sha256'); h=hashlib.sha256(p.read_bytes()+q.read_bytes()).hexdigest(); sys.exit(0 if m.is_file() and m.read_text(encoding='utf-8').strip()==h else 1)"
if errorlevel 1 (
    echo Installation des dependances de build ^(1 a 3 minutes la premiere fois^)...
    "%BUILD%" -m pip install --disable-pip-version-check --upgrade pip
    "%BUILD%" -m pip install --disable-pip-version-check -r requirements-native.txt
    if errorlevel 1 (
        echo [ERREUR] Installation des dependances de build impossible ^(Internet ?^).
        pause
        exit /b 1
    )
    "%BUILD%" -c "import hashlib,pathlib; p=pathlib.Path('requirements-native.txt'); q=pathlib.Path('requirements.txt'); h=hashlib.sha256(p.read_bytes()+q.read_bytes()).hexdigest(); pathlib.Path('.venv-build/.requirements.sha256').write_text(h, encoding='utf-8')"
)
if errorlevel 1 (
    echo [ERREUR] Ecriture de la marque des dependances impossible.
    pause
    exit /b 1
)

set "CIBLE=--portable"
if /i "%~1"=="--installer" set "CIBLE=--installer --portable"

echo.
echo Construction de l'executable et du ZIP portable...
echo ^(NEXUS doit etre ferme ; les tests sont lances avant le build.^)
echo.
"%BUILD%" outils\build_native.py %CIBLE%
if errorlevel 1 (
    echo.
    echo [ERREUR] La construction a echoue. Lis le message ci-dessus.
    pause
    exit /b 1
)

echo.
echo [OK] Archive portable creee dans :
dir /b "dist\NEXUS-Portable-*.zip"
echo.
start "" explorer "dist"
pause
