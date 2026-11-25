"""Chemins de NEXUS : ressources en lecture seule et données inscriptibles.

Deux modes :

- **source** (``python app.py``) : tout reste dans le dossier du projet, comme avant.
  Pratique pour développer et pour les tests.
- **gelé** (``NEXUS.exe``) : les ressources (``static/``, ``profils/`` fournis, exemples) sont
  dans le dossier d'installation / ``_MEIPASS``, et les données vont dans
  ``%LOCALAPPDATA%\\NEXUS``. L'application peut donc être installée dans ``Program Files``
  ou un dossier en lecture seule.

Variables d'environnement :

- ``NEXUS_DATA_DIR`` : force le dossier des données (tests, mode portable, sauvegarde).
- ``NEXUS_APP_DIR`` : force le dossier des ressources (tests).
- ``NEXUS_PORTABLE=1`` : en mode gelé, données à côté de l'exécutable.

Au premier lancement en mode gelé, les anciennes données posées à côté de l'exécutable
(``config.json``, ``data/``, ``actions/``…) sont copiées dans le nouveau dossier, sans
jamais écraser un fichier existant. Un marqueur ``.layout-v2`` évite de recommencer.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

APP_NAME = "NEXUS"
# PyInstaller (sys.frozen) et Nuitka (__compiled__) posent l'un ou l'autre.
FROZEN = bool(getattr(sys, "frozen", False)) or "__compiled__" in globals()


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser().resolve() if value else None


def _app_dir() -> Path:
    override = _env_path("NEXUS_APP_DIR")
    if override:
        return override
    if FROZEN:
        # PyInstaller --onedir : _MEIPASS pointe vers _internal ; --onefile : vers le dossier
        # temporaire d'extraction. Dans les deux cas, c'est là que sont les ressources.
        meipass = getattr(sys, "_MEIPASS", None)
        return Path(meipass).resolve() if meipass else Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _user_root() -> Path:
    override = _env_path("NEXUS_DATA_DIR")
    if override:
        return override
    if FROZEN:
        if os.environ.get("NEXUS_PORTABLE") == "1":
            return Path(sys.executable).resolve().parent
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return (base / APP_NAME).resolve()
    return APP_DIR


APP_DIR = _app_dir()
USER_ROOT = _user_root()

# --- Données inscriptibles -------------------------------------------------
DATA_DIR = USER_ROOT / "data"
CONFIG_FILE = USER_ROOT / "config.json"
DECK_FILE = USER_ROOT / "deck.json"
JEUX_FILE = USER_ROOT / "jeux.json"
FAN_NAMES_FILE = DATA_DIR / "fan_names.json"
LOG_DIR = USER_ROOT / "logs"
LOG_FILE = LOG_DIR / "nexus.log"
ACTIONS_DIR = USER_ROOT / "actions"
PROFILES_DIR = USER_ROOT / "profils"
MAJ_DIR = USER_ROOT / "maj"
SAUVEGARDES_DIR = USER_ROOT / "sauvegardes-maj"
VERSIONS_DIR = USER_ROOT / "versions"
RUNTIME_FILE = USER_ROOT / "runtime.json"
BACKUP_DIR = DATA_DIR / "backups"

# --- Ressources en lecture seule -------------------------------------------
STATIC_DIR = APP_DIR / "static"
BUNDLED_PROFILES_DIR = APP_DIR / "profils"
DEPOT_FILE = APP_DIR / "DEPOT"
DECK_EXAMPLE = APP_DIR / "deck.example.json"
JEUX_EXAMPLE = APP_DIR / "jeux.example.json"
ACTIONS_EXAMPLE = APP_DIR / "actions" / "exemple.bat"

# Dossier d'installation (exe + LHM + éventuels fichiers portables) et ancien emplacement
# des données. En mode source, les deux valent le dossier du projet.
INSTALL_DIR = Path(sys.executable).resolve().parent if FROZEN else APP_DIR
LEGACY_DIR = INSTALL_DIR

_LAYOUT_MARKER = USER_ROOT / ".layout-v2"


MESSAGES: list[str] = []  # messages de prepare() (migration…), recopiés dans le journal une fois celui-ci ouvert


def _dire(message: str) -> None:
    """Écrit sur la console si elle existe (pythonw peut avoir stdout/stderr à None)."""
    MESSAGES.append(message)
    try:
        print(message, flush=True)
    except Exception:
        pass


def _copier_fichier(src: Path, dst: Path) -> bool:
    if not src.is_file() or dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _copier_dossier(src: Path, dst: Path) -> bool:
    if not src.is_dir() or dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)
    return True


def _copier_depuis(source: Path, dossiers: tuple[str, ...]) -> list[str]:
    """Copie les données d'une ancienne installation vers USER_ROOT, sans jamais écraser ni modifier l'original
    (qui reste donc une sauvegarde complète)."""
    copied: list[str] = []
    for name in ("config.json", "deck.json", "jeux.json", "fan_names.json", ".env"):
        if _copier_fichier(source / name, USER_ROOT / name):
            copied.append(name)
    for name in dossiers:
        if _copier_dossier(source / name, USER_ROOT / name):
            copied.append(name + "/")
    # Profils : on copie aussi les profils officiels de l'ancien dossier (l'utilisateur a pu
    # les modifier). Les profils officiels manquants seront ajoutés ensuite par
    # _copier_profils_fournis(), sans écraser ceux qui viennent d'être copiés.
    old_profiles = source / "profils"
    if old_profiles.is_dir():
        for folder in old_profiles.iterdir():
            if not folder.is_dir() or folder.name.startswith(("_", ".")):
                continue
            if _copier_dossier(folder, PROFILES_DIR / folder.name):
                copied.append(f"profils/{folder.name}/")
    if copied:
        _LAYOUT_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _LAYOUT_MARKER.write_text("Migration depuis " + str(source) + " le " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n", encoding="utf-8")
    return copied


def _migrer_anciennes_donnees() -> list[str]:
    """Ancienne version exe : données posées à côté de l'exe, copiées vers USER_ROOT."""
    if not FROZEN or LEGACY_DIR.resolve() == USER_ROOT.resolve() or _LAYOUT_MARKER.exists():
        return []
    return _copier_depuis(LEGACY_DIR, ("data", "logs", "actions", "versions", "sauvegardes-maj", "maj"))


