"""Lance tous les tests SANS navigateur ni serveur en service (faux processus, faux haut-parleurs, faux GitHub,
dossiers temporaires) : utilisé par la CI et par outils/release.py. Les tests qui pilotent Edge
(test_ouverture, test_postit*) demandent un serveur de test sur le port 8001 : on les lance à la main.
Usage : python outils/tests/run_all.py [--couverture]   (code de sortie 0 = tout est passé)
--couverture : mesure la couverture du code (paquet coverage, requirements-dev.txt) et affiche le rapport."""

import os
import subprocess
import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
BASE = ICI.parents[1]
# Console Windows en cp1252 : ne jamais planter en affichant un échec accentué.
for flux in (sys.stdout, sys.stderr):
    try:
        flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
TESTS = [
    ("test_paths.py", [str(BASE)]),
    ("test_portable.py", [str(BASE)]),
    ("test_media.py", []),
    ("test_stats_doublon.py", []),
    ("test_audio.py", [str(BASE)]),
    ("test_audio_api.py", [str(BASE)]),
    ("test_modejeu.py", [str(BASE)]),
    ("test_modejeu_pc.py", [str(BASE)]),
    ("test_maj.py", []),
    ("test_maj_natif.py", [str(BASE)]),
    ("test_telephone_natif.py", [str(BASE)]),
    ("test_deck_sessions.py", [str(BASE)]),
    ("test_critiques.py", [str(BASE)]),
    ("test_migration.py", [str(BASE)]),
    ("test_focus_sante.py", []),
    ("test_philibert.py", [str(BASE)]),
    ("test_release_titre.py", []),
    ("test_superviseur.py", []),
    ("test_demarrage.py", []),
]


def main() -> int:
    couverture = "--couverture" in sys.argv[1:]
    if couverture:
        (BASE / ".couverture").mkdir(exist_ok=True)
        for f in (BASE / ".couverture").glob(".coverage*"):
            f.unlink()
    lanceur = [sys.executable, "-m", "coverage", "run", f"--rcfile={BASE / '.coveragerc'}"] if couverture else [sys.executable]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1", NEXUS_OPEN_BROWSER="0")
    echecs, ignores = [], []
    for nom, args in TESTS:
        # test_maj vérifie les archives de release à partir des fichiers suivis par Git :
        # dans une archive distribuée sans .git, il n'a pas de sens (il tourne dans le dépôt/CI).
        if nom == "test_maj.py" and not (BASE / ".git").exists():
            print("IGNORÉ test_maj.py (dépôt Git absent : test réservé au dépôt)")
            ignores.append(nom)
            continue
        t0 = time.time()
        r = subprocess.run(
            [*lanceur, str(ICI / nom), *args], cwd=BASE, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900
        )
        sortie = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0 and "ÉCHEC" not in sortie
        print(f"{'OK   ' if ok else 'ÉCHEC'} {nom} ({time.time() - t0:.1f} s)")
        if not ok:
            echecs.append(nom)
            lignes = sortie.strip().splitlines()
            # d'abord les vérifications en échec (où qu'elles soient dans la sortie), puis la fin de la sortie
            en_echec = [ligne for ligne in lignes if ligne.lstrip().startswith(("ÉCHEC", "Traceback")) or "Error" in ligne]
            if en_echec:
                print("    --- en échec ---")
                print("\n".join("    " + ligne for ligne in en_echec[:30]))
                print("    --- fin de la sortie ---")
            print("\n".join("    " + ligne for ligne in lignes[-40:]))
    print(
        f"\n{len(TESTS) - len(echecs) - len(ignores)}/{len(TESTS) - len(ignores)} fichiers de tests passés"
        + (f" ({len(ignores)} ignoré(s) : {', '.join(ignores)})" if ignores else "")
    )
    if couverture:
        rc = f"--rcfile={BASE / '.coveragerc'}"
        subprocess.run([sys.executable, "-m", "coverage", "combine", rc], cwd=BASE, capture_output=True)
        subprocess.run([sys.executable, "-m", "coverage", "report", rc], cwd=BASE)
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
