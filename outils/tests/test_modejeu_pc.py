"""Mode jeu actif : l'onglet PC n'est jamais mis en pause (les processus continuent d'être relevés).
Jeu simulé, dossier de données temporaire. Usage : python outils/tests/test_modejeu_pc.py <dossier de NEXUS>"""
import os, sys, tempfile, time
from pathlib import Path

BASE = Path(sys.argv[1]); os.chdir(BASE); sys.path.insert(0, str(BASE))
os.environ.update(NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1")
import store; store.DATA_DIR = Path(tempfile.mkdtemp())
import db; db.DB_FILE = store.DATA_DIR / "nexus.db"; db.migrate()
import app
from fastapi.testclient import TestClient

passed = failed = 0
def ok(c, m):
    global passed, failed
    if c: passed += 1
    else: failed += 1; print("  [ECHEC]", m)

c = TestClient(app.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8000")
time.sleep(5)                                              # 2 premières mesures des processus
app.game_mode._detect = lambda: "JeuDeTest.exe"            # un jeu « tourne »
with app.game_mode._lock:
    app.game_mode.in_game, app.game_mode.game, app.game_mode.since = True, "JeuDeTest.exe", time.time()
    app.game_mode.cfg["enabled"] = True
ok(app.game_mode.active, "mode jeu en vigueur pendant le test")

def procs():
    return c.get("/api/stats").json()["processes"]

a = procs()
seen = []
for _ in range(4):                                         # ~8 s : plusieurs relevés de 2 s
    time.sleep(2.2)
    seen.append(procs())
ok(not any(p.get("paused") for p in [a] + seen), f"processus marqués « en pause » : {[p.get('paused') for p in [a] + seen]}")
sigs = {str([(x.get('name'), x.get('cpu')) for x in p["top_cpu"][:8]]) for p in [a] + seen}
ok(len(sigs) > 1, "la liste des processus change pendant le mode jeu (relevés vivants)")
ok(all(p["count"] > 0 for p in seen), "nombre de processus présent")
st = c.get("/api/stats").json()
ok(st["gamemode"]["in_game"] is True, "l'état indique bien le mode jeu")

print(f"\n{passed} tests réussis, {failed} échec(s)", flush=True)
sys.stdout.flush()
os._exit(1 if failed else 0)                               # (sans attendre les fils de fond du serveur)
