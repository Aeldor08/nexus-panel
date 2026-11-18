"""Superviseur de NEXUS (icône près de l'horloge) : redémarrages, mises à jour, plantages, journal, Python privé,
lancer.bat. Sans icône (pas besoin de pystray), avec un faux app.py dans un dossier temporaire.
Usage : python outils/tests/test_superviseur.py"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
import superviseur as S  # noqa: E402

echecs = 0


def ok(cond, msg):
    global echecs
    print(("OK    " if cond else "ÉCHEC ") + msg)
    if not cond:
        echecs += 1


FAUX_APP = r'''
import json, os, sys, time
from pathlib import Path
ici = Path(__file__).parent
codes = json.loads((ici / "codes.json").read_text())
n = int((ici / "n.txt").read_text()) if (ici / "n.txt").exists() else 0
(ici / "n.txt").write_text(str(n + 1))
with open(ici / "lancements.txt", "a", encoding="utf-8") as f:
    f.write(json.dumps({k: os.environ.get(k) for k in ("NEXUS_LANCEUR", "NEXUS_OPEN_BROWSER", "PYTHONNOUSERSITE",
                                                        "PYTHONPATH")}) + "\n")
print("serveur lancé : élan n°", n + 1, flush=True)
code = codes[min(n, len(codes) - 1)]
if code == "dort":
    time.sleep(60)
    code = 0
sys.exit(code)
'''
FAUX_MAJ = r'''
from pathlib import Path
ici = Path(__file__).parent
(ici / "maj" / "en_cours.json").unlink()
with open(ici / "lancements.txt", "a", encoding="utf-8") as f:
    f.write("MAJ\n")
'''


def dossier(codes, maj=False):
    d = Path(tempfile.mkdtemp(prefix="nx-sup-"))
    (d / "app.py").write_text(FAUX_APP, encoding="utf-8")
    (d / "maj_demarrage.py").write_text(FAUX_MAJ, encoding="utf-8")
    (d / "codes.json").write_text(json.dumps(codes))
    (d / "VERSION").write_text("9.9.9")
    (d / "config.json").write_text("{}")
    if maj:
        (d / "maj").mkdir()
        (d / "maj" / "en_cours.json").write_text("{}")
    return d


def lancements(d):
    f = d / "lancements.txt"
    return [json.loads(x) if x.startswith("{") else x for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []


def sup(d, **kw):
    notes = []
    s = S.Superviseur(d, sys.executable, lhm=False, configurer=False, delai_plantage=.05, prefixe=d,
                      notifier=lambda t, m: notes.append((t, m)), **kw)
    return s, notes


def attendre(cond, t=20):
    fin = time.time() + t
    while time.time() < fin:
        if cond():
            return True
        time.sleep(.05)
    return False


os.environ.pop("PYTHONPATH", None)
os.environ["PYTHONPATH"] = "C:\\ailleurs"        # doit être retiré pour le serveur

# 1. code 3 (redémarrage demandé) puis 0 (arrêt normal)
d = dossier([3, 0])
s, notes = sup(d)
rc = s.boucle()
L = lancements(d)
ok(rc == 0 and len(L) == 2, f"code 3 : relancé tout de suite, code 0 : arrêt ({len(L)} lancements)")
ok(L[0]["NEXUS_OPEN_BROWSER"] == "1" and L[1]["NEXUS_OPEN_BROWSER"] == "0", "le navigateur ne s'ouvre qu'au premier lancement")
ok(all(x["NEXUS_LANCEUR"] == "1" for x in L), "NEXUS_LANCEUR=1 : app.py sait qu'on le relance (mises à jour)")
ok(all(x["PYTHONNOUSERSITE"] == "1" and x["PYTHONPATH"] is None for x in L),
   "serveur isolé : ni paquets « utilisateur » ni PYTHONPATH de Windows")
log = (d / "logs" / "nexus.log").read_text(encoding="utf-8")
ok("serveur lancé : élan n° 1" in log and "élan n° 2" in log, "messages du serveur dans logs\\nexus.log (accents compris)")
ok("[Icône] redémarrage demandé par NEXUS" in log and "serveur arrêté normalement" in log, "le journal raconte ce que fait l'icône")
ok(not notes, "aucune notification quand tout va bien")

# 2. mise à jour préparée : maj_demarrage.py AVANT le serveur, puis plus jamais
d = dossier([3, 0], maj=True)
s, _ = sup(d)
s.boucle()
L = lancements(d)
ok(L[0] == "MAJ" and isinstance(L[1], dict) and L.count("MAJ") == 1, f"mise à jour mise en place avant le serveur ({L[:2]})")

# 3. code 4 : port déjà pris → notification, arrêt
d = dossier([4])
s, notes = sup(d)
rc = s.boucle()
ok(rc == 4 and len(lancements(d)) == 1 and notes and "déjà utilisé" in notes[0][1], "code 4 : notification « port déjà utilisé », pas de relance")

# 4. plantages : relancé, puis abandon au 5ᵉ d'affilée (l'icône reste : Redémarrer ou Quitter)
d = dossier([1])
s, notes = sup(d)
t = threading.Thread(target=s.boucle, daemon=True)
t.start()
ok(attendre(lambda: s.etat.startswith("arrêté")), f"5 plantages d'affilée : arrêté ({s.etat})")
ok(len(lancements(d)) == S.MAX_PLANTAGES and notes and "5 fois" in notes[-1][1], "relancé 4 fois après un plantage, puis notification")
s.redemarrer()                                     # Redémarrer : on repart pour 5 essais
ok(attendre(lambda: len(lancements(d)) == 2 * S.MAX_PLANTAGES and s.etat.startswith("arrêté")),
   "Redémarrer après l'abandon : nouveaux essais")
s.arreter()
t.join(5)
ok(not t.is_alive(), "Quitter pendant l'attente : la boucle s'arrête")

# 5. Redémarrer pendant que le serveur tourne, puis Quitter
d = dossier(["dort"])
s, _ = sup(d)
t = threading.Thread(target=s.boucle, daemon=True)
t.start()
ok(attendre(lambda: s.proc is not None and len(lancements(d)) == 1), "serveur en marche")
s.redemarrer()
ok(attendre(lambda: len(lancements(d)) == 2 and s.proc is not None), "Redémarrer : serveur arrêté puis relancé")
p = s.proc
s.arreter()
t.join(15)
ok(not t.is_alive() and p.poll() is not None, "Quitter : le serveur est arrêté et la boucle finie")

# 6. dépendances : pip seulement si requirements.txt a changé (marque dans le dossier du Python)
d = dossier([0])
(d / "requirements.txt").write_text("fastapi>=0.110\n")
s, _ = sup(d)
appels = []


class FauxPip:
    def __init__(self, rc):
        self.rc = rc

    def wait(self):
        return self.rc


s._lancer = lambda args, **kw: (appels.append(args), FauxPip(0))[1]
ok(s.dependances() and appels and appels[0][:3] == ["-m", "pip", "install"], "requirements.txt nouveau : pip install")
ok((d / "requirements.installe").read_text() == "fastapi>=0.110\n", "marque des dépendances installées écrite")
appels.clear()
ok(s.dependances() and not appels, "requirements.txt inchangé : pas de pip (démarrage rapide)")
(d / "requirements.txt").write_text("fastapi>=0.110\npystray>=0.19\n")
s._lancer = lambda args, **kw: (appels.append(args), FauxPip(1))[1]
notes = []
s.notifier = lambda t, m: notes.append(m)
ok(not s.dependances() and notes and "Internet" in notes[0], "pip en échec : pas de démarrage, notification")

# 7. journal : au-delà de 1 Mo, il devient nexus.1.log
d = dossier([0])
(d / "logs").mkdir()
(d / "logs" / "nexus.log").write_text("x" * (S.JOURNAL_MAX + 10))
s, _ = sup(d)
s.boucle()
ok((d / "logs" / "nexus.1.log").stat().st_size > S.JOURNAL_MAX and (d / "logs" / "nexus.log").stat().st_size < 10_000,
   "journal trop gros : mis de côté (nexus.1.log), nouveau journal")

# 8. Python privé : à jour seulement si runtime\ a la version de outils\python-prive.json
d = Path(tempfile.mkdtemp(prefix="nx-rt-"))
(d / "outils").mkdir()
(d / "outils" / "python-prive.json").write_text(json.dumps({"version": "3.12.10"}))
ok(not S.python_prive_a_jour(d), "pas de runtime\\ : à installer")
(d / "runtime").mkdir()
(d / "runtime" / "python.exe").write_text("")
(d / "runtime" / "VERSION-PYTHON").write_text("3.12.9\n")
ok(not S.python_prive_a_jour(d), "runtime\\ d'une autre version : à refaire")
(d / "runtime" / "VERSION-PYTHON").write_text("3.12.10\r\n")
ok(S.python_prive_a_jour(d), "runtime\\ à la bonne version : rien à faire")
pins = json.loads((BASE / "outils" / "python-prive.json").read_text(encoding="utf-8"))
ok(re.fullmatch(r"3\.\d+\.\d+", pins["version"]) and re.fullmatch(r"[0-9A-F]{64}", pins["sha256"])
   and pins["url"].startswith("https://api.nuget.org/") and pins["version"] in pins["url"],
   "outils\\python-prive.json : version, adresse nuget.org et empreinte SHA256")

# 9. une seule icône par dossier NEXUS (un 2ᵉ lancement ouvre juste le panel)
code = "import sys; sys.path.insert(0, r'%s'); import superviseur as S; from pathlib import Path; " \
       "print(S.deja_ouvert(Path(r'%s')))"
un = subprocess.Popen([sys.executable, "-c", code % (BASE, d) + "; import time; time.sleep(4)"], stdout=subprocess.PIPE, text=True)
time.sleep(1.5)
deux = subprocess.run([sys.executable, "-c", code % (BASE, d)], capture_output=True, text=True).stdout.strip()
autre = subprocess.run([sys.executable, "-c", code % (BASE, d / "autre")], capture_output=True, text=True).stdout.strip()
un.kill()
ok(deux == "True" and autre == "False", f"une icône par dossier : 2ᵉ lancement détecté ({deux}), autre dossier libre ({autre})")

# 10. lancer.bat / installer.bat : fins de ligne Windows, repères présents, Python privé avant .venv
for nom in ("lancer.bat", "installer.bat", "configurer.bat", "restaurer_version.bat", "preparer_partage.bat"):
    b = (BASE / nom).read_bytes()
    ok(b.count(b"\n") == b.count(b"\r\n") and b"\r\r" not in b, f"{nom} : fins de ligne CRLF (sinon cmd.exe se perd dans les goto)")
t = (BASE / "lancer.bat").read_text(encoding="ascii")
reperes = set(re.findall(r"(?im)^:(\w+)", t))
vises = set(re.findall(r"(?i)\b(?:goto|call)\s+:?(\w+)", t)) - {"installer"}
ok(vises <= reperes, f"lancer.bat : tous les repères visés existent ({sorted(vises - reperes)})")
ok("serveur" in reperes and t.index(":serveur") < t.index(":trop"),
   "lancer.bat garde « :serveur » (une ancienne fenêtre NEXUS y revient après une mise à jour)")
apres = t[t.index(":serveur"):t.index(":trop")]
ok("call :trouver" in apres, "après « :serveur », le Python est recherché à nouveau (rien ne dépend de ce qui précède)")
b = (BASE / "lancer.bat").read_bytes()
fin_maj = b.index(b"maj_demarrage.py\r\n") + len(b"maj_demarrage.py\r\n")
ok(fin_maj == 3480 and b[fin_maj:].startswith(b"call :app\r\n"),
   f"lancer.bat calé : « call :app » à l'octet 3480 comme le lancement du serveur dans l'ancien lancer.bat ({fin_maj})")
debut = t[:t.index("\n:console\n")]
ok("call :python_prive" in debut and "call :dependances" in debut and not re.search(r"(?m)^call :app", debut),
   "lancer.bat : Python privé et dépendances avant le démarrage, le serveur seulement en mode console")
tr = t[t.index(":trouver"):]
ok(tr.index("runtime\\python.exe") < tr.index(".venv\\Scripts\\python.exe"), "le Python privé passe avant l'ancien .venv")

print(f"\n{'ÉCHEC' if echecs else 'OK'} : {echecs} vérification(s) en échec")
sys.exit(1 if echecs else 0)
