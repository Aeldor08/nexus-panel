"""Construit NEXUS.exe et, en option, l'installeur Inno Setup et l'archive portable.

Prérequis (dans le venv de build) :
    python -m pip install -r requirements-native.txt
    Inno Setup 6 installé pour --installer

Exemples :
    .venv\\Scripts\\python.exe outils\\build_native.py
    .venv\\Scripts\\python.exe outils\\build_native.py --installer
    .venv\\Scripts\\python.exe outils\\build_native.py --portable
    .venv\\Scripts\\python.exe outils\\build_native.py --installer --portable
    .venv\\Scripts\\python.exe outils\\build_native.py --installer --no-smoke

Le résultat est dans dist\\NEXUS\\ (exe onedir), dist\\NEXUS-x.y.z-Setup.exe
et dist\\NEXUS-Portable-x.y.z.zip, avec les fichiers .sha256 et SHA256SUMS.txt.
La signature Authenticode est faite par outils\\sign_native.ps1 ou par le build
avec --thumbprint / --pfx (signtool requis). L'exe est signé AVANT la fabrication
de l'installeur et de l'archive portable.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DIST = BASE / "dist"


class BuildError(Exception):
    pass


# --------------------------------------------------------------------------- #
#  LibreHardwareMonitor (MPL-2.0) : livré avec l'installeur (option cochée) et le portable
# --------------------------------------------------------------------------- #
LHM_VERSION = "0.9.6"
LHM_URL = f"https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v{LHM_VERSION}/LibreHardwareMonitor.zip"
# Empreinte publiée par GitHub pour cette version (édition .NET Framework 4.7.2, incluse dans Windows 10/11)
LHM_SHA256 = "086d9f1b5a99e643edc2cfaaac16051685b551e4c5ac0b32a57c58c0e529c001"
LHM_LICENCE_URL = f"https://raw.githubusercontent.com/LibreHardwareMonitor/LibreHardwareMonitor/v{LHM_VERSION}/LICENSE"
LHM_CACHE = BASE / "build" / "tiers"


def preparer_lhm() -> Path:
    """Télécharge (une fois, en cache dans build/tiers/) et vérifie LibreHardwareMonitor ; renvoie son dossier
    prêt à livrer : programme + configuration de NEXUS (serveur web 8085, démarrage réduit) + licence."""
    import urllib.request

    dossier = LHM_CACHE / f"LibreHardwareMonitor-{LHM_VERSION}"
    if (dossier / "LibreHardwareMonitor.exe").is_file():
        return dossier
    LHM_CACHE.mkdir(parents=True, exist_ok=True)
    archive = LHM_CACHE / f"LibreHardwareMonitor-{LHM_VERSION}.zip"
    if not archive.is_file() or sha256(archive) != LHM_SHA256:
        print(f"  téléchargement de LibreHardwareMonitor {LHM_VERSION}")
        tmp = archive.with_suffix(".part")
        with urllib.request.urlopen(LHM_URL, timeout=120) as rep, open(tmp, "wb") as f:
            shutil.copyfileobj(rep, f)
        tmp.replace(archive)
    if sha256(archive) != LHM_SHA256:
        archive.unlink(missing_ok=True)
        raise BuildError("LibreHardwareMonitor : empreinte SHA256 différente de celle attendue (téléchargement refusé)")
    tmp_dir = dossier.with_name(dossier.name + ".tmp")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            nom = Path(info.filename)
            if nom.is_absolute() or ".." in nom.parts:
                raise BuildError(f"LibreHardwareMonitor : chemin interdit dans l'archive ({info.filename})")
        z.extractall(tmp_dir)
    # Archive avec ou sans dossier racine
    racine = tmp_dir if (tmp_dir / "LibreHardwareMonitor.exe").is_file() else next(tmp_dir.rglob("LibreHardwareMonitor.exe")).parent
    shutil.copyfile(BASE / "outils" / "LibreHardwareMonitor.config", racine / "LibreHardwareMonitor.config")
    try:
        with urllib.request.urlopen(LHM_LICENCE_URL, timeout=30) as rep:
            licence = rep.read().decode("utf-8", errors="replace")
    except OSError:
        licence = "Mozilla Public License 2.0 : https://mozilla.org/MPL/2.0/\n"
    (racine / "LICENCE-LibreHardwareMonitor.txt").write_text(
        f"LibreHardwareMonitor {LHM_VERSION}, livré avec NEXUS sans modification.\n"
        f"Code source : https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/tree/v{LHM_VERSION}\n\n" + licence,
        encoding="utf-8",
    )
    if racine == tmp_dir:
        tmp_dir.replace(dossier)
    else:
        shutil.move(str(racine), str(dossier))
        shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"  LibreHardwareMonitor {LHM_VERSION} prêt : {dossier}")
    return dossier


def run(cmd: list[str], timeout: int | None = None) -> None:
    print("  >", " ".join(str(c) for c in cmd))
    try:
        subprocess.run(cmd, cwd=BASE, timeout=timeout, check=True)
    except subprocess.CalledProcessError as exc:
        raise BuildError(f"commande en échec (code {exc.returncode}) : {' '.join(map(str, cmd))}") from exc


def version() -> str:
    return (BASE / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"


def find_iscc() -> str | None:
    found = shutil.which("iscc") or shutil.which("ISCC")
    if found:
        return found
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    return str(next((p for p in candidates if p.is_file()), "")) or None


def find_signtool() -> str | None:
    found = shutil.which("signtool") or shutil.which("signtool.exe")
    if found:
        return found
    roots = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10" / "bin",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Windows Kits" / "10" / "bin",
    ]
    for root in roots:
        if root.is_dir():
            hits = sorted(root.glob("**/x64/signtool.exe"), reverse=True)
            if hits:
                return str(hits[0])
    return None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sign(path: Path, args: argparse.Namespace, signtool: str) -> None:
    cmd = [signtool, "sign", "/fd", "SHA256", "/tr", "http://timestamp.digicert.com", "/td", "SHA256"]
    if args.thumbprint:
        cmd += ["/sha1", args.thumbprint]
    elif args.pfx:
        cmd += ["/f", args.pfx]
        if args.pfx_password:
            cmd += ["/p", args.pfx_password]
    else:
        return
    run(cmd + [str(path)])


def write_hashes(files: list[Path]) -> None:
    """Écrit NEXUS-....sha256 (format « hash  nom ») et SHA256SUMS.txt pour les releases."""
    lignes = []
    for path in files:
        empreinte = sha256(path)
        fichier = Path(str(path) + ".sha256")
        fichier.write_text(f"{empreinte}  {path.name}\n", encoding="utf-8")
        lignes.append(f"{empreinte}  {path.name}")
        print(f"  {fichier.name} : {empreinte}")
    if lignes:
        (DIST / "SHA256SUMS.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")


def write_portable(ver: str, lhm: Path | None = None) -> Path:
    """Archive ZIP portable : exe + _internal + drapeau + lanceur + notice (+ LibreHardwareMonitor)."""
    source = DIST / "NEXUS"
    if not (source / "NEXUS.exe").is_file():
        raise BuildError(f"exe introuvable pour l'archive portable : {source / 'NEXUS.exe'}")
    cible = DIST / f"NEXUS-Portable-{ver}.zip"
    racine = f"NEXUS-Portable-{ver}"
    flag = "NEXUS portable\nLes données (config.json, data, logs, profils, actions) restent dans ce dossier.\n"
    lanceur = '@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\nstart "" "NEXUS.exe" --portable\r\n'
    notice = f"""NEXUS {ver} — version portable
