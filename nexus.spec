# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller de NEXUS (Windows x64, onedir).

Construit dist/NEXUS/NEXUS.exe à partir de nexus_launcher.py. L'installeur
Inno Setup (installer.iss) empaquette ensuite ce dossier. Utiliser
outils/build_native.py plutôt que PyInstaller directement.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

BASE = Path(SPECPATH).resolve()
VERSION = (BASE / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
_parts = [int(x) for x in (VERSION.split(".") + ["0", "0", "0"])[:4]]
_file_version = tuple(_parts[:4])

datas = []
binaries = []
hiddenimports = []


def collect(package: str) -> None:
    try:
        d, b, h = collect_all(package, include_py_files=True)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
    except Exception as exc:                       # paquet facultatif / hook absent
        print(f"[spec] collect_all({package}) ignoré : {exc}")


# Dépendances qui font des imports dynamiques (plateformes, backends, hooks COM).
for package in ("webview", "pystray", "winotify", "pycaw", "comtypes", "discord", "aiohttp",
                "keyring", "qrcode", "uvicorn", "fastapi", "starlette", "pydantic", "pydantic_core"):
    collect(package)

# WinRT : le paquet winrt-runtime fournit son propre hook PyInstaller (__pyinstaller).
hiddenimports += [
    "winrt.system", "winrt.runtime", "winrt._winrt",
    "winrt.windows.foundation", "winrt.windows.foundation.collections",
    "winrt.windows.media.control", "winrt.windows.storage.streams",
    "pynvml", "PIL._webp",
    "keyring.backends.Windows", "qrcode.image.svg",
    "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on",
    "sqlite3", "ssl", "certifi",
    # backend Windows de keyring (jeton GitHub) : imports internes à win32ctypes
    "win32ctypes.core._common", "win32ctypes.core._authentication",
    "win32ctypes.core._time", "win32ctypes.core._system_information",
    "win32ctypes.core._resource", "win32ctypes.core._dll",
    "win32ctypes.pywin32.win32cred", "win32ctypes.pywin32.win32api",
]

# Fichiers/données lus au démarrage ou servis par l'interface.
for name in ("static", "profils", "docs"):
    path = BASE / name
    if path.is_dir():
        datas.append((str(path), name))
for name in ("panel.ico", "VERSION", "CHANGELOG.md", "LICENSE", "THIRD_PARTY.md",
             "README.md", "NE_PAS_PARTAGER.md", "DEPOT", "config.example.json",
             "deck.example.json", "jeux.example.json", "requirements.txt",
             "requirements-native.txt", "actions/exemple.bat"):
    path = BASE / name
    if path.is_file():
        dest = str(Path(name).parent) if Path(name).parent != Path(".") else "."
        datas.append((str(path), dest))
for name in ("outils/LibreHardwareMonitor.config", "outils/appliquer_maj.ps1"):
    path = BASE / name
    if path.is_file():
        datas.append((str(path), "outils"))

try:
    datas += collect_data_files("certifi")
except Exception:
    pass

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_file_version, prodvers=_file_version, mask=0x3F, flags=0x0,
                      OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "NEXUS"),
            StringStruct("FileDescription", "NEXUS — tableau de bord du PC"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "NEXUS"),
            StringStruct("LegalCopyright", "MIT — voir LICENSE"),
            StringStruct("OriginalFilename", "NEXUS.exe"),
            StringStruct("ProductName", "NEXUS"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

a = Analysis(
    [str(BASE / "nexus_launcher.py")],
    pathex=[str(BASE)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "tests", "outils.tests", "tkinter", "matplotlib", "numpy"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NEXUS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE / "panel.ico"),
    version=version_info,
    uac_admin=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NEXUS",
)
