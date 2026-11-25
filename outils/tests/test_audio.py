"""Tests du mélangeur côté serveur (audio.AudioMixer), avec de FAUX haut-parleurs et de FAUSSES sessions :
aucun vrai volume du PC n'est touché. Le vrai fil audio (file de travaux, thread COM) est utilisé tel quel.
Règle vérifiée : une fois set() revenu, toute lecture de l'état montre la nouvelle valeur (jamais l'ancienne),
même quand d'autres requêtes lisent l'état en même temps (sondages du mélangeur et des jauges)."""

import random, sys, threading, time
from pathlib import Path

BASE = Path(sys.argv[1])
sys.path.insert(0, str(BASE))
import audio

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  [ECHEC]", m)


if not audio.AVAILABLE:
    print("pycaw indisponible : test sauté")
    sys.exit(0)

store = {"master": 0.5, "spotify.exe": 0.2}


class Vol:  # interface SimpleAudioVolume / EndpointVolume simulée
    def __init__(self, k):
        self.k = k

    def GetMasterVolume(self):
        return store[self.k]

    def SetMasterVolume(self, v, _ctx):
        time.sleep(random.uniform(0.002, 0.012))
        store[self.k] = v

    def GetMasterVolumeLevelScalar(self):
        return store[self.k]

    def SetMasterVolumeLevelScalar(self, v, _ctx):
        time.sleep(random.uniform(0.002, 0.012))
        store[self.k] = v

    def GetMute(self):
        return False

    def SetMute(self, m, _ctx):
        pass


class Sess:
    def __init__(self):
        self.SimpleAudioVolume = Vol("spotify.exe")


class Spk:
    FriendlyName = "Haut-parleurs (test)"

    def __init__(self):
        self.EndpointVolume = Vol("master")


def fake_read():
    v = store["spotify.exe"], store["master"]  # lu au DÉBUT…
    time.sleep(random.uniform(0.005, 0.03))  # … puis la lecture complète prend du temps (≈ 15-20 ms en vrai)
    return {
        "available": True,
        "error": None,
        "device": {"name": "test", "volume": round(v[1], 3), "muted": False, "peak": 0},
        "apps": [
            {"key": "spotify.exe", "name": "Spotify", "volume": round(v[0], 3), "muted": False, "peak": 0, "active": True, "sessions": 1, "has_icon": False}
        ],
    }


m = audio.AudioMixer()
m._read = fake_read
m._levels = lambda: {"master": 0, "apps": {}}
m._speakers = lambda: Spk()
m._groups = lambda: {"spotify.exe": {"key": "spotify.exe", "name": "Spotify", "exe": None, "sessions": [Sess()]}}

stop = False


def lecteur(fn):
    while not stop:
        fn()
        time.sleep(random.uniform(0, 0.01))


th = [
    threading.Thread(target=lecteur, args=(m.state,), daemon=True),
    threading.Thread(target=lecteur, args=(m.levels,), daemon=True),
    threading.Thread(target=lecteur, args=(m.state,), daemon=True),
]
for t in th:
    t.start()

perimes, n = [], 300
for i in range(n):
    target = "spotify.exe" if i % 3 else "master"
    v = round(random.uniform(0.05, 0.95), 3)
    m.set(target, v)
    st = m.state()
    got = st["device"]["volume"] if target == "master" else next(a["volume"] for a in st["apps"] if a["key"] == target)
    if abs(got - v) > 0.002:
        perimes.append((target, v, got))
    time.sleep(random.uniform(0, 0.02))
stop = True
ok(not perimes, f"lecture périmée juste après un réglage : {len(perimes)} / {n} (ex. {perimes[:3]})")

# Réglages venus de plusieurs requêtes à la fois : le dernier demandé gagne toujours
for essai in range(20):
    vals = [round(random.uniform(0.1, 0.9), 3) for _ in range(6)]
    seq = []

    def envoi(v, k):
        time.sleep(k * 0.004)  # envoyés dans l'ordre, à 4 ms d'écart
        m.set("spotify.exe", v, seq=k + 1 + essai * 10)

    ts = [threading.Thread(target=envoi, args=(v, k)) for k, v in enumerate(vals)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    seq.append(store["spotify.exe"])
    if abs(store["spotify.exe"] - vals[-1]) > 0.002:
        ok(False, f"envois simultanés : volume final {store['spotify.exe']} au lieu du dernier demandé {vals[-1]} ({vals})")
        break
else:
    ok(True, "")

# Deux pages (PC + téléphone) : chacune a ses numéros, l'une ne bloque pas l'autre
m.set("spotify.exe", 0.31, seq=5, client="pc")
m.set("spotify.exe", 0.62, seq=1, client="tel")
ok(abs(store["spotify.exe"] - 0.62) < 0.002, f"deux pages : le réglage du téléphone doit passer ({store['spotify.exe']})")
m.set("spotify.exe", 0.1, seq=4, client="pc")  # ancien numéro de la page PC : ignoré
ok(abs(store["spotify.exe"] - 0.62) < 0.002, f"ancienne requête ignorée ({store['spotify.exe']})")
# Ancien format (sans seq) : toujours accepté
m.set("master", 0.44)
ok(abs(store["master"] - 0.44) < 0.002, "réglage sans numéro d'ordre")

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
