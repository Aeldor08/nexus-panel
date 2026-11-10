"""Tests sans navigateur : minuteur Pomodoro (phases, pause, passage, arrêt), temps de focus compté en « travail »
dans les statistiques, journal d'activité (écriture, lecture, filtre, anti-répétition, rotation), capture des
erreurs (fenêtre Santé), classement des processus et fermeture (processus vitaux refusés, NEXUS refusé,
vrai processus de test fermé). Dossier de données temporaire : rien de personnel n'est touché.
Usage : python outils/tests/test_focus_sante.py"""
import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
import store  # noqa: E402

store.DATA_DIR = Path(tempfile.mkdtemp(prefix="nexus-test-focus-"))
import activite  # noqa: E402
import focus as focus_mod  # noqa: E402
import sante  # noqa: E402
import stats  # noqa: E402
import statistiques as S  # noqa: E402

activite.FICHIER = store.DATA_DIR / "activite.jsonl"
focus_mod.FICHIER = store.DATA_DIR / "focus.json"
passed = failed = 0


def ok(c, m):
    global passed, failed
    print(("OK    " if c else "ÉCHEC ") + m, flush=True)
    passed += bool(c)
    failed += not c


# ---- Pomodoro ------------------------------------------------------------------
horloge = [1_000_000.0]
focus_mod.time.time = lambda: horloge[0]
notes = []
f = focus_mod.Focus(journal=lambda *a, **k: notes.append(a))
e = f.demarrer({"travail_min": 25, "pause_min": 5, "longue_min": 15, "cycles": 2})
ok(e["actif"] and e["phase"] == "travail" and e["reste_s"] == 1500, f"session démarrée : 25 min de travail ({e['reste_s']} s)")
ok(f.en_travail(), "en travail : compté par les statistiques")
horloge[0] += 1500
e = f.etat()
ok(e["phase"] == "pause" and e["seances"] == 1 and abs(e["reste_s"] - 300) < 1, f"après 25 min : pause courte ({e['phase']}, {e['reste_s']} s)")
ok(not f.en_travail(), "pendant la pause : pas compté en travail")
horloge[0] += 300
e = f.etat()
ok(e["phase"] == "travail", "après la pause : retour au travail")
horloge[0] += 100
f.suspendre()
horloge[0] += 10_000                             # la suspension fige le temps
e = f.etat()
ok(e["suspendu"] and abs(e["reste_s"] - 1400) < 1 and not f.en_travail(), f"suspendu : temps figé ({e['reste_s']} s)")
f.reprendre()
horloge[0] += 1400
e = f.etat()
ok(e["phase"] == "longue" and e["seances"] == 2, f"2e séance terminée : pause longue ({e['phase']})")
f.passer()
e = f.etat()
ok(e["phase"] == "travail", "« passer » : pause sautée")
horloge[0] += 600
f.passer()                                        # séance écourtée à 10 min
e = f.etat()
ok(e["phase"] == "pause" and abs(e["travail_s"] - (1500 * 2 + 600)) < 2, f"séance écourtée : seul le temps fait compte ({e['travail_s']} s)")
g = focus_mod.Focus()
ok(g.etat()["actif"] and g.etat()["phase"] == "pause", "état gardé sur le disque (redémarrage du panel)")
f.arreter()
ok(not f.etat()["actif"] and any("terminée" in n[1] for n in notes), "arrêt : noté dans le journal")
r = f.regler({"travail_min": 999, "pause_min": 0, "profil_sobre": False})["reglages"]
ok(r["travail_min"] == 180 and r["pause_min"] == 1 and r["profil_sobre"] is False, f"réglages bornés ({r})")

# ---- statistiques : le focus compte en « travail », sans double compte --------------
vrai_iter = S.psutil.process_iter
S.psutil.process_iter = lambda attrs=None: []
S.foreground_process = lambda: "code.exe"
S.idle_seconds = lambda: 9999.0                   # personne au clavier (lecture sur papier)
t = S.Tracker(en_focus=lambda: True)
t.mapping = lambda: {"code.exe": {"nom": "VS Code", "categorie": "travail", "ouverte": False}}
s = t.sample()
ok(s["actif"] and s["applis"] == [{"nom": S.FOCUS_NOM, "categorie": "travail"}], f"focus : présent et compté en travail une seule fois ({s['applis']})")
t.en_focus = lambda: False
s = t.sample()
ok(not s["actif"] and s["applis"] == [], "sans focus et inactif : rien de compté")
S.psutil.process_iter = vrai_iter                 # (même module psutil que stats.py)

