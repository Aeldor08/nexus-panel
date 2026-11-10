r"""Statistiques personnelles : un service léger, dans le même programme que le serveur.

Toutes les TICK secondes (10 s), il note :
  - actif / inactif : dernier évènement clavier ou souris de Windows (GetLastInputInfo) ; un jeu au premier plan
    compte comme actif (la manette n'est pas vue par Windows comme du clavier ou de la souris) ;
  - sessions : début et fin de présence (une pause de plus de SESSION_GAP sépare deux sessions) ;
  - temps par appli et par catégorie, d'après jeux.json (nom de processus -> nom affiché + catégorie) :
      jeu      : tant que le jeu tourne (jeux.json, ou jeu reconnu par le mode jeu) ;
      musique / video : seulement quand Windows indique qu'une lecture est en cours (panneau multimédia),
                 sinon tant que l'appli est au premier plan ;
      navigation / travail / autre : quand l'appli est au premier plan et que tu es actif ;
      option « mode »: « ouverte » (ex. Claude) : tant que l'appli est ouverte et que tu es actif ;
  - charge CPU et GPU (moyenne et pic, par heure).
Ce qui est enregistré : des NOMS DE PROCESSUS et des DURÉES. Jamais de titre de fenêtre, d'historique de
navigation, de frappe clavier ni de contenu d'écran.
Une erreur dans une mesure ne fait jamais tomber le serveur : elle est ignorée et la mesure suivante repart.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
import threading
import time
from pathlib import Path

import psutil

import db

BASE = Path(__file__).resolve().parent
JEUX_FILE, JEUX_EXAMPLE = BASE / "jeux.json", BASE / "jeux.example.json"
CATEGORIES = ("jeu", "musique", "video", "navigation", "travail", "autre")
# lecteurs et sites de musique (nom donné par media.py) : comptés en « musique » même sans entrée dans jeux.json
MUSIC_SERVICES = {"Spotify", "Deezer", "Apple Music", "iTunes", "Tidal", "Amazon Music", "Qobuz", "YouTube Music",
                  "SoundCloud", "Pandora", "Napster", "foobar2000", "MusicBee", "AIMP", "Winamp", "MediaMonkey",
                  "Strawberry", "Dopamine", "Bandcamp"}
CAT_LABELS = {"jeu": "Jeux", "musique": "Musique", "video": "Vidéo", "navigation": "Navigation",
              "travail": "Travail", "autre": "Autre"}
TICK = 10.0                    # secondes entre deux mesures
IDLE_AFTER = 120               # inactif après 2 min sans clavier ni souris
SESSION_GAP = 15 * 60          # une absence de plus de 15 min (ou PC éteint) commence une nouvelle session
DEFAULT_RETENTION = 365        # jours conservés par défaut


# --------------------------------------------------------------------------- #
#  Capteurs Windows (sans titre de fenêtre)
# --------------------------------------------------------------------------- #
def idle_seconds() -> float:
    """Secondes depuis le dernier évènement clavier ou souris (Windows)."""
    if sys.platform != "win32":
        return 0.0
    import ctypes
    from ctypes import wintypes

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]
    li = LASTINPUTINFO(); li.cbSize = ctypes.sizeof(li)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
        return 0.0
    tick = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
    return ((tick - li.dwTime) & 0xFFFFFFFF) / 1000.0


def foreground_process() -> str | None:
    """Nom du processus de la fenêtre au premier plan (seulement le nom : jamais le titre)."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        return psutil.Process(pid.value).name().lower()
    except (psutil.Error, OSError):
        return None


