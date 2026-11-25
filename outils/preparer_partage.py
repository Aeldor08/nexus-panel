r"""Prépare une copie de NEXUS propre à partager (dossier + zip), sans aucune donnée personnelle.

Copie uniquement une LISTE AUTORISÉE de fichiers (le code, la page web, les exemples, la doc) :
jamais config.json, deck.json, data\, logs\, versions\, .venv\, LibreHardwareMonitor\, ni tes scripts
personnels du dossier actions\ (seul l'exemple est copié).
Puis vérifie la copie : si un de tes secrets (jeton Discord, mot de passe, ID, nom d'utilisateur Windows,
nom du PC, chemins personnels…) y apparaît quand même, le partage est annulé.

Utilisation : double-clic sur preparer_partage.bat  ->  partage\NEXUS-<version>\ et partage\NEXUS-<version>.zip
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_ROOT = BASE / "partage"

# Liste autorisée (tout le reste est ignoré)
ROOT_FILES = [
    "*.py",
    "*.bat",
    "nexus.spec",
    "installer.iss",
    "requirements.txt",
    "requirements-native.txt",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "VERSION",
    "panel.ico",
    "config.example.json",
    "deck.example.json",
    "jeux.example.json",
    ".gitignore",
    "NE_PAS_PARTAGER.md",
    "THIRD_PARTY.md",
    "ruff.toml",
    "requirements-dev.txt",
]
TREES = ["static", "outils", "profils", "docs"]
EXTRA = ["actions/exemple.bat"]

# Jamais copiés, même s'ils correspondent à la liste autorisée
NEVER_NAMES = {"config.json", "deck.json", ".env", "fan_names.json", "jeux.json", "nexus.db", "rappels.json", "runtime.json"}
# data\ contient tout le personnel : souvenirs (photos), statistiques, journal (nexus.db), agenda, sauvegardes…
NEVER_DIRS = {
    "data",
    "souvenirs",
    "backups",
    "logs",
    "versions",
    ".venv",
    ".venv-build",
    "runtime",
    "runtime.neuf",
    "runtime.tmp",
    "__pycache__",
    "LibreHardwareMonitor",
    "partage",
    ".git",
    "maj",
    "sauvegardes-maj",
    "dist",
}
NEVER_SUFFIXES = {".log", ".lnk", ".tmp", ".pyc", ".zip", ".db", ".db-wal", ".db-shm", ".sqlite"}

TEXT_SUFFIXES = {".py", ".bat", ".md", ".txt", ".json", ".html", ".css", ".js", ".svg", ".webmanifest", ".config", "", ".gitignore"}


def version() -> str:
    try:
        return (BASE / "VERSION").read_text(encoding="utf-8").strip() or "x"
    except OSError:
        return "x"


def allowed(rel: Path) -> bool:
    if rel.name in NEVER_NAMES or rel.suffix.lower() in NEVER_SUFFIXES:
        return False
    return not (set(rel.parts[:-1]) & NEVER_DIRS)


def collect() -> list[Path]:
    files: set[Path] = set()
    for pattern in ROOT_FILES:
        files.update(p for p in BASE.glob(pattern) if p.is_file())
    for tree in TREES:
        files.update(p for p in (BASE / tree).rglob("*") if p.is_file())
    files.update(BASE / e for e in EXTRA if (BASE / e).is_file())
    return sorted(p for p in files if allowed(p.relative_to(BASE)))


def sensitive_values() -> list[tuple[str, str]]:
    """Ce qui ne doit JAMAIS apparaître dans la copie partagée."""
    vals: list[tuple[str, str]] = []

    def add(label: str, v) -> None:
        v = str(v or "").strip()
        if len(v) >= 4:
            vals.append((label, v))

    try:
        cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8-sig"))
        d, k = cfg.get("discord") or {}, cfg.get("deck") or {}
        add("jeton Discord", d.get("token"))
        add("ID Discord", d.get("user_id"))
        add("ID de salon Discord", d.get("alert_channel_id"))
        add("mot de passe du deck", k.get("password"))
        add("empreinte du mot de passe", k.get("password_hash"))
    except (OSError, ValueError):
        pass
    for name in ("USERNAME", "COMPUTERNAME", "USERDOMAIN"):
        add(f"variable Windows {name}", os.environ.get(name))
    add("dossier personnel", os.path.expanduser("~"))
    add("chemin de ton installation", str(BASE))
    for f in ("remote.json", "devices.json"):  # noms d'appareils appairés / du réseau local
        try:
            data = json.loads((BASE / "data" / f).read_text(encoding="utf-8"))
            items = data.get("devices", data) if isinstance(data, dict) else data
            for it in items.values() if isinstance(items, dict) else items or []:
                if isinstance(it, dict):
                    add("nom d'appareil", it.get("name"))
                    add("nom d'appareil", it.get("hostname"))
                    add("adresse MAC", it.get("mac"))
        except (OSError, ValueError, AttributeError):
            pass
    # « Windows » / « Desktop » comme nom de domaine ou de PC seraient trop génériques
    generic = {"windows", "workgroup", "desktop", "user", "admin", "pc"}
    return [(lib, v) for lib, v in vals if v.lower() not in generic]


PATTERNS = [
    ("jeton Discord", re.compile(r"\b[MNO][\w-]{22,27}\.[\w-]{6}\.[\w-]{27,40}\b")),
    ("chemin d'utilisateur Windows", re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}(?!moi\\|Public\\|<)[^\\\s\"']+", re.I)),
    ("ID Discord (nombre de 17 à 20 chiffres)", re.compile(r"(?<![\d.])\d{17,20}(?![\d.])")),
]


def scan(dest: Path, files: list[Path]) -> list[str]:
    problems = []
    secrets_ = sensitive_values()
    for f in files:
        rel = f.relative_to(dest)
        if f.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        low = text.lower()
        for label, v in secrets_:
            if v.lower() in low:
                problems.append(f"{rel} : contient ton {label}")
        for label, rx in PATTERNS:
            m = rx.search(text)
            if m:
                problems.append(f"{rel} : ressemble à un {label} -> {m.group(0)[:12]}…")
    return problems


def main() -> int:
    ver = version()
    dest = OUT_ROOT / f"NEXUS-{ver}"
    zip_path = OUT_ROOT / f"NEXUS-{ver}.zip"
    files = collect()
    if dest.exists():
        shutil.rmtree(dest)
    zip_path.unlink(missing_ok=True)
    copied = []
    for src in files:
        target = dest / src.relative_to(BASE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(target)

    problems = scan(dest, copied)
    if problems:
        print("\n[STOP] Données personnelles trouvées dans la copie : partage annulé.")
        for p in problems:
            print("   - " + p)
        shutil.rmtree(dest, ignore_errors=True)
        return 2

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(dest.rglob("*")):
            z.write(f, Path(dest.name) / f.relative_to(dest))
    size = zip_path.stat().st_size / 1024
    # copies de partage des versions précédentes : retirées (seule la dernière sert à partager)
    for ancien in OUT_ROOT.glob("NEXUS-*"):
        if ancien.name in (dest.name, zip_path.name):
            continue
        if ancien.is_dir():
            shutil.rmtree(ancien, ignore_errors=True)
        else:
            ancien.unlink(missing_ok=True)
    print(f"\n[OK] {len(copied)} fichiers copiés, aucune donnée personnelle détectée.")
    print(f"     Dossier : {dest}")
    print(f"     Zip     : {zip_path}  ({size:.0f} Ko)")
    print("     Envoie le zip : ton amie le dézippe puis lance installer.bat (voir README).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