================================

1. Décompresse ce dossier où tu veux (clé USB, dossier personnel…), sur un support inscriptible.
2. Lance « Lancer NEXUS.bat » (ou NEXUS.exe : le fichier portable.flag est détecté automatiquement).
3. Au premier lancement, la fenêtre de configuration demande le mot de passe du deck.
4. Tes données restent dans ce dossier : config.json, data\\, logs\\, profils\\, actions\\.
   Aucune installation, aucun raccourci et aucune entrée de démarrage automatique ne sont créés (sauf si tu
   coches ⚙ Réglages → Démarrage de Windows).

Mise à jour automatique (depuis la version 1.9.0) :
- quand une nouvelle version existe, NEXUS propose de l'installer (pastille de version) ; il télécharge la
  nouvelle archive portable, la vérifie (SHA256), sauvegarde NEXUS.exe et _internal\\ dans maj\\rollback\\,
  remplace seulement ces fichiers du programme et se relance ; tes données ne sont jamais touchées ;
- il faut que ce dossier soit modifiable (pas une clé verrouillée ni C:\\Program Files).

Mise à jour manuelle (dossier en lecture seule, ou portable antérieur à 1.9.0) :
- ferme NEXUS ;
- décompresse la nouvelle version dans un autre dossier, puis recopie NEXUS.exe et _internal\\
  par-dessus l'ancienne, sans supprimer config.json, data\\, logs\\, profils\\ ni actions\\ ;
