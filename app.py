"""NEXUS — serveur web (FastAPI).

Écoute sur 127.0.0.1 par défaut (sur le réseau local seulement si l'accès téléphone est activé).
Les capteurs sont dans stats.py, le bot Discord dans bot.py, le stream deck dans deck.py,
la configuration dans config.py (fichier config.json).
"""

from __future__ import annotations

import asyncio
import base64
import datetime as dt
import os
import socket
import threading
import time
from pathlib import Path

import psutil
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

import activite
import agenda as agenda_mod
import audio as audio_mod
import bot as bot_mod
import config
import db as db_mod
import deck as deck_mod
import focus as focus_mod
import gamemode as gamemode_mod
import journal as journal_mod
import lan
import launcher as launcher_mod
import media as media_mod
import profiles as profiles_mod
import reminders as reminders_mod
import remote as remote_mod
import sante as sante_mod
import souvenirs as souvenirs_mod
import stats
import statistiques as statistiques_mod
import store
import maj as maj_mod
import version as version_mod

HOST = "127.0.0.1"
# (NEXUS_PORT : tests uniquement — une copie de test dans un autre dossier, sans gêner le panel en service)
PORT = int(os.environ.get("NEXUS_PORT") or 8000)
# Identifiant de ce démarrage du serveur : une alerte ignorée revient au prochain démarrage (ou mise à jour)
DEMARRAGE = f"{os.getpid()}-{int(dt.datetime.now().timestamp())}"
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


# --------------------------------------------------------------------------- #
#  Application
# --------------------------------------------------------------------------- #
app = FastAPI(title="NEXUS", docs_url=None, redoc_url=None)
game_mode = gamemode_mod.GameMode()
sensors = stats.Sensors()        # (mode jeu : rien n'est mis en pause dans l'onglet PC, processus compris)
mixer = audio_mod.AudioMixer()
media = media_mod.MediaMonitor()
launcher = launcher_mod.Launcher()
pinger = lan.PingMonitor()
scanner = lan.LanScanner(lambda: pinger.gateway, paused=lambda: game_mode.active)
# NEXUS_DECK_DRYRUN=1 : mode simulation pour les tests (aucune action réelle n'est exécutée)
deck = deck_mod.Deck(executor=(lambda b: f"(simulation) {b['type']}") if os.environ.get("NEXUS_DECK_DRYRUN") else deck_mod.execute)
discord_bot = bot_mod.DiscordBot(sensors, deck)     # démarré dans __main__ (voir en bas du fichier)
profile_lib = profiles_mod.ProfileLibrary()
reminder_svc = reminders_mod.ReminderService(notifier=discord_bot.notify)   # démarré dans __main__
# Mises à jour : vérification en tâche de fond (démarrée dans __main__) ; le bot peut seulement PRÉVENIR
updater = maj_mod.Updater(notifier=discord_bot.notify)


def _gpu_load():
    try:
        g = sensors.gpu.read(sensors.lhm.get())
        return g[0]["load_percent"] if g else None
    except Exception:
        return None


# Minuteur Pomodoro / mode focus (le temps de travail compte dans les statistiques)
focus_svc = focus_mod.Focus(journal=activite.noter)
# Statistiques personnelles : réutilise le mode jeu, le panneau multimédia et la lecture GPU (démarré dans __main__)
tracker = statistiques_mod.Tracker(game_state=game_mode.state, media_state=media.state, gpu_load=_gpu_load,
                                   en_focus=focus_svc.en_travail)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---- Accès téléphone : garde réseau --------------------------------------
remote_svc = remote_mod.Remote()
RESTART_CODE = 3            # code de sortie qui demande à lancer.bat de relancer le serveur
# Accessibles sans appairage depuis le réseau : la page d'appairage et ce qu'elle affiche
PUBLIC_REMOTE_PATHS = {"/pair", "/api/pair/claim", "/static/nexus-logo.svg", "/favicon.ico", "/static/favicon.ico",
                       "/static/manifest.webmanifest", "/static/icons/icon-192.png", "/static/icons/icon-512.png"}
_hosts_cache = {"t": 0.0, "hosts": set()}


def allowed_hosts() -> set[str]:
    """Noms acceptés dans l'en-tête Host : le PC lui-même et ses adresses réseau.
    Bloque le « DNS rebinding » (un site piégé qui se ferait passer pour 127.0.0.1)."""
    if time.time() - _hosts_cache["t"] > 60:
        hosts = {"127.0.0.1", "localhost", "::1"}
        for addrs in psutil.net_if_addrs().values():
            for a in addrs:
                if a.family in (socket.AF_INET, socket.AF_INET6):
                    hosts.add(a.address.split("%")[0].lower())
        _hosts_cache.update(t=time.time(), hosts=hosts)
    return _hosts_cache["hosts"]


def _host_name(header: str) -> str:
    h = (header or "").strip().lower()
    if h.startswith("["):                       # [::1]:8000
        return h[1:h.find("]")] if "]" in h else h
    return h.rsplit(":", 1)[0] if h.count(":") == 1 else h


@app.middleware("http")
async def _guard(request: Request, call_next):
    if _host_name(request.headers.get("host", "")) not in allowed_hosts():
        return PlainTextResponse("Hôte non autorisé", status_code=421)
    ip = request.client.host if request.client else ""
    if remote_mod.is_loopback(ip):
        return await call_next(request)          # le PC lui-même : tout est permis
    # --- requête venant du réseau ---
    if not remote_svc.enabled or not remote_mod.is_private(ip):
        activite.noter("appareil", "accès refusé (réseau non autorisé)", "refusé", "", ip, unique_s=600)
        return PlainTextResponse("Accès refusé", status_code=403)
    path = request.url.path
    # (mises à jour, appairage, fermeture de processus : seulement depuis le PC)
    if path.startswith(("/api/remote", "/api/maj", "/api/processus/fermer")):
        return JSONResponse({"error": "réservé au PC"}, status_code=403)
    if path in PUBLIC_REMOTE_PATHS:
        return await call_next(request)
    if not remote_svc.check(request.cookies.get(remote_mod.COOKIE), ip):
        activite.noter("appareil", "appareil non appairé", "refusé", path[:60], ip, unique_s=600)
        if request.method == "GET" and not path.startswith(("/api/", "/static/", "/profils/")):
            return RedirectResponse("/pair", status_code=303)
        return JSONResponse({"error": "appareil non appairé"}, status_code=401)
    return await call_next(request)


