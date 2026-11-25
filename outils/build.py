"""Construit NEXUS d'une seule commande, dans dist/ :

    python outils/build.py            (ou double-clic sur Creer-NEXUS-Portable.bat)

Étapes : environnement de build (.venv-build, dépendances installées seulement si elles changent) → nettoyage →
lint (ruff check + ruff format --check) → tests → audit (pip-audit des dépendances, gitleaks si présent) →
NEXUS.exe (PyInstaller, mode dossier) → test de démarrage → installeur NEXUS-X.Y.Z-Setup.exe (Inno Setup 6) →
NEXUS-Portable-X.Y.Z.zip → fichiers .sha256 et SHA256SUMS.txt. LibreHardwareMonitor est téléchargé une fois
(version et empreinte fixées dans build_native.py) et livré avec l'installeur (option cochée) et le portable.

Options : --sans-tests, --sans-audit, --sans-installeur, --sans-portable, --sans-lhm,
          --thumbprint / --pfx / --pfx-password (signature Authenticode, désactivée par défaut : voir README).
Code de sortie 0 = tout est construit et vérifié.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
VENV = BASE / ".venv-build"
PY = VENV / "Scripts" / "python.exe"
DIST = BASE / "dist"
REQUIREMENTS = ("requirements.txt", "requirements-native.txt", "requirements-dev.txt")


class Arret(Exception):
    pass


def etape(titre: str) -> None:
    print(f"\n=== {titre}", flush=True)


def lancer(cmd: list[str], **kw) -> None:
    print("  >", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, cwd=BASE, **kw)
    if r.returncode != 0:
        raise Arret(f"échec (code {r.returncode}) : {' '.join(str(c) for c in cmd)}")


def environnement() -> None:
    """.venv-build : Python 3.11/3.12 du système, dépendances réinstallées seulement si un requirements change."""
    if not PY.is_file():
        base = shutil.which("py")
        cmd = [base, "-3.12"] if base else [sys.executable]
        lancer([*cmd, "-m", "venv", str(VENV)])
    empreinte = hashlib.sha256(b"".join((BASE / f).read_bytes() for f in REQUIREMENTS)).hexdigest()
    marque = VENV / ".requirements.sha256"
    if marque.is_file() and marque.read_text(encoding="utf-8").strip() == empreinte:
        print("  dépendances à jour")
        return
    lancer([str(PY), "-m", "pip", "install", "--disable-pip-version-check", "-q", "--upgrade", "pip"])
    fichiers = [x for f in REQUIREMENTS for x in ("-r", f)]
    lancer([str(PY), "-m", "pip", "install", "--disable-pip-version-check", "-q", *fichiers])
    marque.write_text(empreinte, encoding="utf-8")


def nettoyer() -> None:
    """dist/ et le dossier de travail de PyInstaller (build/nexus) ; le cache build/tiers/ est gardé."""
    for d in (DIST, BASE / "build" / "nexus"):
        if d.exists():
            shutil.rmtree(d)
            print(f"  supprimé : {d.relative_to(BASE)}")


def gitleaks() -> str | None:
    trouve = shutil.which("gitleaks")
    if trouve:
        return trouve
    racine = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    return next((str(p) for p in racine.glob("Gitleaks.Gitleaks*/gitleaks.exe")), None)


def main() -> int:
    ap = argparse.ArgumentParser(description="Construire NEXUS (exe, installeur, portable) dans dist/")
    for nom, aide in (
        ("--sans-tests", "ne pas lancer les tests"),
        ("--sans-audit", "ne pas lancer pip-audit ni gitleaks"),
        ("--sans-installeur", "ne pas construire l'installeur (Inno Setup 6 non requis)"),
        ("--sans-portable", "ne pas construire le ZIP portable"),
        ("--sans-lhm", "ne pas livrer LibreHardwareMonitor"),
    ):
        ap.add_argument(nom, action="store_true", help=aide)
    ap.add_argument("--depot", default="", help="dépôt GitHub surveillé pour les mises à jour (par défaut : origin)")
    ap.add_argument("--thumbprint", default="", help="signature Authenticode : empreinte du certificat (magasin Windows)")
    ap.add_argument("--pfx", default="", help="signature Authenticode : fichier .pfx")
    ap.add_argument("--pfx-password", default="", help="mot de passe du .pfx (préférer la variable NEXUS_PFX_PASSWORD)")
    a = ap.parse_args()
    t0 = time.time()

    etape("Environnement de build (.venv-build)")
    environnement()
    etape("Nettoyage")
    nettoyer()
    etape("Lint")
    lancer([str(PY), "-m", "ruff", "check", "."])
    lancer([str(PY), "-m", "ruff", "format", "--check", "."])
    if not a.sans_tests:
        etape("Tests")
        lancer([str(PY), str(BASE / "outils" / "tests" / "run_all.py")])
    if not a.sans_audit:
        etape("Audit des dépendances (pip-audit)")
        lancer([str(PY), "-m", "pip_audit", "-r", "requirements.txt", "-r", "requirements-native.txt", "--progress-spinner", "off"])
        g = gitleaks()
        if g:
            etape("Détection de secrets (gitleaks, historique Git)")
            lancer([g, "git", "--no-banner", "--redact", "--exit-code", "1", "."])
        else:
            print("  gitleaks introuvable (winget install Gitleaks.Gitleaks) : étape sautée")
    etape("Exécutable, installeur, portable")
    cmd = [str(PY), str(BASE / "outils" / "build_native.py"), "--skip-tests"]
    cmd += [] if a.sans_installeur else ["--installer"]
    cmd += [] if a.sans_portable else ["--portable"]
    cmd += ["--sans-lhm"] if a.sans_lhm else []
    cmd += ["--depot", a.depot] if a.depot else []
    cmd += ["--thumbprint", a.thumbprint] if a.thumbprint else []
    pfx_mdp = a.pfx_password or os.environ.get("NEXUS_PFX_PASSWORD", "")
    cmd += ["--pfx", a.pfx, "--pfx-password", pfx_mdp] if a.pfx else []
    lancer(cmd)

    etape(f"Terminé en {time.time() - t0:.0f} s — dist/")
    for f in sorted(DIST.glob("*")):
        if f.is_file():
            print(f"  {f.name:42} {f.stat().st_size / 2**20:7.1f} Mo")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Arret as exc:
        print(f"\nÉCHEC : {exc}", file=sys.stderr)
        sys.exit(1)
