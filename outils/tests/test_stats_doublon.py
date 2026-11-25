"""Test : un jeu n'est jamais compté deux fois dans les statistiques (ex. Valorant : le mode jeu voit
« VALORANT.exe », jeux.json compte « valorant-win64-shipping.exe »). Faux processus, aucune donnée touchée.
Usage : python outils/tests/test_stats_doublon.py"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
import statistiques as S

passed = failed = 0


def ok(c, m):
    global passed, failed
    print(("OK   " if c else "ÉCHEC ") + m)
    passed += bool(c)
    failed += not c


class P:
    def __init__(self, n):
        self.info = {"name": n}


def mesure(procs, jeu_mode_jeu, premier_plan=None):
    S.psutil.process_iter = lambda attrs=None: [P(n) for n in procs]
    S.foreground_process = lambda: premier_plan
    S.idle_seconds = lambda: 0.0
    t = S.Tracker(game_state=lambda: {"game": jeu_mode_jeu} if jeu_mode_jeu else {}, media_state=lambda: {})
    t.mapping = lambda: {"valorant-win64-shipping.exe": {"nom": "Valorant", "categorie": "jeu", "ouverte": False}}
    return sorted(a["nom"] for a in t.sample()["applis"] if a["categorie"] == "jeu")


r = mesure(["VALORANT.exe", "VALORANT-Win64-Shipping.exe", "explorer.exe"], "VALORANT.exe")
ok(r == ["Valorant"], f"Valorant compté une seule fois ({r})")
r = mesure(["RedM_b1491_GTAProcess.exe"], "RedM_b1491_GTAProcess.exe")
ok(r == ["RedM_b1491_GTAProcess"], f"jeu absent de jeux.json : compté par le mode jeu ({r})")
r = mesure(["VALORANT-Win64-Shipping.exe"], None)
ok(r == ["Valorant"], f"jeu de jeux.json sans mode jeu : compté ({r})")
r = mesure(["explorer.exe"], None)
ok(r == [], f"aucun jeu : rien ({r})")
print(f"\n{passed} réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