@app.middleware("http")
async def _no_stale_pages(request: Request, call_next):
    """La page et ses scripts sont revalidés à chaque chargement : après une mise à jour
    du panel, le navigateur ne garde pas une ancienne version en cache."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
psutil.cpu_percent(percpu=True)   # amorce : le 1er appel renvoie toujours 0


@app.get("/api/stats")
def api_stats() -> JSONResponse:
    payload = {**sensors.full(), "gamemode": game_mode.state(), "demarrage": DEMARRAGE}
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


class BadRequest(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        self.message, self.status = message, status


@app.exception_handler(BadRequest)
async def _bad_request(_: Request, exc: BadRequest) -> JSONResponse:
    return JSONResponse({"error": exc.message}, status_code=exc.status)


async def json_body(request: Request) -> dict:
    """Corps JSON obligatoire : un autre site web ne peut pas envoyer ce type de requête
    vers 127.0.0.1 sans autorisation CORS (que ce serveur ne donne pas)."""
    if not request.headers.get("content-type", "").startswith("application/json"):
        raise BadRequest("JSON attendu", 415)
    try:
        body = await request.json()
    except ValueError:
        raise BadRequest("JSON invalide")
    if not isinstance(body, dict):
        raise BadRequest("objet JSON attendu")
    return body


def text_field(body: dict, key: str, max_len: int, required: bool = True) -> str:
    value = str(body.get(key) or "").strip()[:max_len]
    if required and not value:
        raise BadRequest(f"champ « {key} » manquant")
    return value


@app.post("/api/fan-name")
async def api_fan_name(request: Request) -> JSONResponse:
    body = await json_body(request)
    fan_id = text_field(body, "id", 200)
    label = text_field(body, "label", 40, required=False)
    return JSONResponse({"ok": True, "names": stats.save_fan_name(fan_id, label)})


# ---- Stockage (agenda, horloges) ------------------------------------------
# L'agenda a ses propres routes (/api/agenda…) : le navigateur ne réécrit plus tout le fichier.
# (« clocks » : ancien onglet Horloges, retiré en 3.11 ; data\clocks.json est conservé mais n'est plus utilisé.)
EDITABLE_KEYS = {"speedtests"}


@app.get("/api/store/{key}")
def api_store_get(key: str) -> JSONResponse:
    if key not in EDITABLE_KEYS:
        raise BadRequest("clé inconnue", 404)
    return JSONResponse({"value": store.load(key)}, headers={"Cache-Control": "no-store"})


@app.put("/api/store/{key}")
async def api_store_put(key: str, request: Request) -> JSONResponse:
    if key not in EDITABLE_KEYS:
        raise BadRequest("clé inconnue", 404)
    body = await json_body(request)
    try:
        store.save(key, body.get("value"))
    except ValueError as exc:
        raise BadRequest(str(exc), 413)
    return JSONResponse({"ok": True})


# ---- Agenda (agenda.py) et rappels (reminders.py) --------------------------
def _agenda_error(exc: agenda_mod.AgendaError) -> JSONResponse:
    return JSONResponse({"error": str(exc), "champs": exc.champs}, status_code=400)


def _range_param(value: str | None, default) -> "dt.date":
    try:
        return agenda_mod.parse_date(value) if value else default
    except ValueError:
        raise BadRequest("date invalide")


@app.get("/api/agenda")
def api_agenda(debut: str | None = None, fin: str | None = None) -> JSONResponse:
    today = dt.date.today()
    start = _range_param(debut, today - dt.timedelta(days=7))
    end = _range_param(fin, today + dt.timedelta(days=42))
    if end < start or (end - start).days > 400:
        raise BadRequest("plage de dates invalide (400 jours maximum)")
    db = agenda_mod.load()
    mins, ref, _ = reminders_mod.settings()
    return JSONResponse({"evenements": db["events"], "occurrences": agenda_mod.occurrences(db, start, end),
                         "todos": db["todos"], "notes": db["notes"],
                         "reglages": {"rappels_minutes": mins, "heure_reference": ref},
                         "repetitions": agenda_mod.REPEAT_LABELS}, headers={"Cache-Control": "no-store"})


@app.post("/api/agenda/evenements")
async def api_agenda_create(request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        return JSONResponse({"ok": True, "evenement": agenda_mod.create(body.get("champs") or {})})
    except agenda_mod.AgendaError as exc:
        return _agenda_error(exc)


@app.post("/api/agenda/evenements/{eid}/modifier")
async def api_agenda_update(eid: str, request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        e = agenda_mod.update(eid, body.get("champs") or {}, body.get("occurrence"), body.get("portee") or "all")
    except agenda_mod.AgendaError as exc:
        return _agenda_error(exc)
    return JSONResponse({"ok": True, "evenement": e})


@app.post("/api/agenda/evenements/{eid}/supprimer")
async def api_agenda_delete(eid: str, request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        agenda_mod.delete(eid, body.get("occurrence"), body.get("portee") or "all")
    except agenda_mod.AgendaError as exc:
        return _agenda_error(exc)
    return JSONResponse({"ok": True})


@app.put("/api/agenda/carnet")
async def api_agenda_notebook(request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        agenda_mod.save_notebook(body.get("todos"), body.get("notes"))
    except agenda_mod.AgendaError as exc:
        return _agenda_error(exc)
    except ValueError as exc:
        raise BadRequest(str(exc), 413)
    return JSONResponse({"ok": True})


@app.get("/api/agenda/rappels")
def api_agenda_reminders() -> JSONResponse:
    return JSONResponse({"rappels": reminder_svc.recent()}, headers={"Cache-Control": "no-store"})


# ---- Souvenirs, statistiques personnelles, journal (données privées, jamais en cache) ----------------
# Même garde que tout le panel (_guard) ; le bot Discord n'utilise aucune de ces routes ni de ces modules.
NO_STORE = {"Cache-Control": "no-store, private", "X-Content-Type-Options": "nosniff"}


def _private(data, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status, headers=NO_STORE)


@app.get("/api/souvenirs/jour/{day}")
def api_souv_day(day: str) -> JSONResponse:
    try:
        return _private(souvenirs_mod.wall(day))        # photos, notes et disposition du mur de ce jour
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))


@app.put("/api/souvenirs/disposition/{day}")
async def api_souv_layout(day: str, request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        return _private(souvenirs_mod.save_layout(day, body.get("elements") or {}))
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))


@app.post("/api/souvenirs/disposition/{day}/auto")
async def api_souv_layout_auto(day: str, request: Request) -> JSONResponse:
    await json_body(request)
    try:
        return _private(souvenirs_mod.auto_layout(day))
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))


@app.post("/api/souvenirs/notes")
async def api_souv_note_add(request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        n = souvenirs_mod.add_note(str(body.get("jour") or ""), str(body.get("texte") or ""),
                                   str(body.get("couleur") or "jaune"), body.get("police") or 18, body.get("position"))
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))
    return _private({"ok": True, "note": n})


@app.post("/api/souvenirs/notes/{nid}/modifier")
async def api_souv_note_update(nid: str, request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        return _private({"ok": True, "note": souvenirs_mod.update_note(
            nid, texte=body.get("texte"), couleur=body.get("couleur"), police=body.get("police"), epinglee=body.get("epinglee"),
            encre=body.get("encre"), fonte=body.get("fonte"))})
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))


@app.post("/api/souvenirs/notes/{nid}/supprimer")
async def api_souv_note_delete(nid: str, request: Request) -> JSONResponse:
    await json_body(request)
    try:
        souvenirs_mod.delete_note(nid)
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc), 404)
    return _private({"ok": True})


@app.get("/api/souvenirs/mois/{month}")
def api_souv_month(month: str) -> JSONResponse:
    try:
        return _private({"jours": souvenirs_mod.month_counts(month)})
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))


@app.get("/api/souvenirs/frise")
def api_souv_timeline() -> JSONResponse:
    return _private({"jours": souvenirs_mod.timeline()})


@app.get("/api/souvenirs/ce-jour-la/{day}")
def api_souv_onthisday(day: str) -> JSONResponse:
    try:
        return _private({"photos": souvenirs_mod.on_this_day(day)})
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))


@app.get("/api/souvenirs/aleatoire")
def api_souv_random(avant: str) -> JSONResponse:
    try:
        return _private({"photos": souvenirs_mod.random_old(avant)})
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))


@app.post("/api/souvenirs")
async def api_souv_add(request: Request, jour: str, legende: str = "", exif: int = 0) -> JSONResponse:
    # Corps brut (application/octet-stream) : un autre site ne peut pas l'envoyer sans autorisation CORS
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/octet-stream":
        raise BadRequest("type de contenu attendu : application/octet-stream", 415)
    if int(request.headers.get("content-length") or 0) > souvenirs_mod.MAX_BYTES:
        raise BadRequest(f"photo trop lourde (maximum {souvenirs_mod.MAX_BYTES // 1048576} Mo)", 413)
    data = await request.body()
    try:
        p = await asyncio.get_running_loop().run_in_executor(None, souvenirs_mod.add, data, jour, legende, bool(exif))
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))
    return _private({"ok": True, "photo": p})


@app.get("/api/souvenirs/photo/{pid}")
def api_souv_photo(pid: str, taille: str = "") -> Response:
    found = souvenirs_mod.file_for(pid, taille == "mini")
    if not found:
        raise BadRequest("photo introuvable", 404)
    path, mime = found
    return FileResponse(path, media_type=mime, headers=NO_STORE)


@app.post("/api/souvenirs/{pid}/modifier")
async def api_souv_update(pid: str, request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        return _private({"ok": True, "photo": souvenirs_mod.update(pid, body.get("jour"), body.get("legende"))})
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc))


@app.post("/api/souvenirs/{pid}/supprimer")
async def api_souv_delete(pid: str, request: Request) -> JSONResponse:
    await json_body(request)
    try:
        souvenirs_mod.delete(pid)
    except souvenirs_mod.SouvenirError as exc:
        raise BadRequest(str(exc), 404)
    return _private({"ok": True})


@app.get("/api/statistiques")
def api_perso_stats(periode: str = "jour") -> JSONResponse:
    data = statistiques_mod.report(periode)
    data["service"] = {k: v for k, v in tracker.status.items()}
    return _private(data)


@app.get("/api/statistiques/jour/{day}")
def api_perso_stats_day(day: str) -> JSONResponse:
    try:
        return _private(statistiques_mod.day_detail(day))
    except ValueError as exc:
        raise BadRequest(str(exc))


@app.post("/api/statistiques/reglages")
async def api_perso_stats_settings(request: Request) -> JSONResponse:
    body = await json_body(request)
    if "pause" in body:
        db_mod.set_setting("stats_pause", bool(body["pause"]))
    if "conservation_jours" in body:
        try:
            days = int(body["conservation_jours"])
            if not 7 <= days <= 3650:
                raise ValueError
        except (TypeError, ValueError):
            raise BadRequest("durée de conservation : entre 7 et 3650 jours")
        db_mod.set_setting("stats_conservation_jours", days)
        tracker.prune()
    return _private({"ok": True, "pause": bool(db_mod.get_setting("stats_pause", False)),
                     "conservation_jours": db_mod.get_setting("stats_conservation_jours", statistiques_mod.DEFAULT_RETENTION)})


@app.post("/api/statistiques/effacer")
async def api_perso_stats_clear(request: Request) -> JSONResponse:
    body = await json_body(request)
    if body.get("confirmation") != "EFFACER":
        raise BadRequest("confirmation manquante")
    statistiques_mod.clear_all()
    return _private({"ok": True})


# -- Journal : verrou facultatif par mot de passe (celui du stream deck), même si la session est active --
def _journal_check(request: Request) -> None:
    if not journal_mod.unlocked(request.cookies.get(journal_mod.COOKIE)):
        raise BadRequest("Journal verrouillé : mot de passe demandé", 401)


def _verify_panel_password(password: str) -> bool:
    cfg = config.get("deck")
    return deck_mod.Deck.password_set(cfg) and deck_mod.verify_password(cfg, str(password or ""))


@app.get("/api/journal/etat")
def api_journal_state(request: Request) -> JSONResponse:
    return _private({"verrou_actif": journal_mod.lock_enabled(),
                     "deverrouille": journal_mod.unlocked(request.cookies.get(journal_mod.COOKIE)),
                     "mot_de_passe_defini": deck_mod.Deck.password_set(config.get("deck")),
                     "humeurs": [{"emoji": e, "nom": n} for e, n in journal_mod.MOODS],
                     "activites": journal_mod.activities()})


@app.post("/api/journal/deverrouiller")
async def api_journal_unlock(request: Request) -> JSONResponse:
    body = await json_body(request)
    if not deck.rate_ok(_ip(request), "journal", 10):
        raise BadRequest("trop d'essais : patiente une minute", 429)
    token = journal_mod.unlock(str(body.get("mot_de_passe") or ""), _verify_panel_password)
    if not token:
        raise BadRequest("mot de passe incorrect", 403)
    r = _private({"ok": True})
    r.set_cookie(journal_mod.COOKIE, token, httponly=True, samesite="strict", path="/api/journal")
    return r


@app.post("/api/journal/reverrouiller")
async def api_journal_relock(request: Request) -> JSONResponse:
    await json_body(request)
    journal_mod.relock()
    return _private({"ok": True})


@app.post("/api/journal/verrou")
async def api_journal_lock(request: Request) -> JSONResponse:
    body = await json_body(request)
    if not deck.rate_ok(_ip(request), "journal", 10):
        raise BadRequest("trop d'essais : patiente une minute", 429)
    if not deck_mod.Deck.password_set(config.get("deck")):
        raise BadRequest("aucun mot de passe défini : lance configurer.bat")
    if not _verify_panel_password(body.get("mot_de_passe")):
        raise BadRequest("mot de passe incorrect", 403)
    db_mod.set_setting("journal_verrou", bool(body.get("actif")))
    journal_mod.relock()
    return _private({"ok": True, "verrou_actif": journal_mod.lock_enabled()})


@app.get("/api/journal/jour/{day}")
def api_journal_get(day: str, request: Request) -> JSONResponse:
    _journal_check(request)
    try:
        return _private(journal_mod.get(day))
    except journal_mod.JournalError as exc:
        raise BadRequest(str(exc))


@app.put("/api/journal/jour/{day}")
async def api_journal_put(day: str, request: Request) -> JSONResponse:
    _journal_check(request)
    body = await json_body(request)
    try:
        return _private(journal_mod.save(day, str(body.get("humeur") or ""), body.get("activites") or [],
                                         str(body.get("texte") or "")))
    except journal_mod.JournalError as exc:
        raise BadRequest(str(exc))


@app.get("/api/journal/mois/{month}")
def api_journal_month(month: str, request: Request) -> JSONResponse:
    _journal_check(request)
    try:
        return _private({"jours": journal_mod.month(month)})
    except journal_mod.JournalError as exc:
        raise BadRequest(str(exc))


@app.get("/api/journal/recherche")
def api_journal_search(q: str, request: Request) -> JSONResponse:
    _journal_check(request)
    return _private({"resultats": journal_mod.search(q)})


@app.get("/api/journal/export")
def api_journal_export(request: Request, format: str = "md") -> Response:
    _journal_check(request)
    name, text = journal_mod.export("md" if format == "md" else "txt")
    return Response(text.encode("utf-8"), media_type="text/markdown; charset=utf-8" if name.endswith(".md") else "text/plain; charset=utf-8",
                    headers={**NO_STORE, "Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/perso/resume")
def api_perso_summary(request: Request) -> JSONResponse:
    """Aperçus du sommaire (sans contenu : nombre de photos, temps actif, humeur si le Journal est ouvert)."""
    today = dt.date.today().isoformat()
    rep = statistiques_mod.report("jour")
    top = rep["jeux"][0] if rep["jeux"] else None
    j = journal_mod.summary(today) if journal_mod.unlocked(request.cookies.get(journal_mod.COOKIE)) else {"verrouille": True}
    return _private({"souvenirs": souvenirs_mod.summary(today), "journal": j,
                     "stats": {"actif_s": rep["actif_s"], "pause": rep["pause"], "jeu": top}})


# ---- Média ----------------------------------------------------------------
@app.get("/api/media")
def api_media(sig: str = "", attendre: float = 0) -> JSONResponse:
    # attendre > 0 : répond dès que l'état visible diffère de « sig » (ou au bout de « attendre » secondes).
    # (fonction synchrone : l'attente se fait dans un fil du serveur, jamais dans sa boucle principale)
    state = media.wait(sig, attendre) if attendre > 0 else media.state()
    return JSONResponse(state, headers={"Cache-Control": "no-store"})


@app.get("/api/media/cover")
def api_media_cover(source: str) -> Response:
    data = media.cover(source)
    if not data:
        return Response(status_code=404)
    mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
    return Response(data, media_type=mime, headers={"Cache-Control": "max-age=3600"})


@app.post("/api/media/control")
async def api_media_control(request: Request) -> JSONResponse:
    body = await json_body(request)
    action = text_field(body, "action", 10)
    if action not in ("toggle", "next", "prev", "seek"):
        raise BadRequest("action inconnue")
    pos = body.get("position")
    # dans un fil à part : la commande attend l'application (jusqu'à 2,5 s) sans bloquer le reste du panel
    ok = await run_in_threadpool(media.control, text_field(body, "source", 300), action,
                                 float(pos) if isinstance(pos, (int, float)) else None)
    return JSONResponse({"ok": ok})


# ---- Son : volume général et mélangeur par application -------------------
@app.get("/api/audio")
def api_audio() -> JSONResponse:
    return JSONResponse(mixer.state(), headers={"Cache-Control": "no-store"})


@app.get("/api/audio/niveaux")
def api_audio_levels() -> JSONResponse:
    """Niveaux sonores seuls, tous regroupés dans une réponse légère (≈ 0,2 ms de lecture) : le mélangeur
    les demande ~10 fois par seconde pour des jauges fluides ; l'état complet reste à 1 fois par seconde."""
    return JSONResponse(mixer.levels(), headers={"Cache-Control": "no-store"})


