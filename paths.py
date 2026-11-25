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


def _dire(message: str) -> None:
    """Écrit sur la console si elle existe (pythonw peut avoir stdout/stderr à None)."""
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


def _migrer_anciennes_donnees() -> list[str]:
    """Copie les anciennes données posées à côté de l'exe vers USER_ROOT (jamais d'écrasement)."""
    if not FROZEN or LEGACY_DIR.resolve() == USER_ROOT.resolve() or _LAYOUT_MARKER.exists():
        return []
    copied: list[str] = []
    for name in ("config.json", "deck.json", "jeux.json", "fan_names.json", ".env"):
        if _copier_fichier(LEGACY_DIR / name, USER_ROOT / name):
            copied.append(name)
    for name in ("data", "logs", "actions", "versions", "sauvegardes-maj", "maj"):
        if _copier_dossier(LEGACY_DIR / name, USER_ROOT / name):
            copied.append(name + "/")
    # Profils : on copie aussi les profils officiels de l'ancien dossier (l'utilisateur a pu
    # les modifier). Les profils officiels manquants seront ajoutés ensuite par
    # _copier_profils_fournis(), sans écraser ceux qui viennent d'être copiés.
    old_profiles = LEGACY_DIR / "profils"
    if old_profiles.is_dir():
        for folder in old_profiles.iterdir():
            if not folder.is_dir() or folder.name.startswith(("_", ".")):
                continue
            if _copier_dossier(folder, PROFILES_DIR / folder.name):
                copied.append(f"profils/{folder.name}/")
    if copied:
        _LAYOUT_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _LAYOUT_MARKER.write_text(
            "Migration depuis " + str(LEGACY_DIR) + " le " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n",
            encoding="utf-8")
    return copied


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
        copied = _migrer_anciennes_donnees()
    except Exception as exc:                       # ne jamais empêcher NEXUS de démarrer
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
