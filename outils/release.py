"""Publication d'une version de NEXUS (release GitHub privée du dépôt « origin »).

Usage (depuis le dossier de NEXUS) :
  .venv\\Scripts\\python.exe outils\\release.py correctif|mineur|majeur|X.Y.Z [--sans-publier]
  .venv\\Scripts\\python.exe outils\\release.py --actuelle [--sans-publier]   (publie VERSION tel quel, ex. 1.0.0)
  python outils/release.py --construire-seulement [--depot proprietaire/nom]  (archive + SHA256 dans dist/, CI)

Étapes : arbre Git propre → tests (outils/tests/run_all.py) → valider_profil.py --tous → lint (ruff) → secrets
(gitleaks sur les fichiers ET l'historique, outils/scan_perso.py) → nouvelle VERSION → section datée du CHANGELOG
→ commit + tag vX.Y.Z → archive dist/NEXUS-X.Y.Z.zip (fichiers suivis par Git seulement : ni data/, ni
configuration réelle, ni sessions, journaux, sauvegardes ou références) + .sha256 → vérification de l'archive →
push → gh release create. Rien n'est poussé si une étape échoue.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DIST = BASE / "dist"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
# Jamais dans une archive, même s'ils étaient suivis par erreur
INTERDITS = re.compile(r"(^|/)(data|logs|versions|partage|maj|sauvegardes-maj|sauvegardes|backups|reference|references|"
                       r"\.venv|venv|runtime|runtime\.neuf|runtime\.tmp|dist|__pycache__|LibreHardwareMonitor)(/|$)|(^|/)(config|deck|jeux|fan_names)\.json$|"
                       r"(^|/)\.env|\.(db|sqlite3?|log|bak|pem|key|pfx|p12|lnk)$", re.I)
HORS_ARCHIVE = (".github/",)               # utile au dépôt seulement


class Arret(Exception):
    pass


def _cmd(*args, capture=True, check=True, env=None, timeout=1800) -> str:
    r = subprocess.run(list(args), cwd=BASE, capture_output=capture, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=timeout)
    if check and r.returncode != 0:
        sortie = ((r.stdout or "") + (r.stderr or "")).strip()
        raise Arret(f"échec de « {' '.join(str(a) for a in args[:3])} … » :\n{sortie[-3000:]}")
    return (r.stdout or "").strip()


def outil(nom: str) -> str | None:
    """git / gh / gitleaks : PATH, sinon l'emplacement d'installation de winget."""
    trouve = shutil.which(nom)
    if trouve:
        return trouve
    racine = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for p in racine.glob(f"*/**/{nom}.exe"):
        return str(p)
    for p in (Path(r"C:\Program Files\Git\cmd") / f"{nom}.exe", Path(r"C:\Program Files\GitHub CLI") / f"{nom}.exe"):
        if p.is_file():
            return str(p)
    return None


def etape(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


# --------------------------------------------------------------------------- #
#  Version et CHANGELOG
# --------------------------------------------------------------------------- #
def version_actuelle() -> str:
    return (BASE / "VERSION").read_text(encoding="utf-8").strip()


def prochaine(actuelle: str, quoi: str) -> str:
    if SEMVER.match(quoi):
        if tuple(map(int, quoi.split("."))) <= tuple(map(int, actuelle.split("."))):
            raise Arret(f"{quoi} n'est pas plus récente que {actuelle}")
        return quoi
    ma, mi, co = map(int, SEMVER.match(actuelle).groups())
    return {"majeur": f"{ma + 1}.0.0", "mineur": f"{ma}.{mi + 1}.0", "correctif": f"{ma}.{mi}.{co + 1}"}[quoi]


def section_changelog(texte: str, ver: str) -> str:
    m = re.search(rf"^## \[{re.escape(ver)}\][^\n]*\n(.*?)(?=^## \[|\Z)", texte, re.M | re.S)
    return m.group(1).strip() if m else ""


def entete_version(ver: str, date: str, titre: str = "") -> str:
    """« ## [1.1.0] - 2026-11-16 » ou, avec un titre, « ## [1.1.0] - 2026-11-16 - Philibert arrive ! » (lu par version.py)."""
    return f"## [{ver}] - {date}" + (f" - {titre}" if titre else "")


def verifier_titre(titre: str) -> str:
    titre = " ".join((titre or "").split())
    if len(titre) > 80 or "[" in titre or "]" in titre:
        raise Arret("--titre : une courte phrase sur une ligne (80 caractères au plus, sans crochets)")
    return titre


def titre_release(ver: str, titre: str = "") -> str:
    return f"NEXUS {ver} — {titre}" if titre else f"NEXUS {ver}"