@app.post("/api/audio")
async def api_audio_set(request: Request) -> JSONResponse:
    body = await json_body(request)
    target = text_field(body, "target", 200)
    vol, muted = body.get("volume"), body.get("muted")
    seq, client = body.get("seq"), body.get("client")
    if vol is not None and (isinstance(vol, bool) or not isinstance(vol, (int, float))):
        raise BadRequest("volume : nombre entre 0 et 1 attendu")
    if muted is not None and not isinstance(muted, bool):
        raise BadRequest("muted : vrai/faux attendu")
    if seq is not None and (isinstance(seq, bool) or not isinstance(seq, int) or seq < 0):
        raise BadRequest("seq : entier positif attendu")
    if client is not None and (not isinstance(client, str) or len(client) > 40):
        raise BadRequest("client : texte court attendu")
    try:
        # dans un thread : le réglage (COM, ≈ 20 ms, jusqu'à 3 s) ne bloque plus tout le serveur
        ok = await run_in_threadpool(mixer.set, target, vol, muted, seq, client)
    except Exception as exc:
        raise BadRequest(f"réglage impossible : {exc}", 500)
    return JSONResponse({"ok": ok})


@app.get("/api/audio/icon/{key}")
def api_audio_icon(key: str) -> Response:
    exe = mixer.exe_paths.get(key.lower())
    path = launcher_mod.exe_icon(exe) if exe else None
    if not path:
        return Response(status_code=404)
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "max-age=86400"})


