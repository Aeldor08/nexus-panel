"""Tests du module média (sans piloter aucun lecteur) : noms des applications et navigateurs, sites devinés,
résumé « sig », attente d'un changement, classement musique / vidéo des statistiques.
Usage : python outils/tests/test_media.py"""
import sys, threading, time
from pathlib import Path
BASE = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(BASE))
import media as M

passed = failed = 0
def ok(c, m):
    global passed, failed
    print(("OK   " if c else "ÉCHEC ") + m); passed += bool(c); failed += not c

for src, attendu in [("Spotify.exe", "Spotify"), ("Opera GX Stable", "Opera GX"), ("opera.exe", "Opera"), ("308046B0AF4A39CB", "Firefox"),
                     ("MSEdge", "Edge"), ("Chrome", "Chrome"), ("Brave", "Brave"), ("Vivaldi.ABCDEF", "Vivaldi"),
                     ("TheBrowserCompany.Arc_ttt!Arc", "Arc"), ("librewolf.exe", "LibreWolf"), ("Firefox", "Firefox"),
                     ("Deezer.62021768415AF_q3wt!Deezer.Music", "Deezer"), ("com.deezer.deezer-desktop", "Deezer"),
                     ("AppleInc.AppleMusicWin_nzyj5cx40ttqa!App", "Apple Music"), ("TIDAL.exe", "Tidal"), ("vlc.exe", "VLC"),
                     ("Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic", "Lecteur multimédia"),
                     ("Editeur.SuperLecteur_abc123!App", "SuperLecteur"), ("C:\\Jeux\\monlecteur.exe", "monlecteur")]:
    ok(M.app_name(src) == attendu, f"{src!r} -> {M.app_name(src)!r} (attendu {attendu!r})")
ok({"Opera GX", "Firefox", "Edge", "Chrome", "Brave", "Vivaldi", "Arc"} <= M.BROWSERS and "Deezer" not in M.BROWSERS, "navigateurs reconnus comme tels (Deezer n'en est pas un)")
ok(M.web_service("Chrome", "Daft Punk", "Deezer", "One More Time") == "Deezer", "site Deezer deviné dans un navigateur")
ok(M.web_service("Opera GX", "Ma chaîne", "", "Vidéo - YouTube") == "YouTube", "site YouTube deviné")
ok(M.web_service("Edge", "", "", "Recette") is None, "aucun site deviné sans indice")
a = [{"source": "s", "status": "playing", "title": "A", "position": 10}]
b = [{"source": "s", "status": "playing", "title": "A", "position": 42}]
c = [{"source": "s", "status": "paused", "title": "A", "position": 42}]
ok(M.signature(a) == M.signature(b), "la position qui avance ne change pas « sig »")
ok(M.signature(a) != M.signature(c), "lecture -> pause change « sig »")

# attente : sans lancer winrt (moniteur « vide »), on simule une publication d'état
M.AVAILABLE_SAVE = M.AVAILABLE; M.AVAILABLE = False
mon = M.MediaMonitor(); M.AVAILABLE = M.AVAILABLE_SAVE
t0 = time.time(); r = mon.wait(mon.state()["sig"], .5)
ok(.45 < time.time() - t0 < 1, f"sans changement : répond au bout du délai ({time.time() - t0:.2f} s)")
def publie():
    time.sleep(.2)
    with mon._cond:
        mon._state = {**mon._state, "sig": "nouveau"}; mon._cond.notify_all()
threading.Thread(target=publie).start()
t0 = time.time(); r = mon.wait(mon.state()["sig"], 5)
ok(r["sig"] == "nouveau" and time.time() - t0 < .5, f"changement publié : réponse immédiate ({time.time() - t0:.2f} s)")

# statistiques : Deezer (appli ou site) et autres lecteurs comptés en musique
import statistiques as S
class P:
    def __init__(self, n): self.info = {"name": n}
S.psutil.process_iter = lambda attrs=None: [P("explorer.exe")]
S.foreground_process = lambda: None; S.idle_seconds = lambda: 0.0
def cat(session):
    t = S.Tracker(media_state=lambda: {"sessions": [session]}); t.mapping = lambda: {}
    return [(a["nom"], a["categorie"]) for a in t.sample()["applis"]]
ok(cat({"source": "Deezer.62021768415AF_q3wt!Deezer.Music", "app": "Deezer", "status": "playing"}) == [("Deezer", "musique")], "appli Deezer : musique")
ok(cat({"source": "Chrome", "app": "Chrome", "site": "Deezer", "status": "playing"}) == [("Deezer", "musique")], "Deezer dans Chrome : musique, nommé Deezer")
ok(cat({"source": "Chrome", "app": "Chrome", "site": "YouTube", "status": "playing"}) == [("Chrome", "video")], "YouTube dans Chrome : vidéo")
ok(cat({"source": "TIDAL.exe", "app": "Tidal", "status": "playing"}) == [("Tidal", "musique")], "Tidal : musique")
print(f"\n{passed} réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
