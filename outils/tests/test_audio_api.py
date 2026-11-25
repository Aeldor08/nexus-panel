"""Point d'accès POST /api/audio : champs seq / client, refus des valeurs invalides, ancien format accepté,
exécution hors de la boucle (le réglage ne bloque plus le serveur). Le mélangeur est remplacé par un
enregistreur : aucun vrai volume n'est touché."""

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


calls, threads = [], []


def fake_set(target, volume=None, muted=None, seq=None, client=None):
    threads.append(threading.current_thread().name)
    time.sleep(0.05)
    calls.append((target, volume, muted, seq, client))
    return True


app.mixer.set = fake_set
c = TestClient(app.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8000")

r = c.post("/api/audio", json={"target": "spotify.exe", "volume": 0.4, "seq": 7, "client": "abc"})
ok(r.status_code == 200 and calls[-1] == ("spotify.exe", 0.4, None, 7, "abc"), f"réglage avec seq/client : {r.status_code} {calls[-1:]}")
r = c.post("/api/audio", json={"target": "master", "volume": 0.3})
ok(r.status_code == 200 and calls[-1] == ("master", 0.3, None, None, None), "ancien format (sans seq)")
r = c.post("/api/audio", json={"target": "master", "muted": True})
ok(r.status_code == 200 and calls[-1][2] is True, "couper le son")
for body, why in (
    ({"target": "m", "volume": True}, "volume booléen"),
    ({"target": "m", "volume": "x"}, "volume texte"),
    ({"target": "m", "volume": 0.2, "seq": "1"}, "seq texte"),
    ({"target": "m", "volume": 0.2, "seq": -1}, "seq négatif"),
    ({"target": "m", "volume": 0.2, "client": "x" * 80}, "client trop long"),
    ({"target": "m", "muted": "oui"}, "muted texte"),
):
    n = len(calls)
    r = c.post("/api/audio", json=body)
    ok(r.status_code == 400 and len(calls) == n, f"refus : {why} ({r.status_code})")
ok(all(t != "MainThread" for t in threads), f"réglage exécuté hors de la boucle principale : {set(threads)}")

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
