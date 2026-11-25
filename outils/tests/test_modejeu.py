"""Mode jeu : bouton désactiver / réactiver, « ce n'est pas un jeu », surcouches jamais prises pour des jeux.
Faux processus, dossier de données temporaire (data/gamemode.json n'est pas touché), plan d'alimentation simulé.
Usage : python outils/tests/test_modejeu.py <dossier de NEXUS>"""

import sys
import tempfile
from pathlib import Path

BASE = Path(sys.argv[1])
sys.path.insert(0, str(BASE))
import store

store.DATA_DIR = Path(tempfile.mkdtemp())
import gamemode as G

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  [ECHEC]", m)


plans = []
G.set_power_plan = lambda guid: plans.append(guid) or True


class P:  # faux processus psutil
    def __init__(self, name, exe):
        self.info, self._exe = {"name": name}, exe

    def exe(self):
        return self._exe


def detect(procs):
    G.psutil.process_iter = lambda attrs=None: iter(procs)
    return gm._detect()


gm = G.GameMode.__new__(G.GameMode)  # sans le fil de détection : on pilote à la main
gm._lock = G.threading.Lock()
gm.in_game, gm.game, gm.since, gm._last_seen, gm.last_switch = False, None, None, 0.0, None
gm.cfg = gm._load()

# ---- surcouches : jamais des jeux, même installées dans un dossier de jeux ----
for name, exe in (
    (
        "EOSOverlayRenderer-Win64-Shipping.exe",
        r"C:\Program Files (x86)\Epic Games\Epic Online Services\managedArtifacts\x\EOSOverlayRenderer-Win64-Shipping.exe",
    ),
    ("EOSOverlayRenderer.exe", r"D:\SteamLibrary\steamapps\common\UnJeu\EOSOverlayRenderer.exe"),
    ("gameoverlayui.exe", r"C:\Program Files (x86)\Steam\steamapps\common\x\gameoverlayui.exe"),
    ("NVIDIA Overlay.exe", r"C:\Program Files\NVIDIA Corporation\NVIDIA app\CEF\NVIDIA Overlay.exe"),
):
    ok(detect([P(name, exe)]) is None, f"surcouche prise pour un jeu : {name}")
# ---- les vrais jeux restent détectés ----
ok(detect([P("VALORANT-Win64-Shipping.exe", r"C:\Riot Games\VALORANT\live\x.exe")]) == "VALORANT-Win64-Shipping.exe", "VALORANT détecté")
ok(detect([P("RDR2.exe", r"D:\Rockstar Games\Red Dead Redemption 2\RDR2.exe")]) == "RDR2.exe", "RDR2 détecté")
ok(detect([P("Hades.exe", r"D:\SteamLibrary\steamapps\common\Hades\x64\Hades.exe")]) == "Hades.exe", "jeu Steam détecté par son dossier")
ok(
    detect([P("EOSOverlayRenderer.exe", r"D:\Epic Games\x\EOSOverlayRenderer.exe"), P("Hades.exe", r"D:\SteamLibrary\steamapps\common\Hades\Hades.exe")])
    == "Hades.exe",
    "le jeu est trouvé même si une surcouche tourne à côté",
)

# ---- désactiver / réactiver pendant une partie ----
gm.in_game, gm.game, gm.since = True, "Hades.exe", 1000.0
st = gm.state()
ok(st["in_game"] and st["enabled"] and st["detected"], "en jeu : mode jeu en vigueur")
gm.update_config({"power_enabled": True})
plans.clear()
gm.update_config({"enabled": False})
st = gm.state()
ok(
    not st["in_game"] and st["detected"] and st["game"] == "Hades.exe" and not st["enabled"],
    f"désactivé : le panel ne s'allège plus, la détection continue (statistiques) : {st}",
)
ok(not gm.active, "propriété active fausse une fois désactivé")
ok(plans == [gm.cfg["normal_plan"]], f"désactivé en pleine partie : retour au plan normal ({plans})")
ok(store.load("gamemode")["enabled"] is False, "désactivation mémorisée (redémarrage)")
plans.clear()
gm.update_config({"enabled": True})
ok(gm.state()["in_game"] and plans == [gm.cfg["game_plan"]], f"réactivé : mode jeu et plan « jeu » ({plans})")

# ---- désactivé : la boucle ne touche jamais au plan d'alimentation ----
gm.update_config({"enabled": False})
plans.clear()
gm.in_game, gm.game = False, None
G.psutil.process_iter = lambda attrs=None: iter([P("Hades.exe", r"D:\SteamLibrary\steamapps\common\Hades\Hades.exe")])


class _FinBoucle(Exception):
    """Sortie propre de la boucle infinie pour le test (StopIteration est interdit dans
    une génératrice depuis Python 3.7, PEP 479)."""


G.time.sleep = lambda s: (_ for _ in ()).throw(_FinBoucle())  # un seul tour de boucle
try:
    gm._loop()
except _FinBoucle:
    pass
ok(gm.in_game and not gm.active and plans == [], f"désactivé : jeu vu mais plan inchangé ({plans})")
gm.update_config({"enabled": True})

# ---- « Ce n'est pas un jeu » : exception + sortie immédiate ----
gm.in_game, gm.game = True, "EOSOverlayRenderer.exe"
plans.clear()
gm.update_config({"ignore": gm.cfg["ignore"] + ["EOSOverlayRenderer.exe"]})
st = gm.state()
ok(not st["in_game"] and not st["detected"] and "EOSOverlayRenderer.exe" in gm.cfg["ignore"], f"exception : sortie immédiate du mode jeu {st}")
ok(plans == [gm.cfg["normal_plan"]], f"exception en pleine partie : plan normal ({plans})")

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