# ---- journal d'activité ------------------------------------------------------------------
activite.noter("deck", "Verrouiller", "ok", "", "127.0.0.1", "web")
activite.noter("appareil", "appareil non appairé", "refusé", "/api/stats", "192.168.1.50", unique_s=600)
activite.noter("appareil", "appareil non appairé", "refusé", "/api/stats", "192.168.1.50", unique_s=600)
activite.noter("maj", "installation validée", "ok", "1.0.1 → 1.0.2")
lu = activite.lire(10)
ok(len(lu) == 3 and lu[0]["action"] == "installation validée", f"journal : 3 évènements, le plus récent d'abord ({[x['action'] for x in lu]})")
ok(len(activite.lire(10, "appareil")) == 1, "journal : filtre par type, répétitions ignorées")
activite.MAX_LIGNES, activite.GARDER = 50, 30
for i in range(60):
    activite.noter("deck", f"bouton {i}")
n = len(activite.FICHIER.read_text(encoding="utf-8").splitlines())
ok(n <= 50, f"journal : taille bornée ({n} lignes)")
ok(not any("password" in json.dumps(x) or "jeton" in json.dumps(x).lower() for x in activite.lire(200) if x["cat"] == "deck"), "journal : aucun secret")

# ---- capture des erreurs ---------------------------------------------------------------
flux = io.StringIO()
d = sante._Double(flux, "console")
d.write("[Config] AVERTISSEMENT : seuil invalide\nligne normale\n")
d.write("Traceback (most recent call last):\n  File \"x.py\", line 1, in <module>\n    boum()\nRuntimeError: ça casse\nsuite\n")
d.write('INFO:     127.0.0.1:5 - "GET /api/x HTTP/1.1" 500 Internal Server Error\n')
lst = sante.liste()
ok(flux.getvalue().count("\n") == 8, "console : tout est encore affiché")
ok(any(x["niveau"] == "avertissement" and "seuil" in x["message"] for x in lst), "avertissement capté")
ok(any("RuntimeError: ça casse" in x["message"] for x in lst), "trace Python captée en un seul évènement")
ok(any(" 500 " in x["message"] for x in lst) and not any("ligne normale" in x["message"] for x in lst), "erreur 500 captée, lignes normales ignorées")

# ---- processus ---------------------------------------------------------------------------
pm = stats.ProcessMonitor.__new__(stats.ProcessMonitor)    # sans le fil d'échantillonnage
pm._lock = __import__("threading").Lock()
pm._procs, pm._tous, pm.paused, pm._ncpu = {}, [], False, 1
pm._result = {"top_cpu": [], "top_ram": [], "count": 0}
pm._sample()
c = pm.classement("ram")
ok(c["total"] > 10 and c["processus"][0]["ram"] >= c["processus"][-1]["ram"], f"classement par mémoire ({c['total']} programmes)")
ok(any(p["protege"] for p in c["processus"] if p["name"].lower() in ("svchost.exe", "csrss.exe", "explorer.exe")), "processus vitaux marqués « protégé »")
for nom in ("svchost.exe", "csrss.exe", "explorer.exe"):
    try:
        pm.fermer(nom)
        ok(False, f"{nom} ne doit pas pouvoir être fermé")
    except ValueError:
        ok(True, f"{nom} : fermeture refusée")
# NEXUS lui-même : vérifié SANS appeler fermer() sur python.exe (le vrai NEXUS du PC en est un aussi)
import os  # noqa: E402
moi = stats._pids_nexus()
ok(os.getpid() in moi, "NEXUS (ce processus et ses parents) repéré")
mon_nom = __import__("psutil").Process().name()
ok(any(p["protege"] for p in pm.classement("cpu", 500)["processus"] if p["name"] == mon_nom), f"le groupe de NEXUS ({mon_nom}) est marqué « protégé »")
cible = subprocess.Popen(["ping", "-n", "120", "127.0.0.1"], stdout=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
time.sleep(.5)
r = pm.fermer("PING.EXE")
time.sleep(.3)
ok(cible.poll() is not None and r["fermes"] >= 1, f"vrai processus de test fermé ({r})")
try:
    pm.fermer("PING.EXE")
    ok(False, "plus rien à fermer")
except ValueError:
    ok(True, "plus aucun processus de ce nom : message clair")

print(f"\n{passed} OK, {failed} échec(s)")
sys.exit(1 if failed else 0)
