"""Recherche de données personnelles ou secrètes dans les fichiers SUIVIS par Git (ou une archive de release).
Complète gitleaks (jetons connus) avec ce qui est propre à NEXUS : chemins du PC, nom d'utilisateur Windows,
IDs Discord, adresses IP / MAC du réseau local, jetons Discord, empreintes de mot de passe, e-mails.
Usage : python outils/scan_perso.py [dossier ou archive .zip]   (code de sortie 1 si quelque chose est trouvé)"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
USER = os.environ.get("USERNAME", "") or os.environ.get("USER", "")
PATTERNS = [
    ("jeton Discord", re.compile(r"[MNO][A-Za-z\d_-]{23,25}\.[A-Za-z\d_-]{6}\.[A-Za-z\d_-]{27,38}")),
    ("empreinte de mot de passe", re.compile(r"pbkdf2_sha256\$\d+\$[0-9a-f]{16,}\$[0-9a-f]{32,}")),
    ("ID Discord (17-20 chiffres)", re.compile(r"(?<![\d.])\d{17,20}(?![\d.])")),
    ("adresse IP du réseau local", re.compile(r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
    ("adresse MAC", re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")),
    ("adresse e-mail", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]{2,}")),
    ("chemin d'un profil Windows", re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+(?!Public|Default|NOM|<)[^\\/\s\"']+", re.I)),
    ("jeton GitHub", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}")),
    ("clé privée", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
PATTERNS.append(("chemin de ce dossier sur le PC", re.compile(r"[\\/]+".join(re.escape(p) for p in re.split(r"[\\/]+", str(BASE))), re.I)))
if len(USER) >= 3:
    PATTERNS.append(("nom d'utilisateur Windows", re.compile(re.escape(USER), re.I)))
# Faux positifs connus (exemples fictifs, domaines publics, IDs d'apps du Store, versions)
ALLOW = [
    re.compile(p)
    for p in (
        r"noreply@anthropic\.com",
        r"@users\.noreply\.github\.com",
        r"example\.(com|org)",
        r"exemple\.(com|fr)",
        r"git@github\.com",
        r"192\.168\.1\.(?:1|10|42|50|100|254)\b",
        r"10\.0\.0\.\d+",
        r"COLLE_ICI",
        r"TON_ID",
        r"00:11:22:33:44:55",
        r"AA:BB:CC:DD:EE:FF",
        r"(?i)ff[:-]ff[:-]ff[:-]ff[:-]ff[:-]ff",  # diffusion réseau (code)
        r"\+@app\.",  # lignes ajoutées d'un patch de code (@app.post)
    )
]
BINARY = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".ico",
    ".woff2",
    ".woff",
    ".ttf",
    ".zip",
    ".gif",
    ".exe",
    ".dll",
    ".db",
    ".mp3",
    ".ogg",
    ".oga",
    ".opus",
    ".wav",
    ".flac",
    ".m4a",
    ".webm",
}  # sons : des octets peuvent ressembler à une adresse


def tracked_files() -> list[tuple[str, bytes]]:
    out = (
        subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=BASE, capture_output=True, check=True)
        .stdout.decode("utf-8")
        .split("\0")
    )
    return [(f, (BASE / f).read_bytes()) for f in out if f and (BASE / f).is_file()]


def archive_files(path: Path) -> list[tuple[str, bytes]]:
    with zipfile.ZipFile(path) as z:
        return [(i.filename, z.read(i)) for i in z.infolist() if not i.is_dir()]


def folder_files(path: Path) -> list[tuple[str, bytes]]:
    return [(str(p.relative_to(path)), p.read_bytes()) for p in path.rglob("*") if p.is_file()]


def scan(files: list[tuple[str, bytes]]) -> list[str]:
    found = []
    for name, data in files:
        if Path(name).suffix.lower() in BINARY:
            continue
        text = data.decode("utf-8", errors="replace")
        for label, rx in PATTERNS:
            for m in rx.finditer(text):
                s = m.group(0)
                ctx = text[max(0, m.start() - 40) : m.end() + 40]
                if any(a.search(s) or a.search(ctx) for a in ALLOW) or (label == "adresse e-mail" and Path(name).name.startswith("OFL")):
                    continue
                line = text.count("\n", 0, m.start()) + 1
                found.append(f"{name}:{line}: {label} : {s[:6]}… (masqué)")
    return found


def main() -> int:
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    files = archive_files(arg) if arg and arg.suffix == ".zip" else folder_files(arg) if arg else tracked_files()
    found = scan(files)
    for f in found:
        print(f)
    print(f"{len(files)} fichier(s) examiné(s) : {len(found)} élément(s) à vérifier")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