# --- Ancienne version source (dossier avec lancer.bat) ------------------------------------------------
IMPORTER_ENV = "NEXUS_IMPORTER"  # posé par « NEXUS.exe --importer <dossier> »


def est_version_source(dossier: Path) -> bool:
    """Un dossier de la version source de NEXUS qui contient des données à reprendre."""
    try:
        return (
            (dossier / "app.py").is_file()
            and (dossier / "nexus.pyw").is_file()
            and ((dossier / "config.json").is_file() or (dossier / "data" / "nexus.db").is_file())
        )
    except OSError:
        return False


def _raccourci_bureau() -> Path | None:
    """Dossier visé par le raccourci « NEXUS » du Bureau créé par installer.bat (version source)."""
    if os.name != "nt":
        return None
    import subprocess

    script = (
        "$d=[Environment]::GetFolderPath('Desktop'); $l=Join-Path $d 'NEXUS.lnk';"
        "if(Test-Path -LiteralPath $l){(New-Object -ComObject WScript.Shell).CreateShortcut($l).WorkingDirectory}"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None
    return Path(out) if out else None


def _ancienne_version_notee() -> Path | None:
    """Dossier noté par l'installeur (ancienne-version.txt) avant qu'il ne remplace le raccourci du Bureau."""
    try:
        texte = (INSTALL_DIR / "ancienne-version.txt").read_text(encoding="utf-8-sig").strip()
    except OSError:
        return None
    return Path(texte) if texte else None


def _premier_lancement() -> bool:
    return not (CONFIG_FILE.exists() or (DATA_DIR / "nexus.db").exists() or _LAYOUT_MARKER.exists())


def _importer_version_source() -> list[str]:
    """Version installée, premier lancement : reprend les données de l'ancienne version source.
    Dossier donné par « NEXUS.exe --importer <dossier> », sinon trouvé grâce au raccourci du Bureau."""
    if not FROZEN or INSTALL_DIR.resolve() == USER_ROOT.resolve():  # (portable : ses données sont à côté de l'exe)
        return []
    demande = os.environ.get(IMPORTER_ENV, "").strip()
    if demande:
        source = Path(demande)
        if not est_version_source(source):
            _dire(f"[Données] {source} n'est pas un dossier NEXUS avec des données (app.py, nexus.pyw, config.json ou data/nexus.db)")
            return []
    elif _premier_lancement():
        source = _ancienne_version_notee() or _raccourci_bureau()
        if source is None or not est_version_source(source):
            return []
    else:
        return []
    # (data/ seulement : versions/, sauvegardes-maj/ et maj/ sont des copies du code de la version source)
    return _copier_depuis(source, ("data", "actions"))


def _copier_profils_fournis() -> None:
    """Installe les profils officiels dans le dossier utilisateur (sans écraser les siens)."""
    if not BUNDLED_PROFILES_DIR.is_dir():
        return
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    for folder in sorted(BUNDLED_PROFILES_DIR.iterdir()):
        if folder.is_dir() and not folder.name.startswith(("_", ".")) and not (PROFILES_DIR / folder.name).exists():
            shutil.copytree(folder, PROFILES_DIR / folder.name)


def prepare() -> None:
    """Prépare l'arborescence inscriptible. Idempotent, appelé au démarrage."""
    USER_ROOT.mkdir(parents=True, exist_ok=True)
    # Migration AVANT de créer data/, logs/, actions/… : sinon _copier_dossier verrait une
    # destination déjà présente et ne copierait rien de l'ancienne installation.
    try:
        copied = _migrer_anciennes_donnees() or _importer_version_source()
    except Exception as exc:  # ne jamais empêcher NEXUS de démarrer
        _dire(f"[Données] AVERTISSEMENT : migration de l'ancien dossier impossible ({exc})")
        copied = []
    for folder in (DATA_DIR, LOG_DIR, BACKUP_DIR, MAJ_DIR, SAUVEGARDES_DIR, VERSIONS_DIR, ACTIONS_DIR, PROFILES_DIR):
        folder.mkdir(parents=True, exist_ok=True)
    if copied:
        _dire(f"[Données] Ancienne installation copiée vers {USER_ROOT} : {', '.join(copied)}")
    # Les fichiers d'exemple ne doivent jamais écraser une configuration réelle.
    _copier_fichier(DECK_EXAMPLE, DECK_FILE)
    _copier_fichier(JEUX_EXAMPLE, JEUX_FILE)
    _copier_fichier(ACTIONS_EXAMPLE, ACTIONS_DIR / "exemple.bat")
    _copier_profils_fournis()


# --- Fichier d'exécution (port + jeton local) ------------------------------
def write_runtime(port: int, token: str = "") -> None:
    """Écrit le port et le jeton du serveur en cours (instance unique, ouverture de l'UI)."""
    data = {"port": int(port), "token": token, "pid": os.getpid(), "started": time.time()}
    USER_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = RUNTIME_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RUNTIME_FILE)


def read_runtime() -> dict:
    try:
        data = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def clear_runtime() -> None:
    try:
        RUNTIME_FILE.unlink(missing_ok=True)
    except OSError:
        pass