# ---- Lanceur --------------------------------------------------------------
@app.get("/api/launcher")
def api_launcher() -> JSONResponse:
    return JSONResponse(launcher.items(), headers={"Cache-Control": "no-store"})


@app.get("/api/launcher/cover/{appid}")
def api_launcher_cover(appid: str) -> Response:
    path = launcher_mod.steam_cover(appid)
    if not path:
        return Response(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "max-age=86400"})


@app.get("/api/launcher/icon/{item_id}")
def api_launcher_icon(item_id: str) -> Response:
    path = launcher.icon(item_id)
    if not path:
        return Response(status_code=404)
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "max-age=86400"})


@app.post("/api/launcher/launch")
async def api_launcher_launch(request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        ok = launcher.launch(text_field(body, "id", 200))
    except OSError as exc:
        raise BadRequest(f"lancement impossible : {exc}", 500)
    return JSONResponse({"ok": ok})


@app.post("/api/launcher/app")
async def api_launcher_add(request: Request) -> JSONResponse:
    body = await json_body(request)
    name = text_field(body, "name", 40)
    target = text_field(body, "target", 500).strip('"')
    args = [str(a)[:200] for a in body.get("args") or []][:10]
    if "://" not in target and not target.lower().startswith("shell:") and not Path(target).exists():
        raise BadRequest("fichier introuvable : vérifiez le chemin")
    cfg = launcher.config()
    cfg["apps"].append({"id": launcher.new_app_id(name), "name": name, "target": target, "args": args})
    store.save("launcher", cfg)
    return JSONResponse({"ok": True})


@app.post("/api/launcher/remove")
async def api_launcher_remove(request: Request) -> JSONResponse:
    body = await json_body(request)
    item_id = text_field(body, "id", 200)
    cfg = launcher.config()
    cfg["apps"] = [a for a in cfg["apps"] if a["id"] != item_id]
    store.save("launcher", cfg)
    return JSONResponse({"ok": True})


@app.post("/api/launcher/hide")
async def api_launcher_hide(request: Request) -> JSONResponse:
    body = await json_body(request)
    item_id = text_field(body, "id", 200)
    cfg = launcher.config()
    hidden = set(cfg["hidden"])
    (hidden.add if body.get("hidden") else hidden.discard)(item_id)
    cfg["hidden"] = sorted(hidden)
    store.save("launcher", cfg)
    return JSONResponse({"ok": True})


# ---- Accès téléphone ------------------------------------------------------
def lan_url() -> str | None:
    local = lan._local_network()
    return f"http://{local[0]}:{PORT}" if local else None


def schedule_restart() -> None:
    """Le serveur s'arrête avec RESTART_CODE ; lancer.bat le relance aussitôt (nouvelle écoute réseau)."""
    threading.Timer(1.2, lambda: os._exit(RESTART_CODE)).start()


@app.get("/pair")
def pair_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "pair.html", headers={"Cache-Control": "no-store"})


@app.post("/api/pair/claim")
async def api_pair_claim(request: Request) -> JSONResponse:
    body = await json_body(request)
    ip = request.client.host if request.client else ""
    token = remote_svc.claim(ip, str(body.get("secret") or "")[:100] or None, str(body.get("code") or "")[:10] or None,
                             text_field(body, "name", 40, required=False), request.headers.get("user-agent", ""))
    if not token:
        activite.noter("appareil", "appairage refusé", "refusé", "code invalide ou expiré", ip, unique_s=30)
        raise BadRequest("code invalide ou expiré : relance l'appairage sur le PC", 403)
    activite.noter("appareil", "nouvel appareil appairé", "ok",
                   text_field(body, "name", 40, required=False) or remote_mod.device_label(request.headers.get("user-agent", "")), ip)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(remote_mod.COOKIE, token, max_age=remote_mod.COOKIE_MAX_AGE, httponly=True, samesite="strict", path="/")
    return resp


@app.get("/api/remote")
def api_remote() -> JSONResponse:
    p = remote_svc.pairing()
    return JSONResponse({**remote_svc.state(), "url": lan_url(), "port": PORT,
                         "pairing": {"code": p["code"], "expires": p["expires"]} if p else None},
                        headers={"Cache-Control": "no-store"})


@app.post("/api/remote/config")
async def api_remote_config(request: Request) -> JSONResponse:
    body = await json_body(request)
    restart = remote_svc.set_enabled(bool(body.get("enabled")))
    activite.noter("appareil", "accès téléphone " + ("activé" if body.get("enabled") else "désactivé"), "ok", "", _ip(request))
    if restart:
        schedule_restart()
    return JSONResponse({"ok": True, "restart": restart})