# --------------------------------------------------------------------------- #
#  Service
# --------------------------------------------------------------------------- #
class Tracker:
    def __init__(self, game_state=None, media_state=None, gpu_load=None) -> None:
        self.game_state = game_state or (lambda: {})      # mode jeu (gamemode.py) : jeu reconnu
        self.media_state = media_state or (lambda: {})    # panneau multimédia Windows (media.py)
        self.gpu_load = gpu_load or (lambda: None)        # charge GPU en % (stats.py)
        self.status = {"etat": "arrete", "erreur": None, "derniere_mesure": None}
        self._map, self._map_mtime, self._map_checked = {}, None, 0.0
        self._last_tick = None
        self._session_id = None
        self._lock = threading.Lock()
        psutil.cpu_percent()                              # amorce (mesure globale, indépendante des autres)

    # -- jeux.json -------------------------------------------------------------
    def mapping(self) -> dict[str, dict]:
        now = time.time()
        if now - self._map_checked < 60 and self._map:
            return self._map
        self._map_checked = now
        if not JEUX_FILE.exists() and JEUX_EXAMPLE.exists():
            shutil.copyfile(JEUX_EXAMPLE, JEUX_FILE)
        try:
            mtime = JEUX_FILE.stat().st_mtime
            if mtime != self._map_mtime:
                raw = json.loads(JEUX_FILE.read_text(encoding="utf-8-sig")).get("processus") or {}
                self._map = {str(k).lower(): {"nom": str(v.get("nom") or k)[:60],
                                              "categorie": v.get("categorie") if v.get("categorie") in CATEGORIES else "autre",
                                              "ouverte": v.get("mode") == "ouverte"}
                             for k, v in raw.items() if isinstance(v, dict)}
                self._map_mtime = mtime
                self.status["erreur_jeux"] = None
        except (OSError, ValueError, AttributeError) as exc:
            self.status["erreur_jeux"] = f"jeux.json illisible : {exc}"
        return self._map

    # -- une mesure ----------------------------------------------------------------
    def sample(self) -> dict:
        """Ce qui se passe maintenant (sans rien enregistrer) : utile aussi pour les tests."""
        mp = self.mapping()
        running = set()
        for p in psutil.process_iter(["name"]):
            n = (p.info.get("name") or "").lower()
            if n:
                running.add(n)
        fg = foreground_process()
        idle = idle_seconds()
        apps: dict[tuple[str, str], bool] = {}          # (nom, catégorie) -> compté
        # jeux : tant qu'ils tournent
        for proc in running:
            m = mp.get(proc)
            if m and m["categorie"] == "jeu":
                apps[(m["nom"], "jeu")] = True
        g = (self.game_state() or {}).get("game")
        # jeu reconnu par le mode jeu, absent de jeux.json : compté sous son nom de processus — SAUF si un jeu de
        # jeux.json tourne déjà (ex. Valorant : le mode jeu voit « VALORANT.exe », jeux.json compte
        # « valorant-win64-shipping.exe » : c'est le même jeu, il ne doit pas être compté deux fois)
        if g and not mp.get(g.lower()) and not any(c == "jeu" for (_, c) in apps):
            apps[(g.rsplit(".", 1)[0], "jeu")] = True
        fg_is_game = bool(fg and ((mp.get(fg) or {}).get("categorie") == "jeu" or (g and fg == g.lower())))
        active = idle < IDLE_AFTER or fg_is_game
        # musique / vidéo : lecture en cours d'après Windows
        playing = [s for s in (self.media_state() or {}).get("sessions", []) if s.get("status") == "playing"]
        for s in playing:
            # identifiant Windows de l'appli : « Spotify.exe », « chrome », « Microsoft.ZuneMusic_…!App »…
            src = str(s.get("source") or "").lower()
            exe = src if src.endswith(".exe") else src.split("!")[0] + ".exe"
            m = mp.get(exe)
            name = (m or {}).get("nom") or str(s.get("app") or "Lecteur")[:60]
            site = s.get("site")                       # site de musique deviné dans un navigateur (media.py)
            if not m and site in MUSIC_SERVICES:
                apps[(site, "musique")] = True
            elif (m or {}).get("categorie") == "musique" or (not m and ("music" in src or s.get("app") in MUSIC_SERVICES)):
                apps[(name, "musique")] = True
            else:                                       # navigateur (YouTube…), lecteur vidéo, autre
                apps[(name, "video")] = True
        # « mode ouverte » (ex. Claude en travail) : tant que l'appli tourne ET que tu es actif
        if active:
            for proc in running:
                m = mp.get(proc)
                if m and m.get("ouverte") and m["categorie"] != "jeu":
                    apps[(m["nom"], m["categorie"])] = True
        # autres catégories : appli au premier plan, si tu es actif
        m = mp.get(fg or "")
        if m and active and m["categorie"] not in ("jeu",):
            if not (m["categorie"] in ("musique", "video") and any(k[1] == m["categorie"] for k in apps)):
                apps[(m["nom"], m["categorie"])] = True
        return {"actif": active, "inactif_depuis": idle, "premier_plan_jeu": fg_is_game,
                "applis": [{"nom": n, "categorie": c} for (n, c) in apps]}

    def tick(self, now: float | None = None, sample: dict | None = None) -> None:
        if db.get_setting("stats_pause", False):
            self.status.update(etat="pause")
            self._last_tick = None
            return
        now = now or time.time()
        s = sample or self.sample()
        dur = TICK if self._last_tick is None else min(max(0.0, now - self._last_tick), TICK * 3)
        gap = None if self._last_tick is None else now - self._last_tick
        self._last_tick = now
        t = dt.datetime.fromtimestamp(now)
        day, hour = t.date().isoformat(), t.hour
        cpu = psutil.cpu_percent()
        gpu = self.gpu_load()
        c = db.conn()
        with self._lock:
            c.execute("BEGIN")
            try:
                c.execute("INSERT INTO activite_heure(jour, heure) VALUES(?, ?) ON CONFLICT DO NOTHING", (day, hour))
                c.execute("""UPDATE activite_heure SET actif_s = actif_s + ?, inactif_s = inactif_s + ?,
                             cpu_somme = cpu_somme + ?, cpu_max = MAX(cpu_max, ?), cpu_n = cpu_n + 1,
                             gpu_somme = gpu_somme + ?, gpu_max = MAX(gpu_max, ?), gpu_n = gpu_n + ?
                             WHERE jour = ? AND heure = ?""",
                          (dur if s["actif"] else 0, 0 if s["actif"] else dur, cpu, cpu,
                           gpu or 0, gpu or 0, 1 if gpu is not None else 0, day, hour))
                for a in s["applis"]:
                    c.execute("""INSERT INTO temps_appli(jour, nom, categorie, secondes) VALUES(?,?,?,?)
                                 ON CONFLICT(jour, nom, categorie) DO UPDATE SET secondes = secondes + excluded.secondes""",
                              (day, a["nom"], a["categorie"], dur))
                # sessions : présence continue (actif), coupée par une longue absence ou un arrêt du PC
                if s["actif"]:
                    row = c.execute("SELECT id, fin FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
                    if row and now - row["fin"] <= SESSION_GAP and (gap is None or gap <= SESSION_GAP):
                        c.execute("UPDATE sessions SET fin = ?, actif_s = actif_s + ? WHERE id = ?", (now, dur, row["id"]))
                    else:
                        c.execute("INSERT INTO sessions(debut, fin, actif_s) VALUES(?, ?, 0)", (now, now))
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise
        self.status.update(etat="actif", erreur=None, derniere_mesure=now)

    def prune(self) -> None:
        days = int(db.get_setting("stats_conservation_jours", DEFAULT_RETENTION) or DEFAULT_RETENTION)
        limit = (dt.date.today() - dt.timedelta(days=days)).isoformat()
        c = db.conn()
        c.execute("DELETE FROM activite_heure WHERE jour < ?", (limit,))
        c.execute("DELETE FROM temps_appli WHERE jour < ?", (limit,))
        c.execute("DELETE FROM sessions WHERE fin < ?", (time.time() - days * 86400,))

    def start(self) -> None:
        def loop():
            last_prune = 0.0
            while True:
                try:
                    self.tick()
                    if time.time() - last_prune > 6 * 3600:
                        self.prune(); last_prune = time.time()
                except Exception as exc:            # jamais d'arrêt du serveur
                    self.status.update(etat="erreur", erreur=f"{type(exc).__name__}: {exc}")
                time.sleep(TICK)
        self.status["etat"] = "actif"
        threading.Thread(target=loop, daemon=True, name="statistiques").start()


# --------------------------------------------------------------------------- #
#  Lecture pour la page
# --------------------------------------------------------------------------- #
def report(period: str, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    n = {"jour": 1, "7j": 7, "30j": 30}.get(period, 1)
    start = (today - dt.timedelta(days=n - 1)).isoformat()
    end = today.isoformat()
    c = db.conn()
    tot = c.execute("SELECT COALESCE(SUM(actif_s),0) a, COALESCE(SUM(inactif_s),0) i FROM activite_heure WHERE jour BETWEEN ? AND ?",
                    (start, end)).fetchone()
    cats = {r["categorie"]: r["s"] for r in c.execute(
        "SELECT categorie, SUM(secondes) s FROM temps_appli WHERE jour BETWEEN ? AND ? GROUP BY categorie", (start, end))}
    apps = [{"nom": r["nom"], "categorie": r["categorie"], "secondes": r["s"]} for r in c.execute(
        "SELECT nom, categorie, SUM(secondes) s FROM temps_appli WHERE jour BETWEEN ? AND ? GROUP BY nom, categorie "
        "ORDER BY s DESC LIMIT 15", (start, end))]
    per_day = {r["jour"]: {"actif_s": r["a"], "cpu_moy": r["cm"], "cpu_max": r["cx"], "gpu_moy": r["gm"], "gpu_max": r["gx"]}
               for r in c.execute("""SELECT jour, SUM(actif_s) a, SUM(cpu_somme)/MAX(SUM(cpu_n),1) cm, MAX(cpu_max) cx,
                                     CASE WHEN SUM(gpu_n) > 0 THEN SUM(gpu_somme)/SUM(gpu_n) END gm, MAX(gpu_max) gx
                                     FROM activite_heure WHERE jour BETWEEN ? AND ? GROUP BY jour""", (start, end))}
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]
    series = [{"jour": d, **per_day.get(d, {"actif_s": 0, "cpu_moy": None, "cpu_max": None, "gpu_moy": None, "gpu_max": None})}
              for d in days]
    hours = []
    if n == 1:
        by_h = {r["heure"]: r for r in c.execute("SELECT * FROM activite_heure WHERE jour = ?", (end,))}
        for h in range(24):
            r = by_h.get(h)
            hours.append({"heure": h, "actif_s": r["actif_s"] if r else 0,
                          "cpu_moy": r["cpu_somme"] / r["cpu_n"] if r and r["cpu_n"] else None, "cpu_max": r["cpu_max"] if r else None,
                          "gpu_moy": r["gpu_somme"] / r["gpu_n"] if r and r["gpu_n"] else None, "gpu_max": r["gpu_max"] if r else None})
    d0 = dt.datetime.combine(today - dt.timedelta(days=n - 1), dt.time()).timestamp()
    sess = [{"debut": r["debut"], "fin": r["fin"], "actif_s": r["actif_s"]}
            for r in c.execute("SELECT * FROM sessions WHERE fin >= ? ORDER BY debut", (d0,))]
    return {"periode": period, "du": start, "au": end, "actif_s": tot["a"], "inactif_s": tot["i"],
            "categories": [{"categorie": k, "nom": CAT_LABELS[k], "secondes": cats.get(k, 0)} for k in CATEGORIES],
            "applis": apps, "jeux": [a for a in apps if a["categorie"] == "jeu"][:10], "jours": series, "heures": hours,
            "sessions": sess[-50:], "pause": bool(db.get_setting("stats_pause", False)),
            "conservation_jours": int(db.get_setting("stats_conservation_jours", DEFAULT_RETENTION) or DEFAULT_RETENTION)}


def day_detail(day: str) -> dict:
    """Détail d'un seul jour (encart « Détail du jour ») : sessions, temps, applis, charge, frise par heure."""
    try:
        d = dt.date.fromisoformat(day)
    except (TypeError, ValueError):
        raise ValueError("date invalide")
    day = d.isoformat()
    c = db.conn()
    by_h = {r["heure"]: r for r in c.execute("SELECT * FROM activite_heure WHERE jour = ?", (day,))}
    hours = [{"heure": h, "actif_s": (by_h[h]["actif_s"] if h in by_h else 0), "inactif_s": (by_h[h]["inactif_s"] if h in by_h else 0),
              "cpu_moy": (by_h[h]["cpu_somme"] / by_h[h]["cpu_n"] if h in by_h and by_h[h]["cpu_n"] else None),
              "gpu_moy": (by_h[h]["gpu_somme"] / by_h[h]["gpu_n"] if h in by_h and by_h[h]["gpu_n"] else None)}
             for h in range(24)]
    rows = list(by_h.values())
    cpu_n = sum(r["cpu_n"] for r in rows); gpu_n = sum(r["gpu_n"] for r in rows)
    apps = [{"nom": r["nom"], "categorie": r["categorie"], "secondes": r["secondes"]} for r in c.execute(
        "SELECT nom, categorie, secondes FROM temps_appli WHERE jour = ? ORDER BY secondes DESC", (day,))]
    cats = {k: 0.0 for k in CATEGORIES}
    for a in apps:
        cats[a["categorie"]] = cats.get(a["categorie"], 0) + a["secondes"]
    t0 = dt.datetime.combine(d, dt.time()).timestamp(); t1 = t0 + 86400
    sess = [{"debut": max(r["debut"], t0), "fin": min(r["fin"], t1), "actif_s": r["actif_s"]}
            for r in c.execute("SELECT * FROM sessions WHERE fin >= ? AND debut < ? ORDER BY debut", (t0, t1))]
    return {"jour": day, "vide": not rows and not apps,
            "actif_s": sum(r["actif_s"] for r in rows), "inactif_s": sum(r["inactif_s"] for r in rows),
            "debut": sess[0]["debut"] if sess else None, "fin": sess[-1]["fin"] if sess else None, "sessions": sess,
            "cpu_moy": sum(r["cpu_somme"] for r in rows) / cpu_n if cpu_n else None,
            "cpu_max": max((r["cpu_max"] for r in rows), default=None),
            "gpu_moy": sum(r["gpu_somme"] for r in rows) / gpu_n if gpu_n else None,
            "gpu_max": max((r["gpu_max"] for r in rows if r["gpu_n"]), default=None),
            "categories": [{"categorie": k, "nom": CAT_LABELS[k], "secondes": cats.get(k, 0)} for k in CATEGORIES],
            "jeux": [a for a in apps if a["categorie"] == "jeu"],
            "medias": [a for a in apps if a["categorie"] in ("musique", "video")],
            "applis": apps[:20], "heures": hours}


def clear_all() -> None:
    c = db.conn()
    for t in ("activite_heure", "temps_appli", "sessions"):
        c.execute(f"DELETE FROM {t}")
    try:
        c.execute("VACUUM")                 # récupère la place sur le disque (sans gravité si la base est occupée)
    except Exception:
        pass
