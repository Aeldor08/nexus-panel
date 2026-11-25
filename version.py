"""Versions du panel : numéro (fichier VERSION), notes (CHANGELOG.md) et sauvegarde
automatique du code de chaque version dans versions/panel-vX.Y.Z.zip."""

from __future__ import annotations

import re
import time
import zipfile
from pathlib import Path

import paths

BASE = paths.APP_DIR
VERSIONS_DIR = paths.VERSIONS_DIR
# Ce qui fait partie du « code » du panel (les données dans data/ ne sont jamais incluses)
# (config.json et deck.json, personnels, ne sont jamais inclus : seuls les modèles *.example.json le sont)
CODE_GLOBS = [
    "*.py",
    "*.bat",
    "*.spec",
    "*.iss",
    "*.md",
    "*.txt",
    "*.ico",
    "*.example.json",
    ".gitignore",
    "VERSION",
    "LICENSE",
    "static/**/*",
    "outils/*",
    "profils/**/*",
    "docs/**/*",
    "actions/*.bat",
    "actions/*.cmd",
    "actions/*.ps1",
    "actions/*.py",
]
EXCLUDE_PARTS = {
    ".venv",
    ".venv-build",
    "runtime",
    "runtime.neuf",
    "runtime.tmp",
    "data",
    "versions",
    "__pycache__",
    "LibreHardwareMonitor",
    "partage",
    "maj",
    "sauvegardes-maj",
    "dist",
}


def current() -> str:
    try:
        return (BASE / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def changelog() -> list[dict]:
    try:
        text = (BASE / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return []
    entries = []
    # Format « Keep a Changelog » : ## [1.2.0] - 2026-11-10 (titre facultatif : - Titre), rubriques ### Ajouté…
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        m = re.match(r"\[(.+?)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?(?:\s*-\s*(.+))?", head.strip())
        if not m or not re.match(r"^\d+\.\d+\.\d+", m.group(1)):  # [Non publié] / [Unreleased] : ignoré
            continue
        items: list[str] = []
        rubrique = ""
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("### "):
                rubrique = s[4:].strip()
            elif s.startswith("- "):
                items.append((f"{rubrique} : " if rubrique else "") + s[2:].strip())
            elif s and items and line[:1] in (" ", "\t"):  # ligne de suite (indentée) du point précédent
                items[-1] += " " + s
        entries.append({"version": m.group(1), "date": m.group(2) or "", "title": (m.group(3) or "").strip(), "items": items})
    return entries


def date_version(v: str | None = None) -> str:
    """Date (AAAA-MM-JJ) de la version installée d'après CHANGELOG.md ('' si inconnue)."""
    v = v or current()
    return next((e["date"] for e in changelog() if e["version"] == v), "")


def code_files() -> list[Path]:
    files = set()
    for pattern in CODE_GLOBS:
        for p in BASE.glob(pattern):
            rel = p.relative_to(BASE)
            if p.is_file() and not (set(rel.parts) & EXCLUDE_PARTS) and p.suffix != ".lnk":
                files.add(p)
    return sorted(files)


def snapshot(force: bool = False) -> Path | None:
    """Archive le code de la version actuelle (une seule fois par version).

    En version installée, le code vit dans le dossier de ressources en lecture seule : les
    snapshots de code n'ont plus de sens (la mise à jour passera par l'installeur signé).
    """
    if paths.FROZEN:
        return None
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = VERSIONS_DIR / f"panel-v{current()}.zip"
    if target.exists() and not force:
        return None
    tmp = target.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in code_files():
            z.write(f, f.relative_to(BASE).as_posix())
    tmp.replace(target)
    return target


VERSIONS_A_GARDER = 8  # sauvegardes de code gardées dans versions\ (les plus récentes)


def nettoyer(garder: int = VERSIONS_A_GARDER) -> list[str]:
    """Supprime les sauvegardes de code les plus anciennes (au-delà de « garder ») ; renvoie les noms retirés.
    Les copies « avant-restauration » sont gardées par 3 au plus. Ne touche à rien d'autre."""
    retires = []
    for motif, n in (("panel-v*.zip", garder), ("avant-restauration-*.zip", 3)):
        fichiers = sorted(VERSIONS_DIR.glob(motif), key=lambda f: f.stat().st_mtime, reverse=True)
        actuelle = VERSIONS_DIR / f"panel-v{current()}.zip"
        for f in fichiers[max(1, n) :]:
            if f == actuelle:
                continue
            try:
                f.unlink()
                retires.append(f.name)
            except OSError:
                pass
    return retires


def snapshots() -> list[dict]:
    out = []
    for z in VERSIONS_DIR.glob("*.zip"):
        m = re.match(r"panel-v(.+)\.zip$", z.name)
        st = z.stat()
        out.append({"file": z.name, "version": m.group(1) if m else None, "size": st.st_size, "time": st.st_mtime})
    out.sort(key=lambda s: s["time"], reverse=True)
    return out


def backup_current() -> Path:
    """Sauvegarde de sécurité du code actuel avant une restauration."""
    if paths.FROZEN:
        raise OSError("les sauvegardes de code ne sont pas disponibles dans la version installée")
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = VERSIONS_DIR / f"avant-restauration-v{current()}-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for f in code_files():
            z.write(f, f.relative_to(BASE).as_posix())
    return target


def restore(archive: Path) -> int:
    """Remet en place le code contenu dans l'archive. Ne touche jamais à data/, .venv/, etc."""
    if paths.FROZEN:
        raise OSError("la restauration de code n'est pas disponible dans la version installée")
    count = 0
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if member.is_dir():
                continue
            dest = (BASE / member.filename).resolve()
            rel = dest.relative_to(BASE) if dest.is_relative_to(BASE) else None
            if rel is None or set(rel.parts) & EXCLUDE_PARTS:  # chemin hors du dossier : ignoré
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(member))
            count += 1
    return count


def _cli() -> None:
    """Assistant de restauration (lancé par restaurer_version.bat)."""
    snaps = snapshots()
    print(f"\n  Version installée : v{current()}\n")
    if not snaps:
        print("  Aucune sauvegarde dans le dossier versions\\.")
        return
    for i, s in enumerate(snaps, 1):
        when = time.strftime("%d/%m/%Y %H:%M", time.localtime(s["time"]))
        print(f"  {i:2}. {s['file']:<48} {when}")
    choice = input("\n  Numéro de la version à restaurer (Entrée = annuler) : ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(snaps):
        print("  Annulé, rien n'a été modifié.")
        return
    archive = VERSIONS_DIR / snaps[int(choice) - 1]["file"]
    if input(f"  Restaurer {archive.name} ? Tes données (agenda, notes...) sont conservées. (o/N) : ").strip().lower() not in ("o", "oui", "y"):
        print("  Annulé, rien n'a été modifié.")
        return
    backup = backup_current()
    print(f"  Sauvegarde de sécurité de la version actuelle : versions\\{backup.name}")
    n = restore(archive)
    print(f"  ✔ {n} fichiers restaurés. Version maintenant installée : v{current()}")
    print("  Relance NEXUS (raccourci sur le bureau) pour l'utiliser.")


if __name__ == "__main__":
    _cli()


def info() -> dict:
    return {"version": current(), "date": date_version(), "changelog": changelog(), "snapshots": snapshots(), "checked": time.time()}