@app.post("/api/remote/pair")
async def api_remote_pair(request: Request) -> JSONResponse:
    await json_body(request)
    if not remote_svc.active:
        raise BadRequest("active d'abord l'accès téléphone", 409)
    p = remote_svc.start_pairing()
    activite.noter("appareil", "appairage lancé (code affiché)", "ok", "", _ip(request))
    return JSONResponse({"code": p["code"], "expires": p["expires"], "url": lan_url()})


@app.post("/api/remote/pair/cancel")
async def api_remote_pair_cancel(request: Request) -> JSONResponse:
    await json_body(request)
    remote_svc.cancel_pairing()
    return JSONResponse({"ok": True})


@app.get("/api/remote/qr.svg")
def api_remote_qr() -> Response:
    p, url = remote_svc.pairing(), lan_url()
    if not p or not url:
        return Response(status_code=404)
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(f"{url}/pair#{p['secret']}", image_factory=qrcode.image.svg.SvgPathImage, border=2)
    return Response(img.to_string(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


@app.post("/api/remote/revoke")
async def api_remote_revoke(request: Request) -> JSONResponse:
    body = await json_body(request)
    did = text_field(body, "id", 40)
    nom = next((d.get("name") for d in remote_svc.state()["devices"] if d.get("id") == did), did)
    ok = remote_svc.revoke(did)
    activite.noter("appareil", "appareil retiré", "ok" if ok else "erreur", str(nom), _ip(request))
    return JSONResponse({"ok": ok})


@app.post("/api/remote/rename")
async def api_remote_rename(request: Request) -> JSONResponse:
    body = await json_body(request)
    return JSONResponse({"ok": remote_svc.rename(text_field(body, "id", 40), text_field(body, "name", 40))})


# ---- Stream deck ----------------------------------------------------------
# Toutes les routes exigent une session (mot de passe de config.json) et sont limitées en débit.
def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def deck_guard(request: Request) -> None:
    cfg = config.get("deck")
    if not deck.rate_ok(_ip(request), "deck", int(cfg.get("rate_limit_per_minute") or 30)):
        raise BadRequest("trop de requêtes : réessaie dans une minute", 429)
    if not deck.check_session(request.cookies.get(deck_mod.SESSION_COOKIE)):
        raise BadRequest("mot de passe du deck requis", 401)


@app.post("/api/deck/login")
async def api_deck_login(request: Request) -> JSONResponse:
    body = await json_body(request)
    cfg = config.get("deck")
    if not deck.rate_ok(_ip(request), "login", 5):
        raise BadRequest("trop d'essais : réessaie dans une minute", 429)
    if not deck.password_set(cfg):
        raise BadRequest("aucun mot de passe défini : lance configurer.bat sur le PC", 503)
    token = deck.login(cfg, str(body.get("password") or ""))
    if not token:
        deck._log("web", _ip(request), "-", "connexion", "refusé", "mauvais mot de passe")
        raise BadRequest("mot de passe incorrect", 403)
    deck._log("web", _ip(request), "-", "connexion", "ok", "nouvelle session du deck")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(deck_mod.SESSION_COOKIE, token, max_age=deck_mod.SESSION_DAYS * 86400,
                    httponly=True, samesite="strict", path="/")
    return resp


@app.post("/api/deck/logout")
async def api_deck_logout(request: Request) -> JSONResponse:
    await json_body(request)
    deck.logout(request.cookies.get(deck_mod.SESSION_COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(deck_mod.SESSION_COOKIE, path="/")
    return resp


@app.get("/api/deck")
def api_deck(request: Request) -> JSONResponse:
    if not deck.check_session(request.cookies.get(deck_mod.SESSION_COOKIE)):
        return JSONResponse({"logged_in": False, "password_set": deck.password_set(config.get("deck"))},
                            headers={"Cache-Control": "no-store"})
    deck_guard(request)
    return JSONResponse({
        "logged_in": True, "buttons": deck.buttons, "warnings": deck.warnings,
        "catalog": {"types": deck_mod.ACTION_TYPES, "media": deck_mod.MEDIA_LABELS, "power": deck_mod.POWER_OPS,
                    "scripts": deck_mod.list_scripts(), "app_exts": deck_mod.APP_EXTS},
        "log": deck.recent_log(12),
        "discord": discord_bot.status,
    }, headers={"Cache-Control": "no-store"})


@app.post("/api/deck/run")
async def api_deck_run(request: Request) -> JSONResponse:
    deck_guard(request)
    body = await json_body(request)
    # Le client n'envoie QUE l'identifiant (et la confirmation) : l'action est lue dans deck.json
    ok, msg = deck.run(text_field(body, "id", 40), source="web", ip=_ip(request), confirmed=body.get("confirmed") is True)
    return JSONResponse({"ok": ok, "message": msg}, status_code=200 if ok else 400)


@app.put("/api/deck")
async def api_deck_save(request: Request) -> JSONResponse:
    deck_guard(request)
    body = await json_body(request)
    try:
        buttons = deck.save(body.get("buttons"))
    except deck_mod.DeckError as exc:
        raise BadRequest(str(exc))
    deck._log("web", _ip(request), "-", "édition", "ok", f"{len(buttons)} boutons enregistrés")
    return JSONResponse({"ok": True, "buttons": buttons})


# ---- Version --------------------------------------------------------------
# ---- Mises à jour (PC uniquement : voir _guard) ---------------------------
def _redemarrer_pour_maj() -> None:
    """Arrêt du serveur pour mettre la mise à jour en place. Avec lancer.bat (NEXUS_LANCEUR=1) : code 3, il relance
    maj_demarrage.py puis app.py. Sans lui (lancement direct) : on relance soi-même maj_demarrage.py --puis-lancer."""
    if os.environ.get("NEXUS_LANCEUR") != "1":
        import subprocess
        import sys
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen([sys.executable, str(BASE_DIR / "maj_demarrage.py"), "--puis-lancer"], cwd=BASE_DIR,
                         creationflags=flags, env={**os.environ, "NEXUS_OPEN_BROWSER": "0"})
        threading.Timer(.4, lambda: os._exit(0)).start()
        return
    threading.Timer(.4, lambda: os._exit(RESTART_CODE)).start()


def _maj_mot_de_passe(request: Request, body: dict, action: str = "mise à jour") -> None:
    if not deck.rate_ok(_ip(request), "maj", 5):
        raise BadRequest("trop d'essais : attends une minute", 429)
    if not deck_mod.Deck.password_set(config.get("deck")):
        raise BadRequest("aucun mot de passe défini pour le panel : lance configurer.bat, puis réessaie", 403)
    if not _verify_panel_password(body.get("mot_de_passe")):
        activite.noter("maj", action, "refusé", "mauvais mot de passe", _ip(request))
        raise BadRequest("mot de passe incorrect", 403)


@app.get("/api/maj")
def api_maj() -> JSONResponse:
    return JSONResponse(updater.public(), headers={"Cache-Control": "no-store"})


@app.post("/api/maj/verifier")
async def api_maj_verifier() -> JSONResponse:
    return JSONResponse(await run_in_threadpool(updater.verifier))


@app.post("/api/maj/plus-tard")
async def api_maj_plus_tard(request: Request) -> JSONResponse:
    body = await json_body(request)
    h = body.get("heures")
    return JSONResponse(updater.plus_tard(float(h) if isinstance(h, (int, float)) and 1 <= h <= 24 * 30 else 24))


@app.post("/api/maj/reglages")
async def api_maj_reglages(request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        avant = maj_mod.reglages()
        apres = maj_mod.modifier_reglages({k: body[k] for k in ("depot", "actif", "intervalle_heures", "discord") if k in body})
    except maj_mod.MajError as exc:
        raise BadRequest(str(exc))
    changes = [f"{k} : {avant.get(k)} → {apres.get(k)}" for k in ("depot", "actif", "intervalle_heures", "discord")
               if avant.get(k) != apres.get(k)]
    if changes:
        activite.noter("maj", "réglages des mises à jour", "ok", " ; ".join(changes), _ip(request))
    return JSONResponse(updater.public())


@app.post("/api/maj/jeton")
async def api_maj_jeton(request: Request) -> JSONResponse:
    body = await json_body(request)
    try:
        ou = maj_mod.enregistrer_jeton(maj_mod.reglages()["depot"], str(body.get("jeton") or ""))
    except maj_mod.MajError as exc:
        raise BadRequest(str(exc))
    activite.noter("maj", "jeton GitHub " + ("enregistré" if ou else "effacé"), "ok", f"rangé : {ou}" if ou else "", _ip(request))
    # (le jeton n'est jamais renvoyé : seulement « enregistré » et où)
    return JSONResponse(await run_in_threadpool(updater.verifier))


@app.post("/api/maj/resultat-vu")
def api_maj_resultat_vu() -> JSONResponse:
    (maj_mod.MAJ_DIR / "resultat.json").unlink(missing_ok=True)
    return JSONResponse({"ok": True})


@app.post("/api/maj/installer")
async def api_maj_installer(request: Request) -> JSONResponse:
    body = await json_body(request)
    dispo = updater.public().get("disponible")
    # validation explicite de CETTE version (étape « Valider la mise à jour » de la fenêtre Version) : obligatoire
    if not dispo or str(body.get("validation") or "") != dispo["version"]:
        raise BadRequest("validation requise : confirme l'installation de cette version dans la fenêtre Version", 400)
    _maj_mot_de_passe(request, body, "installation")
    try:
        updater.installer(_redemarrer_pour_maj)
    except maj_mod.MajError as exc:
        activite.noter("maj", "installation", "erreur", str(exc), _ip(request))
        raise BadRequest(str(exc))
    activite.noter("maj", "installation validée", "ok", f"{version_mod.current()} → {dispo['version']}", _ip(request))
    return JSONResponse({"ok": True, **updater.public()})


@app.post("/api/maj/revenir")
async def api_maj_revenir(request: Request) -> JSONResponse:
    body = await json_body(request)
    sauv = updater.sauvegardes()
    if not sauv or str(body.get("validation") or "") != sauv[0]["version"]:
        raise BadRequest("validation requise : confirme le retour à la version précédente", 400)
    _maj_mot_de_passe(request, body, "retour à la version précédente")
    try:
        v = updater.revenir(_redemarrer_pour_maj)
    except maj_mod.MajError as exc:
        raise BadRequest(str(exc))
    activite.noter("maj", "retour à la version précédente validé", "ok", f"{version_mod.current()} → {v}", _ip(request))
    return JSONResponse({"ok": True, "vers": v})


# ---- Santé de NEXUS, journal d'activité -----------------------------------
def _etat(ok: bool | None, detail: str = "", attention: bool = False) -> dict:
    """ok : True / False / None (inactif ou facultatif) ; attention : marche, mais à surveiller."""
    return {"etat": "inactif" if ok is None else "attention" if (attention and ok) else "ok" if ok else "erreur",
            "detail": detail}


def _duree(s: float) -> str:
    s = max(0, int(s))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min"
    if s < 86400:
        return f"{s // 3600} h {s % 3600 // 60:02d}"
    return f"{s // 86400} j {s % 86400 // 3600} h"


BOT_ETATS = {"online": (True, "connecté"), "connecting": (True, "connexion en cours"), "disabled": (None, "désactivé"),
             "no_token": (None, "aucun jeton (facultatif)"), "stopped": (None, "arrêté"),
             "missing_lib": (False, "bibliothèque discord.py absente"), "bad_token": (False, "jeton refusé par Discord"),
             "bad_config": (False, "configuration incomplète")}


def _sante_elements(now: float) -> list[dict]:
    proc = psutil.Process()
    b = discord_bot.status
    ok_b, txt_b = BOT_ETATS.get(b.get("state"), (False, str(b.get("state") or "?")))
    lhm = sensors.lhm.get()
    tr = tracker.status
    derniere = tr.get("derniere_mesure")
    en_retard = bool(derniere and now - derniere > 3 * statistiques_mod.TICK + 15)
    md = media.state()
    v = updater.etat
    try:
        libre = psutil.disk_usage(str(BASE_DIR)).free
    except OSError:
        libre = None
    src = getattr(sensors.gpu, "last_source", None)
    if tr.get("etat") == "pause":
        stats_e = _etat(None, "en pause (onglet Statistiques)")
    elif tr.get("etat") == "erreur":
        stats_e = _etat(False, f"erreur : {tr.get('erreur')}")
    elif tr.get("etat") == "arrete":
        stats_e = _etat(False, "arrêté (base de données indisponible ?)")
    else:
        stats_e = _etat(not en_retard, (f"dernière mesure il y a {_duree(now - derniere)}" if derniere else "en attente de la 1re mesure")
                        + (" — en retard" if en_retard else ""))
    res = v.get("resultat")
    maj_txt = ("dernière vérification " + time.strftime("%d/%m %H:%M", time.localtime(v["derniere"])) + " : " if v.get("derniere") else "")
    maj_txt += {"ok": "à jour" if v.get("a_jour") else "une nouvelle version est disponible",
                "non_configure": "aucun dépôt configuré"}.get(res) or (v.get("erreur") or "pas encore vérifié")
    db_f = db_mod.DB_FILE
    lhm_pas_encore = lhm.get("error") == "pas encore interrogé"
    return [
        {"id": "serveur", "nom": "Serveur", **_etat(True, f"v{version_mod.current()} · démarré il y a {_duree(now - proc.create_time())} · "
                                                           f"{proc.memory_info().rss / 2**20:.0f} Mo · {proc.num_threads()} fils · port {PORT}")},
        {"id": "bot", "nom": "Bot Discord", **_etat(ok_b, (txt_b if not b.get("detail") or b["detail"].startswith(txt_b)
                                                            else f"{txt_b} — {b['detail']}")[:200])},
        {"id": "lhm", "nom": "LibreHardwareMonitor", **_etat(
            None if lhm_pas_encore else bool(lhm.get("available")),
            "en attente" if lhm_pas_encore else "répond (températures, ventilateurs)" if lhm.get("available")
            else f"ne répond pas ({lhm.get('error') or '?'}) : températures CPU et ventilateurs indisponibles")},
        {"id": "gpu", "nom": "Carte graphique", **_etat(bool(src) or None, f"lue par : {stats.SOURCE_LABELS.get(src, src) if src else 'aucune source'}")},
        {"id": "stats", "nom": "Suivi des statistiques", **stats_e},
        {"id": "media", "nom": "Lecture en cours (Windows)", **_etat(
            bool(md.get("available")) and not md.get("error"),
            f"{len(md.get('sessions') or [])} lecteur(s) détecté(s)" if md.get("available") else f"indisponible : {md.get('error') or '?'}")},
        {"id": "maj", "nom": "Mises à jour", **_etat(None if res in (None, "non_configure") else res == "ok", maj_txt)},
        {"id": "base", "nom": "Base de données", **_etat(
            db_f.exists() or None, f"schéma {db_mod.VERSION} · {db_f.stat().st_size / 2**20:.1f} Mo" if db_f.exists() else "pas encore créée")},
        {"id": "disque", "nom": "Espace disque (dossier de NEXUS)", **_etat(
            libre is not None, f"{libre / 2**30:.1f} Go libres" if libre is not None else "inconnu",
            attention=libre is not None and libre < 5 * 2**30)},
        {"id": "telephone", "nom": "Accès téléphone", **_etat(
            True if remote_svc.active else None,
            f"activé · {len(remote_svc.state()['devices'])} appareil(s) appairé(s)" if remote_svc.active else "désactivé")},
    ]


@app.get("/api/sante")
def api_sante() -> JSONResponse:
    now = time.time()
    elems = _sante_elements(now)
    erreurs = sante_mod.liste()
    recentes = [x for x in erreurs if x["niveau"] == "erreur" and now - x["t"] < 3600]
    resume = ("erreur" if any(e["etat"] == "erreur" for e in elems)
              else "attention" if recentes or any(e["etat"] == "attention" for e in elems) else "ok")
    return JSONResponse({"elements": elems, "erreurs": erreurs, "resume": resume, "maintenant": now},
                        headers={"Cache-Control": "no-store"})


@app.get("/api/activite")
def api_activite(cat: str = "", n: int = 200) -> JSONResponse:
    return JSONResponse({"evenements": activite.lire(max(1, min(1000, n)), cat if cat in activite.CATEGORIES else None),
                         "categories": activite.CATEGORIES}, headers={"Cache-Control": "no-store"})


# ---- Processus : classement complet et fermeture (PC uniquement, avec confirmation) ----
@app.get("/api/processus")
def api_processus(tri: str = "cpu") -> JSONResponse:
    return JSONResponse(sensors.procs.classement(tri), headers={"Cache-Control": "no-store"})


@app.post("/api/processus/fermer")
async def api_processus_fermer(request: Request) -> JSONResponse:
    body = await json_body(request)
    nom = text_field(body, "nom", 120)
    if str(body.get("confirmation") or "") != nom:          # nom confirmé par l'utilisateur dans la page
        raise BadRequest("confirmation manquante")
    try:
        r = await run_in_threadpool(sensors.procs.fermer, nom)
    except ValueError as exc:
        activite.noter("processus", f"fermeture de {nom}", "refusé", str(exc), _ip(request))
        raise BadRequest(str(exc))
    activite.noter("processus", f"fermeture de {nom}", "partiel" if r["refuses"] else "ok",
                   f"{r['fermes']}/{r['trouves']} fermé(s)" + (f", {r['forces']} de force" if r["forces"] else "")
                   + (f", {r['refuses']} refusé(s) par Windows" if r["refuses"] else ""), _ip(request))
    return JSONResponse(r)


# ---- Focus (Pomodoro) --------------------------------------------------------
@app.get("/api/focus")
def api_focus() -> JSONResponse:
    return JSONResponse(focus_svc.etat(), headers={"Cache-Control": "no-store"})


@app.post("/api/focus/{action}")
async def api_focus_action(action: str, request: Request) -> JSONResponse:
    body = await json_body(request)
    actions = {"demarrer": lambda: focus_svc.demarrer(body.get("reglages") or None), "suspendre": focus_svc.suspendre,
               "reprendre": focus_svc.reprendre, "passer": focus_svc.passer, "arreter": focus_svc.arreter,
               "reglages": lambda: focus_svc.regler(body)}
    if action not in actions:
        raise BadRequest("action inconnue", 404)
    return JSONResponse(actions[action]())


@app.get("/api/version")
def api_version() -> JSONResponse:
    return JSONResponse(version_mod.info(), headers={"Cache-Control": "no-store"})


# ---- Mode jeu -------------------------------------------------------------
@app.get("/api/gamemode")
def api_gamemode() -> JSONResponse:
    return JSONResponse(game_mode.details(), headers={"Cache-Control": "no-store"})


@app.post("/api/gamemode/config")
async def api_gamemode_config(request: Request) -> JSONResponse:
    body = await json_body(request)
    return JSONResponse({"ok": True, "config": game_mode.update_config(body)})


# ---- Réseau ---------------------------------------------------------------
@app.get("/api/net")
def api_net() -> JSONResponse:
    return JSONResponse({**pinger.state(), "lan": scanner.state()},
                        headers={"Cache-Control": "no-store"})


@app.post("/api/net/scan")
async def api_net_scan(request: Request) -> JSONResponse:
    await json_body(request)
    scanner.request_scan()
    return JSONResponse({"ok": True})


@app.post("/api/net/device")
async def api_net_device(request: Request) -> JSONResponse:
    body = await json_body(request)
    mac = text_field(body, "mac", 40)
    if body.get("forget"):
        return JSONResponse({"ok": scanner.forget(mac)})
    return JSONResponse({"ok": scanner.rename(mac, text_field(body, "label", 40, required=False))})


# --------------------------------------------------------------------------- #
#  Profils visuels (dossier profils\, voir profiles.py et profils\FORMAT.md)
#  Même garde que tout le panel (middleware _guard) : ce PC, ou un téléphone appairé.
# --------------------------------------------------------------------------- #
MAX_IMPORT_BODY = 9 * 1024 * 1024       # 5 Mo de profil, encodés en base64 dans du JSON


@app.get("/api/profils")
def api_profiles() -> JSONResponse:
    return JSONResponse(profile_lib.scan(), headers={"Cache-Control": "no-store"})


def _profile_cache(request: Request, pid: str, etag: str) -> tuple[dict, bool]:
    """Fichiers STATIQUES des profils (jamais une page ni une API) :
    - adresse versionnée (?v= version actuelle du profil) : gardée en cache (privé, 1 an) — une nouvelle
      version du profil change l'adresse ;
    - sinon : revalidée à chaque fois, avec une vraie réponse 304 si rien n'a changé."""
    headers = dict(profiles_mod.SAFE_HEADERS)
    headers["ETag"] = f'"{etag}"'
    if request.query_params.get("v") and request.query_params.get("v") == profile_lib.signature(pid):
        headers["Cache-Control"] = "private, max-age=31536000, immutable"
    inm = request.headers.get("if-none-match", "")
    return headers, f'"{etag}"' in [t.strip() for t in inm.split(",")]


@app.get("/profils/{pid}/style.css")
def profile_css(pid: str, request: Request) -> Response:
    css = profile_lib.css(pid)
    if css is None:
        return PlainTextResponse("/* profil introuvable ou invalide */", status_code=404,
                                 media_type="text/css", headers=profiles_mod.SAFE_HEADERS)
    headers, same = _profile_cache(request, pid, "css-" + (profile_lib.signature(pid) or ""))
    if same:
        return Response(status_code=304, headers=headers)
    return Response(css, media_type="text/css; charset=utf-8", headers=headers)


@app.get("/profils/{pid}/assets/{rel:path}")
def profile_asset(pid: str, rel: str, request: Request) -> Response:
    found = profile_lib.asset(pid, rel)
    if not found:
        return PlainTextResponse("introuvable", status_code=404, headers=profiles_mod.SAFE_HEADERS)
    path, mime = found
    st = path.stat()
    headers, same = _profile_cache(request, pid, f"{st.st_size:x}-{st.st_mtime_ns:x}")
    if same:
        return Response(status_code=304, headers=headers)
    return FileResponse(path, media_type=mime, headers=headers)


@app.get("/api/profils/{pid}/export")
def api_profile_export(pid: str) -> Response:
    try:
        name, data = profile_lib.export_zip(pid)
    except profiles_mod.ProfileError as exc:
        raise BadRequest(str(exc), 404)
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


@app.post("/api/profils/import")
async def api_profile_import(request: Request) -> JSONResponse:
    if int(request.headers.get("content-length") or 0) > MAX_IMPORT_BODY:
        raise BadRequest(f"fichier trop gros (maximum {profiles_mod.MAX_TOTAL // 1048576} Mo)", 413)
    body = await json_body(request)
    on_conflict = body.get("si_existe") if body.get("si_existe") in ("replace", "keep") else None
    try:
        if body.get("zip_base64"):
            try:
                data = base64.b64decode(str(body["zip_base64"]), validate=True)
            except ValueError:
                raise BadRequest("fichier illisible")
            result = profile_lib.import_zip(data, on_conflict)
        elif body.get("fichiers"):
            result = profile_lib.import_files(body["fichiers"], on_conflict)
        else:
            raise BadRequest("aucun fichier reçu")
    except profiles_mod.ProfileError as exc:
        return JSONResponse({"error": str(exc), "details": exc.details}, status_code=400)
    return JSONResponse(result, status_code=409 if result.get("conflict") else 200)


@app.post("/api/profils/{pid}/supprimer")
async def api_profile_delete(pid: str, request: Request) -> JSONResponse:
    await json_body(request)
    try:
        profile_lib.delete(pid)
    except profiles_mod.ProfileError as exc:
        raise BadRequest(str(exc))
    return JSONResponse({"ok": True})


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> RedirectResponse:
    # Les navigateurs demandent /favicon.ico d'eux-mêmes : on renvoie au logo (plus de 404 dans le journal)
    return RedirectResponse("/static/nexus-logo.svg", status_code=301)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def _journaliser_resultat_maj() -> None:
    """Résultat d'une installation / d'un retour (écrit par maj_demarrage.py) : une seule fois dans le journal."""
    import json as _json
    f = maj_mod.MAJ_DIR / "resultat.json"
    try:
        r = _json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if r.get("journalise"):
        return
    activite.noter("maj", "retour effectué" if r.get("type") == "retour" else "installation terminée",
                   "ok" if r.get("ok") else "erreur", str(r.get("message") or ""), "", "panel")
    r["journalise"] = True
    try:
        f.write_text(_json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _test_demarrage(attendue: str) -> int:
    """Lancé par maj_demarrage.py après une mise à jour : migrations, serveur sur un port libre, /api/version doit
    répondre la version attendue. Code 0 = la nouvelle version démarre ; sinon la mise à jour est annulée."""
    import json as _json
    import sys
    import urllib.request
    import uvicorn
    config.migrer()
    config.load(force=True)
    agenda_mod.load()
    db_mod.migrate()
    probe = socket.socket()
    probe.bind((HOST, 0))
    port = probe.getsockname()[1]
    probe.close()
    threading.Thread(target=lambda: uvicorn.run(app, host=HOST, port=port, log_level="error"), daemon=True).start()
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"http://{HOST}:{port}/api/version", timeout=2) as r:
                v = _json.loads(r.read().decode("utf-8"))["version"]
            if attendue and v != attendue:
                print(f"version {v} au lieu de {attendue}", file=sys.stderr)
                return 1
            with urllib.request.urlopen(f"http://{HOST}:{port}/", timeout=2) as r:
                r.read(64)
            print(f"TEST-DEMARRAGE-OK {v}")
            return 0
        except OSError:
            time.sleep(.5)
    print("le serveur de test ne répond pas", file=sys.stderr)
    return 1


if __name__ == "__main__":
    import sys

    import uvicorn

    if "--test-demarrage" in sys.argv:
        i = sys.argv.index("--test-demarrage")
        try:
            os._exit(_test_demarrage(sys.argv[i + 1] if len(sys.argv) > i + 1 else ""))
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            os._exit(1)
    sante_mod.install()                  # dernières erreurs gardées pour la fenêtre « Santé de NEXUS »
    _journaliser_resultat_maj()
    try:
        config.migrer()                  # schéma de config.json (sauvegarde avant chaque migration)
    except Exception as exc:
        print(f"[Config] AVERTISSEMENT : migration impossible ({exc})")
    try:
        saved = version_mod.snapshot()   # sauvegarde du code de cette version (une seule fois)
        if saved:
            print(f"Version {version_mod.current()} sauvegardée dans versions\\{saved.name}")
    except OSError as exc:
        print(f"[avertissement] sauvegarde de version impossible : {exc}")
    # Accès téléphone activé : écoute aussi sur le réseau local (la garde exige un appareil appairé)
    host = "0.0.0.0" if remote_svc.enabled else HOST
    remote_svc.active = remote_svc.enabled
    print(f"NEXUS v{version_mod.current()} : http://{HOST}:{PORT}  (Ctrl+C pour arrêter)")
    if remote_svc.enabled:
        print(f"Accès téléphone ACTIVÉ : {lan_url() or 'réseau local introuvable'}  (appareils appairés uniquement)")
    config.load()
    for w in config.warnings:
        print(f"[Config] AVERTISSEMENT : {w}")
    if not deck.password_set(config.get("deck")):
        print("[Deck] AVERTISSEMENT : aucun mot de passe : stream deck inaccessible (lance configurer.bat)")
    # Port déjà pris (autre programme, ou NEXUS déjà ouvert) : message clair au lieu d'un plantage
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):    # Windows : échoue aussi si le port est pris sur une autre adresse
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        probe.bind((host, PORT))
    except OSError:
        print(f"\n[ERREUR] Le port {PORT} est déjà utilisé sur ce PC.")
        print("  - NEXUS est peut-être déjà ouvert : cherche une autre fenêtre noire NEXUS (barre des tâches).")
        print(f"  - Sinon, un autre programme utilise le port {PORT} : redémarre le PC, ou change PORT en haut de app.py.")
        raise SystemExit(4)
    finally:
        probe.close()

    # Diagnostic matériel en arrière-plan : il ne retarde pas le démarrage du serveur
    threading.Thread(target=lambda: [print(l, flush=True) for l in sensors.hardware_report()], daemon=True).start()

    # Ouvre le navigateur seulement quand le serveur répond vraiment (lancer.bat met NEXUS_OPEN_BROWSER=1)
    def _open_when_ready() -> None:
        import webbrowser
        for _ in range(240):                      # jusqu'à 2 minutes (PC lent, antivirus…)
            try:
                with socket.create_connection((HOST, PORT), timeout=.5):
                    break
            except OSError:
                time.sleep(.5)
        else:
            print("[ERREUR] NEXUS ne répond pas : regarde le message d'erreur au-dessus dans cette fenêtre.")
            return
        print(f"NEXUS est prêt : ouverture de http://{HOST}:{PORT}", flush=True)
        webbrowser.open(f"http://{HOST}:{PORT}")
    if os.environ.get("NEXUS_OPEN_BROWSER") == "1":
        threading.Thread(target=_open_when_ready, daemon=True).start()

    discord_bot.start()     # thread séparé ; un jeton absent ou invalide n'empêche pas NEXUS de démarrer
    try:
        agenda_mod.load()   # migre l'agenda au format 2 si besoin (avec sauvegarde) avant les rappels
    except Exception as exc:
        print(f"[Agenda] AVERTISSEMENT : {exc}")
    reminder_svc.start()
    updater.demarrer()      # vérification des mises à jour : 20 s après le démarrage, puis toutes les N heures
    try:
        db_mod.migrate()    # base locale des souvenirs, statistiques et journal (créée vide sur une installation neuve)
        tracker.start()     # mesures légères toutes les 10 s ; une erreur n'arrête jamais le serveur
    except Exception as exc:
        print(f"[Données perso] AVERTISSEMENT : {exc} — souvenirs, statistiques et journal indisponibles")
    uvicorn.run(app, host=host, port=PORT, log_level="warning")