- ou copie ces dossiers de données dans le nouveau dossier avant de lancer.

À savoir :
- Microsoft Edge WebView2 est nécessaire (présent sur Windows 11 et la plupart des Windows 10).
- NEXUS n'est pas signé pour l'instant : Windows SmartScreen peut afficher un avertissement.
- Pour supprimer NEXUS, ferme-le et supprime simplement ce dossier.
"""
    exclus = {"NEXUS.exe.sha256", "SHA256SUMS.txt"}
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for fichier in sorted(source.rglob("*")):
            if not fichier.is_file():
                continue
            rel = fichier.relative_to(source)
            if fichier.name in exclus or rel.parts[0].lower().startswith("unins"):
                continue
            z.write(fichier, f"{racine}/{rel.as_posix()}")
        if lhm is not None:
            for fichier in sorted(lhm.rglob("*")):
                if fichier.is_file():
                    z.write(fichier, f"{racine}/LibreHardwareMonitor/{fichier.relative_to(lhm).as_posix()}")
        z.writestr(f"{racine}/portable.flag", flag)
        z.writestr(f"{racine}/Lancer NEXUS.bat", lanceur)
        z.writestr(f"{racine}/LISEZMOI.txt", notice)
    return cible


def depot_origin() -> str:
    """propriétaire/nom du remote origin GitHub, ou chaîne vide."""
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=BASE, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""
    m = re.search(r"github\.com[:/]([A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$", url)
    return m.group(1) if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Construire NEXUS.exe et l'installeur")
    ap.add_argument("--skip-tests", action="store_true", help="ne pas lancer outils/tests/run_all.py")
    ap.add_argument("--installer", action="store_true", help="construire aussi l'installeur Inno Setup")
    ap.add_argument("--portable", action="store_true", help="construire aussi l'archive portable ZIP")
    ap.add_argument("--no-smoke", action="store_true", help="ne pas tester le démarrage de l'exe")
    ap.add_argument("--thumbprint", default="", help="empreinte du certificat Authenticode (signtool /sha1)")
    ap.add_argument("--pfx", default="", help="fichier .pfx pour signer")
    ap.add_argument("--pfx-password", default="", help="mot de passe du .pfx")
    ap.add_argument("--hashes-only", action="store_true", help="réécrire seulement les fichiers .sha256")
    ap.add_argument("--depot", default="", help="dépôt GitHub surveillé pour les mises à jour (propriétaire/nom) ; par défaut : le remote origin")
    ap.add_argument("--sans-lhm", action="store_true", help="ne pas livrer LibreHardwareMonitor (installeur et portable)")
    args = ap.parse_args()

    ver = version()
    exe = DIST / "NEXUS" / "NEXUS.exe"
    installer = DIST / f"NEXUS-{ver}-Setup.exe"
    portable = DIST / f"NEXUS-Portable-{ver}.zip"
    if args.hashes_only:
        fichiers = [p for p in (exe, installer, portable) if p.is_file()]
        if not fichiers:
            raise BuildError("aucun exe, installeur ou archive portable à hacher (construis-les d'abord)")
        write_hashes(fichiers)
        return 0

    print(f"NEXUS {ver} — construction native")
    print(f"Python : {sys.executable}")
    signing = bool(args.thumbprint or args.pfx)
    signtool = find_signtool() if signing else None
    if signing and not signtool:
        raise BuildError("signtool introuvable : installe le Windows SDK ou signe avec outils/sign_native.ps1")

    lhm = None
    if (args.installer or args.portable) and not args.sans_lhm:
        print("\nLibreHardwareMonitor (températures) pour l'installeur et le portable")
        lhm = preparer_lhm()

    if not args.skip_tests:
        print("\n[1/6] Tests")
        run([sys.executable, str(BASE / "outils" / "tests" / "run_all.py")])

    print("\n[2/6] PyInstaller")
    depot = args.depot.strip() or depot_origin()
    depot_file = BASE / "DEPOT"
    depot_temp = bool(depot) and not depot_file.exists()
    if depot_temp:
        # Embarqué dans l'exe : l'installation sait quel dépôt surveiller pour ses mises à jour
        depot_file.write_text(depot + "\n", encoding="utf-8")
    print(f"  dépôt des mises à jour : {depot or '(aucun : mises à jour à configurer à la main)'}")
    try:
        run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(BASE / "nexus.spec")])
    finally:
        if depot_temp:
            depot_file.unlink(missing_ok=True)
    if not exe.is_file():
        raise BuildError(f"exe introuvable après PyInstaller : {exe}")
    print(f"  {exe} ({exe.stat().st_size / 2**20:.1f} Mo)")

    if not args.no_smoke:
        print("\n[3/6] Test de démarrage de l'exe")
        data = Path(tempfile.mkdtemp(prefix="nexus-build-smoke-"))
        try:
            run([str(exe), "--smoke-test", "--no-tray", "--data-dir", str(data)], timeout=180)
        finally:
            shutil.rmtree(data, ignore_errors=True)

    if signing:
        print("\nSignature Authenticode de l'exe (avant l'installeur et l'archive portable)")
        sign(exe, args, signtool)

    if args.installer:
        print("\n[4/6] Installeur Inno Setup")
        iscc = find_iscc()
        if not iscc:
            raise BuildError("Inno Setup 6 introuvable (ISCC.exe). Installe-le depuis jrsoftware.org, ou construis seulement l'exe sans --installer.")
        cmd = [iscc, f"/DMyVersion={ver}"]
        if lhm is not None:
            cmd.append(f"/DLhmDir={lhm}")
        run([*cmd, str(BASE / "installer.iss")])
        if not installer.is_file():
            raise BuildError(f"installeur introuvable après Inno Setup : {installer}")
        print(f"  {installer} ({installer.stat().st_size / 2**20:.1f} Mo)")
        if signing:
            print("\nSignature Authenticode de l'installeur")
            sign(installer, args, signtool)
    else:
        print("\n[4/6] Installeur ignoré (ajoute --installer)")

    portable_zip = None
    if args.portable:
        print("\n[5/6] Archive portable")
        portable_zip = write_portable(ver, lhm)
        print(f"  {portable_zip} ({portable_zip.stat().st_size / 2**20:.1f} Mo)")
    else:
        print("\n[5/6] Archive portable ignorée (ajoute --portable)")

    print("\n[6/6] Empreintes SHA256")
    fichiers = [p for p in (exe, installer if args.installer else None, portable_zip) if p and p.is_file()]
    write_hashes(fichiers)

    print("\nTerminé :")
    print(f"  exe       : {exe}")
    print(f"  SHA256    : {sha256(exe)}")
    if args.installer:
        print(f"  installeur: {installer}")
        print(f"  SHA256    : {sha256(installer)}")
    if portable_zip:
        print(f"  portable  : {portable_zip}")
        print(f"  SHA256    : {sha256(portable_zip)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"\nÉCHEC : {exc}", file=sys.stderr)
        raise SystemExit(1)
