"""Lance tous les tests SANS navigateur ni serveur en service (faux processus, faux haut-parleurs, faux GitHub,
dossiers temporaires) : utilisé par la CI et par outils/release.py. Les tests qui pilotent Edge
(test_ouverture, test_postit*) demandent un serveur de test sur le port 8001 : on les lance à la main.
Usage : python outils/tests/run_all.py   (code de sortie 0 = tout est passé)"""
import os
import subprocess
import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
BASE = ICI.parents[1]
TESTS = [
    ("test_media.py", []),
    ("test_stats_doublon.py", []),
    ("test_audio.py", [str(BASE)]),
    ("test_audio_api.py", [str(BASE)]),
    ("test_modejeu.py", [str(BASE)]),
    ("test_modejeu_pc.py", [str(BASE)]),
    ("test_maj.py", []),
]


def main() -> int:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1",
               NEXUS_OPEN_BROWSER="0")
    echecs = []
    for nom, args in TESTS:
        t0 = time.time()
        r = subprocess.run([sys.executable, str(ICI / nom), *args], cwd=BASE, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=900)
        sortie = (r.stdout or "") + (r.stderr or "")
        ok = r.returncode == 0 and "ÉCHEC" not in sortie
        print(f"{'OK   ' if ok else 'ÉCHEC'} {nom} ({time.time() - t0:.1f} s)")
        if not ok:
            echecs.append(nom)
            print("\n".join("    " + ligne for ligne in sortie.strip().splitlines()[-40:]))
    print(f"\n{len(TESTS) - len(echecs)}/{len(TESTS)} fichiers de tests passés")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