def dater_changelog(ver: str, date: str, titre: str = "") -> None:
    p = BASE / "CHANGELOG.md"
    t = p.read_text(encoding="utf-8")
    m = re.search(r"^## \[Non publié\][^\n]*\n(.*?)(?=^## \[|\Z)", t, re.M | re.S)
    if not m or not re.search(r"^\s*- ", m.group(1), re.M):
        raise Arret("CHANGELOG.md : la section « ## [Non publié] » est vide. Note les changements avant de publier.")
    t = t[:m.start()] + f"## [Non publié]\n\n{entete_version(ver, date, titre)}\n{m.group(1)}" + t[m.end():]
    p.write_text(t, encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
#  Archive
# --------------------------------------------------------------------------- #
def fichiers_suivis(git: str) -> list[str]:
    out = _cmd(git, "-c", "core.quotepath=false", "ls-files", "-z")
    return [f for f in out.split("\0") if f]


def construire_archive(ver: str, depot: str, fichiers: list[str], dest: Path = DIST, source: Path = BASE) -> tuple[Path, Path]:
    dest.mkdir(parents=True, exist_ok=True)
    nom = f"NEXUS-{ver}"
    archive, somme = dest / f"{nom}.zip", dest / f"{nom}.zip.sha256"
    archive.unlink(missing_ok=True)
    pris = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in sorted(fichiers):
            rel = rel.replace("\\", "/")
            if rel.startswith(HORS_ARCHIVE):
                continue
            if INTERDITS.search(rel) and not rel.endswith(".example.json"):
                raise Arret(f"fichier interdit suivi par Git : {rel} (retire-le de Git et ajoute-le à .gitignore)")
            src = source / rel
            if not src.is_file():
                continue
            if rel == "VERSION":
                z.writestr(f"{nom}/VERSION", ver + "\n")
            else:
                z.write(src, f"{nom}/{rel}")
            pris += 1
        if depot:
            z.writestr(f"{nom}/DEPOT", depot + "\n")       # dépôt surveillé proposé à l'installation
    h = hashlib.sha256(archive.read_bytes()).hexdigest()
    somme.write_text(f"{h}  {archive.name}\n", encoding="utf-8", newline="\n")
    print(f"  {archive.name} : {pris} fichiers, {archive.stat().st_size / 1e6:.1f} Mo, SHA256 {h[:16]}…")
    return archive, somme


def nettoyer_dist(ver: str) -> None:
    """Le dossier dist ne garde que l'archive (et son .sha256) de la version qu'on vient de fabriquer : les précédentes
    sont sur GitHub (releases)."""
    for f in DIST.glob("*"):
        if f.is_file() and not f.name.startswith((f"NEXUS-{ver}.", f"notes-{ver}.")):
            f.unlink(missing_ok=True)


def verifier_archive(archive: Path, ver: str) -> None:
    with zipfile.ZipFile(archive) as z:
        noms = z.namelist()
        racine = f"NEXUS-{ver}/"
        if any(not n.startswith(racine) for n in noms):
            raise Arret("archive : tout doit être dans un seul dossier NEXUS-x.y.z/")
        for n in noms:
            rel = n[len(racine):]
            if INTERDITS.search(rel) and not rel.endswith(".example.json"):
                raise Arret(f"archive : fichier interdit {rel}")
        for indispensable in ("VERSION", "app.py", "maj_demarrage.py", "requirements.txt", "lancer.bat", "installer.bat",
                            "nexus.pyw", "superviseur.py", "outils/installer_python.ps1", "outils/python-prive.json"):
            if racine + indispensable not in noms:
                raise Arret(f"archive : {indispensable} manquant")
        if z.read(racine + "VERSION").decode().strip() != ver:
            raise Arret("archive : VERSION ne correspond pas")
    _cmd(sys.executable, str(BASE / "outils" / "scan_perso.py"), str(archive))


# --------------------------------------------------------------------------- #
#  Contrôles
# --------------------------------------------------------------------------- #
def controles(git: str, rapide: bool = False) -> None:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if not rapide:
        etape("Tests")
        print(_cmd(sys.executable, str(BASE / "outils" / "tests" / "run_all.py"), env=env).splitlines()[-1])
    etape("Profils visuels (valider_profil.py --tous)")
    out = _cmd(sys.executable, str(BASE / "valider_profil.py"), "--tous", env=env)
    print(f"  {out.count('PROFIL VALIDE')} profil(s) valide(s)")
    etape("Lint (ruff)")
    try:
        print("  " + _cmd(sys.executable, "-m", "ruff", "check", ".", env=env))
    except Arret as e:
        if "No module named ruff" in str(e):
            raise Arret("ruff n'est pas installé : .venv\\Scripts\\python.exe -m pip install ruff")
        raise
    etape("Secrets et données personnelles")
    gl = outil("gitleaks")
    if not gl:
        raise Arret("gitleaks introuvable (winget install Gitleaks.Gitleaks) : publication refusée sans détection de secrets")
    _cmd(gl, "git", "--no-banner", "--redact", "--exit-code", "1", ".")
    print("  gitleaks (historique) : 0 fuite")
    _cmd(sys.executable, str(BASE / "outils" / "scan_perso.py"), env=env)
    print("  scan_perso (fichiers suivis) : 0 donnée personnelle")


def depot_origin(git: str) -> str:
    url = _cmd(git, "remote", "get-url", "origin", check=False)
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Publier une version de NEXUS")
    ap.add_argument("quoi", nargs="?", help="correctif | mineur | majeur | X.Y.Z")
    ap.add_argument("--actuelle", action="store_true", help="publier la version de VERSION telle quelle")
    ap.add_argument("--sans-publier", action="store_true", help="tout préparer sans pousser ni créer la release")
    ap.add_argument("--construire-seulement", action="store_true", help="seulement l'archive et son SHA256 (CI)")
    ap.add_argument("--depot", default="", help="propriétaire/nom écrit dans l'archive (par défaut : origin)")
    ap.add_argument("--titre", default="", help="titre de la version (ex. « Philibert arrive ! ») : dans l'en-tête du "
                                                "CHANGELOG (« ## [X.Y.Z] - date - titre ») et comme titre de la release GitHub")
    ap.add_argument("--branche", action="store_true",
                    help="publier depuis une branche de release (ex. sans une fonction pas encore prête) : "
                         "seul le tag est poussé, main n'est pas touchée")
    a = ap.parse_args()
    titre = verifier_titre(a.titre)
    git = outil("git")
    if not git:
        raise Arret("git introuvable")
    depot = a.depot or depot_origin(git)

    if a.construire_seulement:
        ver = version_actuelle()
        archive, _ = construire_archive(ver, depot, fichiers_suivis(git))
        verifier_archive(archive, ver)
        return 0

    if not a.actuelle and a.quoi not in ("correctif", "mineur", "majeur") and not (a.quoi and SEMVER.match(a.quoi)):
        ap.error("indique correctif, mineur, majeur, un numéro X.Y.Z ou --actuelle")
    etape("Arbre Git propre")
    if _cmd(git, "status", "--porcelain"):
        raise Arret("des fichiers sont modifiés ou non suivis : commite-les (ou ajoute-les à .gitignore) d'abord")
    branche = _cmd(git, "branch", "--show-current")
    if branche != "main" and not a.branche:
        raise Arret(f"publie depuis la branche main (actuelle : {branche})")
    gh = outil("gh")
    if not a.sans_publier:
        if not gh:
            raise Arret("gh introuvable (winget install GitHub.cli)")
        if not depot:
            raise Arret("aucun dépôt « origin » GitHub")
        _cmd(gh, "auth", "status")

    controles(git)

    actuelle = version_actuelle()
    ver = actuelle if a.actuelle else prochaine(actuelle, a.quoi)
    tag = f"v{ver}"
    if _cmd(git, "tag", "--list", tag):
        raise Arret(f"le tag {tag} existe déjà")
    if not a.actuelle:
        etape(f"Version {actuelle} → {ver}")
        (BASE / "VERSION").write_text(ver + "\n", encoding="utf-8", newline="\n")
        dater_changelog(ver, time.strftime("%Y-%m-%d"), titre)
        _cmd(git, "add", "VERSION", "CHANGELOG.md")
        _cmd(git, "commit", "-m", f"Version {ver}")
    notes = section_changelog((BASE / "CHANGELOG.md").read_text(encoding="utf-8"), ver)
    if not notes:
        raise Arret(f"CHANGELOG.md : aucune section « ## [{ver}] »")
    _cmd(git, "tag", "-a", tag, "-m", f"NEXUS {ver}")
    try:
        etape("Archive de la release")
        archive, somme = construire_archive(ver, depot, fichiers_suivis(git))
        verifier_archive(archive, ver)
        nettoyer_dist(ver)
    except Arret:
        _cmd(git, "tag", "-d", tag, check=False)           # pas de tag local orphelin
        raise
    if a.sans_publier:
        print(f"\nPrêt (non publié) : tag {tag} local, {archive.name} et {somme.name} dans dist\\."
              + (f" Titre : « {titre_release(ver, titre)} »." if titre else ""))
        return 0
    etape("Envoi sur GitHub")
    if not a.branche:
        _cmd(git, "push", "origin", "main")
    _cmd(git, "push", "origin", tag)                       # (avec --branche : seul le tag part, pas la branche)
    notes_f = DIST / f"notes-{ver}.md"
    notes_f.write_text(notes + "\n\nVérifier l'archive : `certutil -hashfile NEXUS-" + ver + ".zip SHA256` doit donner "
                       "le contenu du fichier `.sha256`.\n", encoding="utf-8")
    existe = subprocess.run([gh, "release", "view", tag, "--repo", depot], cwd=BASE, capture_output=True).returncode == 0
    if existe:                                              # créée entre-temps par la CI (release.yml)
        _cmd(gh, "release", "upload", tag, str(archive), str(somme), "--repo", depot, "--clobber")
        if titre:
            _cmd(gh, "release", "edit", tag, "--repo", depot, "--title", titre_release(ver, titre))
    else:
        _cmd(gh, "release", "create", tag, str(archive), str(somme), "--repo", depot, "--title", titre_release(ver, titre),
             "--notes-file", str(notes_f), "--verify-tag")
    print(f"\n✔ Release {tag} publiée : https://github.com/{depot}/releases/tag/{tag}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Arret as e:
        print(f"\n✖ ARRÊT : {e}\nRien n'a été poussé sur GitHub depuis cette étape.", file=sys.stderr)
        sys.exit(1)
