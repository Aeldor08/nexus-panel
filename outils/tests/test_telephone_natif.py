"""Accès téléphone en fenêtre native : activer / couper l'accès relance le serveur web via le crochet du
lanceur au lieu de quitter le processus (NEXUS.exe n'a pas de lancer.bat pour le relancer) ; état du
pare-feu et route de création de la règle limitée à la version exe."""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

BASE = Path(sys.argv[1])
os.chdir(BASE)
sys.path.insert(0, str(BASE))
os.environ.update(NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1")
import store

store.DATA_DIR = Path(tempfile.mkdtemp())
import db

db.DB_FILE = store.DATA_DIR / "nexus.db"
db.migrate()
from fastapi.testclient import TestClient

import app

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  [ECHEC]", m)


# --- relance par le crochet natif (le processus reste vivant) --------------------------------
appel = threading.Event()
app.RESTART_HOOK = appel.set
quitte = []
ancien_exit = os._exit
os._exit = lambda code: quitte.append(code)
try:
    app.schedule_restart()
    ok(appel.wait(5), "le crochet de relance du lanceur est appelé")
    time.sleep(0.3)
    ok(not quitte, f"le processus ne quitte pas en mode natif : {quitte}")
    # Sans crochet (lancer.bat) : comportement historique, code de relance
    app.RESTART_HOOK = None
    app.schedule_restart()
    time.sleep(1.6)
    ok(quitte == [app.RESTART_CODE], f"sans crochet : sortie avec RESTART_CODE : {quitte}")
finally:
    os._exit = ancien_exit
    app.RESTART_HOOK = None

# --- pare-feu : seulement pour la version exe --------------------------------------------------
c = TestClient(app.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8000")
r = c.get("/api/remote")
ok(r.status_code == 200 and r.json().get("pare_feu") is None, f"mode source : pare_feu = None : {r.json().get('pare_feu')}")
r = c.post("/api/remote/pare-feu", json={})
ok(r.status_code == 409, f"mode source : création de règle refusée : {r.status_code}")
# Depuis le réseau, /api/remote/* reste réservé au PC
app.remote_svc.enabled = True
c2 = TestClient(app.app, client=("192.168.1.50", 5000), base_url="http://127.0.0.1:8000")
r = c2.post("/api/remote/pare-feu", json={})
ok(r.status_code == 403, f"depuis le téléphone : refusé : {r.status_code}")
app.remote_svc.enabled = False

print(f"{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
