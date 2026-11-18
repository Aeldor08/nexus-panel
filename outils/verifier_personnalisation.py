"""Vérifie qu'une copie de NEXUS contient les invariants de la version native/portable.

À lancer depuis la racine du projet :
    .venv\\Scripts\\python.exe outils\\verifier_personnalisation.py

Sortie 0 = tous les invariants sont présents. Sortie 1 = au moins un manque.
Ce script ne remplace pas les tests : il vérifie les fichiers et les marqueurs
structurants après une fusion avec une nouvelle version upstream.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RACINE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BASE

FICHIERS = [
    "paths.py",
    "logs.py",
    "nexus_launcher.py",
    "lancer_native.bat",
    "Creer-NEXUS-Portable.bat",
    "requirements-native.txt",
    "nexus.spec",
    "installer.iss",
    "maj_natif.py",
    "outils/build_native.py",
    "outils/sign_native.ps1",
    "outils/appliquer_maj.ps1",
    "outils/verifier_personnalisation.py",
    "outils/tests/test_paths.py",
    "outils/tests/test_maj_natif.py",
    "outils/tests/test_portable.py",
    ".github/workflows/ci.yml",
    ".github/workflows/build-native.yml",
    "docs/GITHUB-FORK.md",
    "docs/MODOP-PORTABLE.md",
    "docs/PERSONNALISATION.md",
    "docs/PATCH-PERSONNALISATION-1.6.0.patch",
]

MARQUEURS = {
    "paths.py": ["FROZEN", "NEXUS_PORTABLE", "USER_ROOT", "DATA_DIR", "INSTALL_DIR"],
    "nexus_launcher.py": ["portable.flag", "_portable_flag", "_mutex_name", "--configure", "NEXUS_PORTABLE"],
    "maj.py": ["maj_natif", "installateur", "sha256_installateur", "verifier_signature",
               "construire_job_installation", "sauvegarder_installation"],
    "maj_natif.py": ["verifier_signature", "evaluer_signature", "sauvegarder_installation",
                     "construire_job_installation", "lancer_helper", "marquer_demarrage_ok"],
    "app.py": ["start_services", "stop_services", "maj_natif", "marquer_demarrage_ok", "RESTART_CODE"],
    "audio.py": ["comtypes.client.gen_dir"],
    "bot.py": ["def stop"],
    "reminders.py": ["def stop"],
    "statistiques.py": ["def stop", "paths.JEUX_FILE"],
    "store.py": ["DATA_DIR = paths.DATA_DIR"],
    "deck.py": ["paths.DECK_FILE", "paths.ACTIONS_DIR", "paths.FROZEN"],
    "profiles.py": ["PROFILES_DIR = paths.PROFILES_DIR"],
    "stats.py": ["FAN_NAMES_FILE = paths.FAN_NAMES_FILE", "paths.INSTALL_DIR"],
    "config.py": ['"signature": "auto"', '"certificat": ""'],
    "nexus.spec": ["appliquer_maj.ps1", "panel.ico", "collect_all"],
    "outils/build_native.py": ["write_portable", "--portable", "write_hashes"],
    "installer.iss": ["[InstallDelete]", "_internal", "Configurer NEXUS", "PrivilegesRequired=lowest"],
    "static/js/version.js": ["maj.natif", "maj.portable", "d.taille"],
    "static/js/rappels.js": ["window.NEXUS_NATIVE"],
    "static/js/philibert.js": ["window.NEXUS_NATIVE"],
    "outils/tests/run_all.py": ["test_maj_natif.py", "test_portable.py"],
}


def lire(rel: str) -> str:
    try:
        return (RACINE / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def main() -> int:
    manquants = []
    for rel in FICHIERS:
        if not (RACINE / rel).is_file():
            manquants.append(f"fichier absent : {rel}")
    for rel, extraits in MARQUEURS.items():
        contenu = lire(rel)
        if not contenu:
            manquants.append(f"fichier illisible : {rel}")
            continue
        for extrait in extraits:
            if extrait not in contenu:
                manquants.append(f"{rel} : marqueur absent « {extrait} »")
    if manquants:
        print(f"Personnalisation incomplète dans {RACINE} :")
        for item in manquants:
            print("  -", item)
        return 1
    print(f"Personnalisation complète : {RACINE}")
    print(f"  {len(FICHIERS)} fichiers, {sum(len(v) for v in MARQUEURS.values())} marqueurs vérifiés.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
