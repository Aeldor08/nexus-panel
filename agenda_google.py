r"""Liaison de l'Agenda de NEXUS avec Google Agenda (API Google Calendar v3), dans les deux sens.

Principe
- Les évènements Google restent dans Google Agenda : NEXUS en garde une copie (data\agenda_google.json, relue
  toutes les N minutes et après chaque modification) pour les afficher, envoyer leurs rappels et fonctionner
  hors connexion (en lecture). Créer / modifier / supprimer un évènement Google depuis NEXUS passe par l'API :
  seuls les champs changés sont envoyés (invités, lieu, visioconférence… ne sont jamais effacés).
- Les évènements NEXUS restent dans data\agenda.json ; le formulaire de l'Agenda choisit où créer un évènement.
  Envoi automatique (réglage « envoi_auto », activé par défaut) : à chaque relecture, les évènements NEXUS
  encore locaux (sauf ceux créés avec le choix « NEXUS (sur ce PC seulement) ») sont créés dans Google Agenda
  puis retirés de NEXUS. Jamais de doublon : l'identifiant Google est calculé à partir de celui de NEXUS (un
  second envoi est refusé par Google, « 409 », et devient une simple mise à jour) et chaque envoi est noté
  (data\agenda_google_envois.json) avant que la copie locale soit retirée.
- Répétitions : une série Google « simple » (tous les jours / semaines / mois / ans, avec ou sans date de fin)
  se modifie comme une série NEXUS (cette occurrence, les suivantes, toute la série). Une répétition plus riche
  (« toutes les 2 semaines », « lundi et jeudi »…) est affichée et modifiable, mais sa règle reste celle de Google.

Connexion (OAuth 2.0 « application de bureau », PKCE) : l'utilisateur crée SON projet Google Cloud et un
identifiant client (docs\GOOGLE_AGENDA.md). NEXUS ouvre la page de connexion de Google ; Google renvoie le
navigateur vers un petit serveur temporaire de NEXUS sur 127.0.0.1 (port au hasard, 5 minutes, une seule
réponse, « state » vérifié). Le secret du client et le jeton de rafraîchissement sont rangés dans le gestionnaire
d'identifiants de Windows (identifiants.py ; repli : config.json, exclu de Git). Ils ne sont jamais renvoyés au
navigateur ni écrits dans les journaux, et ne partent que vers Google.

Tests : NEXUS_GOOGLE_AUTH_TEST, NEXUS_GOOGLE_TOKEN_TEST et NEXUS_GOOGLE_API_TEST pointent vers un faux Google
(outils/tests/test_agenda_google.py) ; NEXUS_IDENTIFIANTS=memoire garde les secrets en mémoire.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import html
import http.client
import http.server
import json
import math
import os
import re
import secrets
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import agenda
import config
import identifiants
import paths

AUTH_URL = os.environ.get("NEXUS_GOOGLE_AUTH_TEST", "").strip() or "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = os.environ.get("NEXUS_GOOGLE_TOKEN_TEST", "").strip() or "https://oauth2.googleapis.com/token"
REVOKE_URL = os.environ.get("NEXUS_GOOGLE_REVOKE_TEST", "").strip() or "https://oauth2.googleapis.com/revoke"
API = (os.environ.get("NEXUS_GOOGLE_API_TEST", "").strip() or "https://www.googleapis.com/calendar/v3").rstrip("/")
# Lire et modifier les évènements de tes agendas + voir la liste de tes agendas (pour choisir lequel relier)
SCOPES = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/calendar.readonly"
SECTION = "google_agenda"
SERVICE = identifiants.SERVICE_GOOGLE
CACHE_FILE = paths.DATA_DIR / "agenda_google.json"
ENVOIS_FILE = paths.DATA_DIR / "agenda_google_envois.json"  # trace des évènements NEXUS envoyés dans Google
ENVOI_MAX = 200  # évènements envoyés au plus par relecture (la suite à la relecture suivante)
FENETRE_AVANT, FENETRE_APRES = 62, 400  # jours gardés en copie autour d'aujourd'hui
CONNEXION_SECONDES = 300
MAX_PAGES = 20
PREFIXE = "g:"  # identifiants des évènements Google dans NEXUS
CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,200}\.apps\.googleusercontent\.com$")
SECRET_RE = re.compile(r"^[A-Za-z0-9_-]{10,100}$")
AGENDA_ID_RE = re.compile(r"^[^\s/?#]{1,200}$")
JOURS_RRULE = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
FREQ = {"DAILY": "daily", "WEEKLY": "weekly", "MONTHLY": "monthly", "YEARLY": "yearly"}
REPEAT_CUSTOM = "custom"
REPEAT_CUSTOM_LABEL = "Répétition personnalisée (Google Agenda)"

_lock = threading.RLock()  # état en mémoire et fichier de cache
_sync_lock = threading.Lock()  # une seule relecture à la fois
_acces: dict = {"jeton": "", "expire": 0.0}  # jeton d'accès (1 h), jamais écrit sur le disque
_etat: dict = {"erreur": "", "derniere": 0.0, "connexion": None, "envoi": None}
_plages: dict = {}  # plages hors de la copie, lues à la demande : {(début, fin): (horodatage, occurrences)}
_cache: dict | None = None
_thread: threading.Thread | None = None
_stop = threading.Event()
_reveil = threading.Event()
_serveur_connexion = None


def _journal(texte: str) -> None:
    """Message dans la console / le journal (jamais de secret) ; une console en cp1252 ne fait jamais planter."""
    try:
        print(texte, flush=True)
    except (UnicodeError, OSError, ValueError):
        try:
            print(texte.encode("ascii", "replace").decode("ascii"), flush=True)
        except (OSError, ValueError):
            pass


class GoogleErreur(agenda.AgendaError):
    """Erreur lisible (affichée telle quelle dans le panel)."""


class AccesRetire(GoogleErreur):
    """Jeton de rafraîchissement refusé par Google (expiré ou révoqué) : il faut se reconnecter."""


class DejaExistant(GoogleErreur):
    """Identifiant d'évènement déjà pris chez Google (409) : l'évènement a déjà été envoyé."""


class Refuse(GoogleErreur):
    """Google refuse CET évènement (valeurs invalides) : les autres envois continuent."""


class OccurrenceAbsente(GoogleErreur):
    """L'occurrence demandée n'existe pas (ou plus) dans la série Google."""


# --------------------------------------------------------------------------- #
#  Réglages et secrets
# --------------------------------------------------------------------------- #
def reglages() -> dict:
    r = dict(config.get(SECTION))
    r["client_id"] = str(r.get("client_id") or "").strip()
    if r["client_id"] and not CLIENT_ID_RE.match(r["client_id"]):
        r["client_id"] = ""
    a = str(r.get("agenda") or "primary").strip()
    r["agenda"] = a if AGENDA_ID_RE.match(a) else "primary"
    r["cible"] = "nexus" if r.get("cible") == "nexus" else "google"
    r["rappels"] = bool(r.get("rappels", True))
    try:
        r["intervalle_minutes"] = max(2, min(240, int(float(r.get("intervalle_minutes") or 10))))
    except (TypeError, ValueError):
        r["intervalle_minutes"] = 10
    r["envoi_auto"] = bool(r.get("envoi_auto", True))
    return r


def _secret(cle: str, repli: str) -> tuple[str, str]:
    """(valeur, où elle est rangée : 'windows' | 'config' | '')."""
    v = identifiants.lire(SERVICE, cle)
    if v:
        return v, "windows"
    v = str(config.get(SECTION).get(repli) or "").strip()
    return (v, "config") if v else ("", "")


def _ranger(cle: str, repli: str, valeur: str) -> str:
    if not valeur:
        identifiants.supprimer(SERVICE, cle)
        config.modifier_section(SECTION, {repli: ""}, vides_retires=(repli,))
        return ""
    if identifiants.ecrire(SERVICE, cle, valeur):
        config.modifier_section(SECTION, {repli: ""}, vides_retires=(repli,))  # jamais en double dans config.json
        return "windows"
    config.modifier_section(SECTION, {repli: valeur})  # repli : config.json, exclu de Git
    return "config"


def secret_client() -> str:
    return _secret(identifiants.CLE_SECRET_GOOGLE, "client_secret")[0]


def jeton_rafraichissement() -> str:
    return _secret(identifiants.CLE_JETON_GOOGLE, "jeton")[0]


def configure() -> bool:
    return bool(reglages()["client_id"] and secret_client())


def connecte() -> bool:
    return configure() and bool(jeton_rafraichissement())


def enregistrer_client(client_id: str, client_secret: str) -> dict:
    """Identifiant client OAuth (Google Cloud Console). Un autre client = il faut se reconnecter."""
    client_id = str(client_id or "").strip()
    client_secret = str(client_secret or "").strip()
    if not client_id and not client_secret:
        deconnecter()
        _ranger(identifiants.CLE_SECRET_GOOGLE, "client_secret", "")
        config.modifier_section(SECTION, {"client_id": ""})
        return etat()
    if not CLIENT_ID_RE.match(client_id):
        raise GoogleErreur("Identifiant client invalide : il se termine par .apps.googleusercontent.com (voir docs\\GOOGLE_AGENDA.md).")
    if client_secret and not SECRET_RE.match(client_secret):
        raise GoogleErreur("Code secret du client invalide (il commence en général par GOCSPX-).")
    if not client_secret and not secret_client():
        raise GoogleErreur("Colle aussi le code secret du client (il commence en général par GOCSPX-).")
    if client_id != reglages()["client_id"]:
        deconnecter()  # le jeton appartient à l'ancien client
    config.modifier_section(SECTION, {"client_id": client_id})
    if client_secret:
        _ranger(identifiants.CLE_SECRET_GOOGLE, "client_secret", client_secret)
    return etat()


def modifier_reglages(changes: dict) -> dict:
    ok = {}
    if "agenda" in changes:
        a = str(changes["agenda"] or "").strip() or "primary"
        if not AGENDA_ID_RE.match(a):
            raise GoogleErreur("agenda invalide")
        ok["agenda"] = a
    if "cible" in changes:
        ok["cible"] = "nexus" if changes["cible"] == "nexus" else "google"
    if "rappels" in changes:
        ok["rappels"] = bool(changes["rappels"])
    if "envoi_auto" in changes:
        ok["envoi_auto"] = bool(changes["envoi_auto"])
    if "intervalle_minutes" in changes:
        try:
            ok["intervalle_minutes"] = max(2, min(240, int(float(changes["intervalle_minutes"]))))
        except (TypeError, ValueError):
            raise GoogleErreur("intervalle invalide")
    if ok:
        avant = reglages()["agenda"]
        config.modifier_section(SECTION, ok)
        if ok.get("agenda", avant) != avant:
            _vider_cache()
            reveiller()
        elif ok.get("envoi_auto"):
            reveiller()  # envoi tout de suite (en arrière-plan)
    return etat()


def etat() -> dict:
    """Ce que le panel peut savoir (jamais de secret)."""
    r = reglages()
    c = _lire_cache()
    connexion = _etat.get("connexion")
    return {
        "configure": configure(),
        "connecte": connecte(),
        "client_id": r["client_id"],
        "secret_range": _secret(identifiants.CLE_SECRET_GOOGLE, "client_secret")[1],
        "jeton_range": _secret(identifiants.CLE_JETON_GOOGLE, "jeton")[1],
        "agenda": r["agenda"],
        "agenda_nom": c.get("nom") or "",
        "fuseau": c.get("fuseau") or "",
        "lecture_seule": c.get("acces") not in (None, "owner", "writer"),
        "cible": r["cible"],
        "rappels": r["rappels"],
        "intervalle_minutes": r["intervalle_minutes"],
        "envoi_auto": r["envoi_auto"],
        "envoi": dict(_etat["envoi"]) if _etat.get("envoi") else None,
        **comptes_locaux(),
        "derniere_synchro": c.get("maj") or 0,
        "nb_evenements": len(c.get("occurrences") or []),
        "erreur": _etat.get("erreur") or "",
        "connexion": dict(connexion) if connexion else None,
    }


def comptes_locaux() -> dict:
    """Évènements NEXUS encore à envoyer, et ceux gardés « sur ce PC seulement »."""
    try:
        evs = agenda.load()["events"]
    except Exception:
        evs = []
    seuls = sum(1 for e in evs if e.get("seulement_nexus"))
    return {"a_envoyer": len(evs) - seuls, "seulement_nexus": seuls}


def court() -> dict:
    """Résumé pour la vue Agenda."""
    if not connecte():
        return {"connecte": False}
    c = _lire_cache()
    return {
        "connecte": True,
        "cible": reglages()["cible"],
        "agenda_nom": c.get("nom") or "Google Agenda",
        "lecture_seule": c.get("acces") not in (None, "owner", "writer"),
        "derniere_synchro": c.get("maj") or 0,
        "erreur": _etat.get("erreur") or "",
        "envoi": dict(_etat["envoi"]) if _etat.get("envoi") else None,
    }


# --------------------------------------------------------------------------- #
#  HTTP (uniquement vers Google)
# --------------------------------------------------------------------------- #
_CTX = ssl.create_default_context()


def _ouvrir(req: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(req, timeout=timeout, context=_CTX if req.full_url.startswith("https:") else None)


def _post_formulaire(url: str, champs: dict, timeout: float = 20) -> dict:
    data = urllib.parse.urlencode(champs).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    try:
        with _ouvrir(req, timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            corps = json.loads(e.read().decode("utf-8") or "{}")
        except (ValueError, OSError):
            corps = {}
        code = str(corps.get("error") or "")
        if code == "invalid_grant":
            raise AccesRetire("Google a retiré l'accès de NEXUS (jeton expiré ou révoqué) : reconnecte-toi dans ⚙ Réglages → Google Agenda.")
        if code in ("invalid_client", "unauthorized_client"):
            raise GoogleErreur("Google ne reconnaît pas l'identifiant client ou son code secret : vérifie-les dans ⚙ Réglages → Google Agenda.")
        raise GoogleErreur(f"Google refuse la connexion ({code or e.code}).")
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError):
        raise GoogleErreur("Google injoignable (pas de connexion Internet ?) : réessaie plus tard.")


def _jeton_acces(forcer: bool = False) -> str:
    with _lock:
        if not forcer and _acces["jeton"] and _acces["expire"] > time.time() + 60:
            return _acces["jeton"]
    rt = jeton_rafraichissement()
    if not rt or not configure():
        raise GoogleErreur("Google Agenda n'est pas relié : ⚙ Réglages → Google Agenda.")
    try:
        r = _post_formulaire(
            TOKEN_URL, {"client_id": reglages()["client_id"], "client_secret": secret_client(), "refresh_token": rt, "grant_type": "refresh_token"}
        )
    except GoogleErreur as exc:
        if isinstance(exc, AccesRetire):
            _ranger(identifiants.CLE_JETON_GOOGLE, "jeton", "")  # inutilisable : on le jette (reconnexion)
        _etat["erreur"] = str(exc)
        raise
    tok = str(r.get("access_token") or "")
    if not tok:
        raise GoogleErreur("réponse inattendue de Google (pas de jeton d'accès)")
    with _lock:
        _acces["jeton"], _acces["expire"] = tok, time.time() + float(r.get("expires_in") or 3600)
    return tok


def _erreur_api(code: int, corps: dict) -> GoogleErreur:
    err = corps.get("error") if isinstance(corps.get("error"), dict) else {}
    raisons = {str(x.get("reason") or "") for x in err.get("errors") or [] if isinstance(x, dict)}
    message = str(err.get("message") or "")
    if code == 403 and ("accessNotConfigured" in raisons or "has not been used" in message or "is disabled" in message):
        return GoogleErreur("L'API Google Calendar n'est pas activée dans ton projet Google Cloud (voir docs\\GOOGLE_AGENDA.md, étape 2).")
    if (code == 403 and raisons & {"rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded"}) or code == 429:
        return GoogleErreur("Google Agenda limite les demandes : réessaie dans une minute.")
    if code == 403:
        return GoogleErreur("Google refuse cette modification (agenda en lecture seule ou évènement dont tu n'es pas l'organisateur).")
    if code == 409:
        return DejaExistant("Cet évènement existe déjà dans Google Agenda.")
    if code in (404, 410):
        return GoogleErreur("Évènement introuvable dans Google Agenda (il a peut-être été supprimé ailleurs).")
    if code == 400:
        return Refuse("Google refuse ces valeurs" + (f" : {message[:160]}" if message else "."))
    if code >= 500:
        return GoogleErreur("Google Agenda ne répond pas correctement : réessaie dans un instant.")
    return GoogleErreur(f"erreur de Google Agenda ({code})")


def _appel(methode: str, chemin: str, query: dict | None = None, corps: dict | None = None, timeout: float = 20):
    """Appel de l'API Calendar (chemin relatif : jamais une autre adresse). Renvoie le JSON (ou None)."""
    if not chemin.startswith("/") or "://" in chemin:
        raise GoogleErreur("adresse refusée")
    url = API + chemin + ("?" + urllib.parse.urlencode(query, doseq=True) if query else "")
    data = json.dumps(corps).encode("utf-8") if corps is not None else None
    for essai in range(2):
        tok = _jeton_acces(forcer=essai > 0)
        h = {"Authorization": f"Bearer {tok}", "Accept": "application/json", "User-Agent": "NEXUS-panel"}
        if data is not None:
            h["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(url, data=data, method=methode, headers=h)
        try:
            with _ouvrir(req, timeout) as r:
                brut = r.read().decode("utf-8")
                return json.loads(brut) if brut.strip() else None
        except urllib.error.HTTPError as e:
            try:
                c = json.loads(e.read().decode("utf-8") or "{}")
            except (ValueError, OSError):
                c = {}
            if e.code == 401 and essai == 0:
                continue  # jeton d'accès périmé : on en redemande un
            if e.code == 401:
                raise GoogleErreur("Google refuse l'accès : reconnecte-toi dans ⚙ Réglages → Google Agenda.")
            if e.code == 410 and methode == "DELETE":
                return None  # déjà supprimé
            raise _erreur_api(e.code, c if isinstance(c, dict) else {})
        except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError):
            raise GoogleErreur("Google Agenda injoignable (pas de connexion Internet ?) : réessaie plus tard.")
    raise GoogleErreur("Google refuse l'accès : reconnecte-toi dans ⚙ Réglages → Google Agenda.")


def _q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def _cal() -> str:
    return "/calendars/" + _q(reglages()["agenda"])


# --------------------------------------------------------------------------- #
#  Connexion (OAuth « application de bureau » + PKCE)
# --------------------------------------------------------------------------- #
PAGE_RETOUR = """<!doctype html><html lang="fr"><meta charset="utf-8"><title>NEXUS · Google Agenda</title>
<body style="font-family:Segoe UI,system-ui,sans-serif;background:#0f1115;color:#e8e8ea;display:grid;place-items:center;min-height:90vh">
<div style="max-width:520px;text-align:center"><h1 style="font-size:22px">{titre}</h1><p>{texte}</p></div></body></html>"""


def demarrer_connexion() -> str:
    """Prépare la connexion et renvoie l'adresse de la page de Google à ouvrir dans le navigateur."""
    global _serveur_connexion
    if not configure():
        raise GoogleErreur("Enregistre d'abord l'identifiant client et son code secret (⚙ Réglages → Google Agenda).")
    _arreter_serveur_connexion()
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    fini = threading.Event()

    class Retour(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):  # (l'adresse contient le code : jamais dans les journaux)
            pass

        def _page(self, code: int, titre: str, texte: str) -> None:
            corps = PAGE_RETOUR.format(titre=html.escape(titre), texte=html.escape(texte)).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = dict(urllib.parse.parse_qsl(u.query))
            if u.path != "/" or fini.is_set():
                self._page(404, "Page inconnue", "Cette page n'existe pas.")
                return
            if not secrets.compare_digest(q.get("state", ""), state):
                self._page(400, "Demande inconnue", "Cette réponse ne correspond pas à la connexion lancée depuis NEXUS. Relance-la depuis ⚙ Réglages.")
                return
            fini.set()
            if q.get("error") or not q.get("code"):
                refus = q.get("error") == "access_denied"
                msg = "Connexion refusée sur la page de Google." if refus else f"Google n'a pas donné d'autorisation ({q.get('error') or 'réponse vide'})."
                _etat["connexion"] = {"etat": "erreur", "message": msg}
                self._page(200, "NEXUS n'est pas relié", msg + " Tu peux fermer cet onglet.")
            else:
                try:
                    _terminer_connexion(q["code"], redirect_uri, verifier)
                    self._page(200, "NEXUS est relié à Google Agenda ✔", "Tu peux fermer cet onglet et revenir dans NEXUS.")
                except GoogleErreur as exc:
                    _etat["connexion"] = {"etat": "erreur", "message": str(exc)}
                    self._page(200, "NEXUS n'est pas relié", str(exc))
            threading.Thread(target=srv.shutdown, daemon=True).start()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Retour)
    srv.daemon_threads = True
    redirect_uri = f"http://127.0.0.1:{srv.server_address[1]}/"
    _serveur_connexion = srv

    def servir():
        srv.serve_forever(poll_interval=0.5)
        srv.server_close()

    def minuteur():
        if not fini.wait(CONNEXION_SECONDES):
            fini.set()
            if _serveur_connexion is srv and (_etat.get("connexion") or {}).get("etat") == "attente":
                _etat["connexion"] = {"etat": "erreur", "message": "Délai dépassé (5 minutes) : relance la connexion."}
            srv.shutdown()

    threading.Thread(target=servir, daemon=True, name="google-connexion").start()
    threading.Thread(target=minuteur, daemon=True, name="google-connexion-delai").start()
    query = {
        "client_id": reglages()["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(query)
    _etat["connexion"] = {"etat": "attente", "message": "Connecte-toi dans la page de Google qui vient de s'ouvrir…", "debut": time.time(), "url": url}
    return url


def _arreter_serveur_connexion() -> None:
    global _serveur_connexion
    srv, _serveur_connexion = _serveur_connexion, None
    if srv is not None:
        threading.Thread(target=srv.shutdown, daemon=True).start()


def _terminer_connexion(code: str, redirect_uri: str, verifier: str) -> None:
    r = _post_formulaire(
        TOKEN_URL,
        {
            "client_id": reglages()["client_id"],
            "client_secret": secret_client(),
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    rt, tok = str(r.get("refresh_token") or ""), str(r.get("access_token") or "")
    if not rt or not tok:
        raise GoogleErreur("Google n'a pas donné d'accès durable : relance la connexion.")
    _ranger(identifiants.CLE_JETON_GOOGLE, "jeton", rt)
    with _lock:
        _acces["jeton"], _acces["expire"] = tok, time.time() + float(r.get("expires_in") or 3600)
    _etat["connexion"] = {"etat": "ok", "message": "NEXUS est relié à Google Agenda."}
    _etat["erreur"] = ""
    _vider_cache()
    reveiller()  # première relecture tout de suite (en arrière-plan)


def deconnecter() -> None:
    """Oublie le jeton (et le révoque chez Google, au mieux) et la copie des évènements Google."""
    _arreter_serveur_connexion()
    rt = jeton_rafraichissement()
    if rt:
        try:
            _post_formulaire(REVOKE_URL, {"token": rt}, timeout=8)
        except GoogleErreur:
            pass  # hors connexion : le jeton est oublié quand même
        _ranger(identifiants.CLE_JETON_GOOGLE, "jeton", "")
    with _lock:
        _acces["jeton"], _acces["expire"] = "", 0.0
    _etat.update(erreur="", connexion=None)
    _vider_cache()


# --------------------------------------------------------------------------- #
#  Conversions Google <-> NEXUS
# --------------------------------------------------------------------------- #
def _local(s: str) -> dt.datetime:
    """Date-heure RFC 3339 de Google -> heure locale du PC (sans fuseau)."""
    d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d.astimezone().replace(tzinfo=None) if d.tzinfo else d


def _rfc3339(d: dt.datetime) -> str:
    """Heure locale du PC -> RFC 3339 avec son décalage (été / hiver compris)."""
    return d.astimezone().isoformat(timespec="seconds")


def _jour_local(t: dict) -> dt.date | None:
    if not isinstance(t, dict):
        return None
    if t.get("date"):
        return dt.date.fromisoformat(t["date"])
    if t.get("dateTime"):
        return _local(t["dateTime"]).date()
    return None


def _texte(desc: str) -> str:
    """Description Google (souvent du HTML simple) -> texte."""
    s = str(desc or "")
    if re.search(r"<\s*/?\s*(br|p|div|b|i|u|a|ul|ol|li|span|strong|em)\b", s, re.I):
        s = re.sub(r"<\s*br\s*/?\s*>|<\s*/\s*(p|div|li)\s*>", "\n", s, flags=re.I)
        s = re.sub(r"<[^>]+>", "", s)
        s = html.unescape(s)
    return s.strip()[:2000]


def _until_local(v: str) -> dt.date | None:
    v = v.strip()
    try:
        if "T" in v:
            d = dt.datetime.strptime(v.rstrip("Z"), "%Y%m%dT%H%M%S")
            if v.endswith("Z"):
                d = d.replace(tzinfo=dt.UTC).astimezone().replace(tzinfo=None)
            return d.date()
        return dt.datetime.strptime(v, "%Y%m%d").date()
    except ValueError:
        return None


def _regle(recurrence) -> tuple[dict, list[str]]:
    rr = [x for x in recurrence or [] if str(x).upper().startswith("RRULE:")]
    autres = [x for x in recurrence or [] if not str(x).upper().startswith(("RRULE:", "EXDATE"))]
    if len(rr) != 1:
        return {}, autres or list(recurrence or [])
    p = {}
    for kv in rr[0][6:].split(";"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            p[k.strip().upper()] = v.strip()
    return p, autres


def repetition(recurrence, debut: dt.date) -> tuple[str, str | None]:
    """Règle Google -> (répétition NEXUS ou « custom », dernière date). Seules les règles que NEXUS sait refaire
    à l'identique sont traduites : sinon « custom » (la règle de Google est gardée telle quelle)."""
    if not recurrence:
        return "none", None
    p, autres = _regle(recurrence)
    if not p or autres:
        return REPEAT_CUSTOM, None
    p = dict(p)
    rep = FREQ.get(p.pop("FREQ", ""))
    p.pop("WKST", None)
    if not rep or p.pop("INTERVAL", "1") != "1" or "COUNT" in p:
        return REPEAT_CUSTOM, None
    until = p.pop("UNTIL", None)
    if rep == "weekly":
        byday = p.pop("BYDAY", None)
        if byday and byday.upper() != JOURS_RRULE[debut.weekday()]:
            return REPEAT_CUSTOM, None
    if rep in ("monthly", "yearly"):
        bymd, setpos = p.pop("BYMONTHDAY", None), p.pop("BYSETPOS", None)
        fin_de_mois = debut.day > 28 and setpos == "-1" and bymd == ",".join(str(x) for x in range(28, debut.day + 1))
        if not (fin_de_mois or (setpos is None and bymd in (None, str(debut.day)))):
            return REPEAT_CUSTOM, None
    if rep == "yearly" and p.pop("BYMONTH", str(debut.month)) != str(debut.month):
        return REPEAT_CUSTOM, None
    if p:
        return REPEAT_CUSTOM, None
    u = _until_local(until) if until else None
    if until and not u:
        return REPEAT_CUSTOM, None
    return rep, u.isoformat() if u else None


def rrule(repeat: str, debut: dt.date, until: str | None, journee: bool) -> list[str]:
    """Répétition NEXUS -> règle Google (même calendrier : le 31 devient le dernier jour des mois courts)."""
    if repeat in (None, "", "none"):
        return []
    freq = {v: k for k, v in FREQ.items()}[repeat]
    r = f"RRULE:FREQ={freq}"
    if repeat in ("monthly", "yearly") and debut.day > 28:
        if repeat == "yearly":
            r += f";BYMONTH={debut.month}"
        r += ";BYMONTHDAY=" + ",".join(str(x) for x in range(28, debut.day + 1)) + ";BYSETPOS=-1"
    if until:
        u = agenda.parse_date(until)
        if journee:
            r += f";UNTIL={u:%Y%m%d}"
        else:  # fin de la journée locale, en UTC (comme le demande la norme pour une série avec heure)
            fin = dt.datetime.combine(u, dt.time(23, 59, 59)).astimezone().astimezone(dt.UTC)
            r += f";UNTIL={fin:%Y%m%dT%H%M%SZ}"
    return [r]


def _until_avant(recurrence: list[str], occ: dt.date, journee: bool) -> list[str]:
    """Coupe une règle Google la veille de occ (COUNT remplacé par UNTIL : la série s'arrête de toute façon avant)."""
    out = []
    for ligne in recurrence or []:
        if str(ligne).upper().startswith("RRULE:"):
            parts = [kv for kv in ligne[6:].split(";") if kv and kv.split("=", 1)[0].upper() not in ("UNTIL", "COUNT")]
            veille = occ - dt.timedelta(days=1)
            if journee:
                parts.append(f"UNTIL={veille:%Y%m%d}")
            else:
                fin = dt.datetime.combine(veille, dt.time(23, 59, 59)).astimezone().astimezone(dt.UTC)
                parts.append(f"UNTIL={fin:%Y%m%dT%H%M%SZ}")
            ligne = "RRULE:" + ";".join(parts)
        out.append(ligne)
    return out


def _ref_minutes() -> int:
    """Heure de référence des rappels NEXUS pour une journée entière (config.json, agenda.heure_reference)."""
    ref = str(config.get("agenda").get("heure_reference") or "09:00")
    if not agenda.TIME_RE.match(ref):
        ref = "09:00"
    h, m = ref.split(":")
    return int(h) * 60 + int(m)


def _rappels_minutes(ev: dict, defaut: list[int]) -> tuple[list[int] | None, list[int]]:
    """(rappels NEXUS : None = « par défaut de Google », minutes effectives).
    Journée entière : Google compte depuis minuit, NEXUS depuis l'heure de référence (09:00) ; on convertit
    pour que le rappel tombe à la même heure des deux côtés (1 jour avant à 9 h = 900 min chez Google)."""
    r = ev.get("reminders") or {}
    if r.get("useDefault", True):
        return None, list(defaut)
    decale = _ref_minutes() if (ev.get("start") or {}).get("date") else 0
    mins = sorted({min(agenda.MAX_REMINDER_MIN, int(o.get("minutes") or 0) + decale) for o in r.get("overrides") or [] if isinstance(o, dict)}, reverse=True)
    return mins, mins


def champs(ev: dict, defaut_rappels: list[int] | None = None, recurrence=None) -> dict:
    """Évènement Google -> champs du formulaire NEXUS (title, date, time, duration…)."""
    s, e = ev.get("start") or {}, ev.get("end") or {}
    priv = (ev.get("extendedProperties") or {}).get("private") or {}
    if s.get("date"):
        d0 = dt.date.fromisoformat(s["date"])
        jours = (dt.date.fromisoformat(e["date"]) - d0).days if e.get("date") else 1
        date, heure, duree = d0, None, jours * 1440 if jours > 1 else None
    else:
        a = _local(s["dateTime"])
        b = _local(e["dateTime"]) if e.get("dateTime") else a
        date, heure = a.date(), a.strftime("%H:%M")
        duree = max(0, round((b - a).total_seconds() / 60)) or None
        if priv.get("nexus_sans_duree") == "1" and duree == 60:
            duree = None
    duree = min(duree, agenda.MAX_DURATION_MIN) if duree else None
    rec = recurrence if recurrence is not None else ev.get("recurrence")
    rep, until = repetition(rec, date)
    anniv = priv.get("nexus_anniversaire") == "1" or ev.get("eventType") == "birthday"
    try:
        annee = int(priv.get("nexus_annee") or 0) or None
    except ValueError:
        annee = None
    rem, _ = _rappels_minutes(ev, defaut_rappels or [])
    return {
        "title": (str(ev.get("summary") or "").strip() or "(sans titre)")[:120],
        "date": date.isoformat(),
        "time": None if anniv else heure,
        "duration": None if anniv else duree,
        "description": _texte(ev.get("description")),
        "repeat": rep,
        "until": until,
        "birthday": anniv,
        "birth_year": annee if anniv else None,
        "reminders": rem,
    }


def _horaires(f: dict, fuseau: str) -> dict:
    d = agenda.parse_date(f["date"])
    if not f.get("time"):
        jours = max(1, math.ceil((f.get("duration") or 0) / 1440))
        return {"start": {"date": d.isoformat()}, "end": {"date": (d + dt.timedelta(days=jours)).isoformat()}}
    hh, mm = (int(x) for x in f["time"].split(":"))
    a = dt.datetime(d.year, d.month, d.day, hh, mm)
    b = a + dt.timedelta(minutes=f.get("duration") or 60)
    out = {"start": {"dateTime": _rfc3339(a)}, "end": {"dateTime": _rfc3339(b)}}
    if fuseau:  # obligatoire pour une série : Google calcule les répétitions dans ce fuseau
        out["start"]["timeZone"] = out["end"]["timeZone"] = fuseau
    return out


def _rappels_google(rem: list[int] | None, journee: bool = False) -> dict:
    if rem is None:
        return {"useDefault": True}
    decale = _ref_minutes() if journee else 0  # (un rappel le jour même avant 9 h : à minuit, au plus tôt)
    return {"useDefault": False, "overrides": [{"method": "popup", "minutes": m} for m in sorted({max(0, int(m) - decale) for m in rem})[:5]]}


def _prive(f: dict) -> dict:
    timed_sans_duree = bool(f.get("time")) and not f.get("duration")
    return {
        "nexus_sans_duree": "1" if timed_sans_duree else "",
        "nexus_anniversaire": "1" if f.get("birthday") else "",
        "nexus_annee": str(f.get("birth_year") or "") if f.get("birthday") else "",
    }


def corps(f: dict, fuseau: str) -> dict:
    """Champs NEXUS validés -> nouvel évènement Google."""
    b = {"summary": f["title"], "description": f.get("description") or "", **_horaires(f, fuseau)}
    b["reminders"] = _rappels_google(f.get("reminders"), not f.get("time"))
    b["extendedProperties"] = {"private": {"nexus": "1", **_prive(f)}}
    rec = rrule(f.get("repeat") or "none", agenda.parse_date(f["date"]), f.get("until"), not f.get("time"))
    if rec:
        b["recurrence"] = rec
    return b


def _differences(avant: dict, apres: dict, fuseau: str, serie: bool) -> dict:
    """Seulement ce qui a changé (le reste de l'évènement Google n'est jamais réécrit)."""
    p: dict = {}
    if apres["title"] != avant["title"]:
        p["summary"] = apres["title"]
    if apres.get("description", "") != avant.get("description", ""):
        p["description"] = apres.get("description", "")
    if any(apres.get(k) != avant.get(k) for k in ("date", "time", "duration")):
        p.update(_horaires(apres, fuseau))
    if apres.get("reminders") != avant.get("reminders") or (apres.get("reminders") is not None and bool(apres.get("time")) != bool(avant.get("time"))):
        p["reminders"] = _rappels_google(apres.get("reminders"), not apres.get("time"))
    if any(apres.get(k) != avant.get(k) for k in ("birthday", "birth_year")) or (bool(apres.get("time")) and not apres.get("duration")) != (
        bool(avant.get("time")) and not avant.get("duration")
    ):
        p["extendedProperties"] = {"private": _prive(apres)}
    if serie and apres.get("repeat") != REPEAT_CUSTOM and (apres.get("repeat"), apres.get("until")) != (avant.get("repeat"), avant.get("until")):
        p["recurrence"] = rrule(apres.get("repeat") or "none", agenda.parse_date(apres["date"]), apres.get("until"), not apres.get("time"))
    elif serie and "start" in p and avant.get("repeat") not in ("none", REPEAT_CUSTOM):
        # série NEXUS déplacée : la date de fin et le « 31 du mois » suivent le nouveau début
        p["recurrence"] = rrule(apres["repeat"], agenda.parse_date(apres["date"]), apres.get("until"), not apres.get("time"))
    return p


def _modifiable(ev: dict, acces: str) -> bool:
    if acces not in ("owner", "writer") or ev.get("locked"):
        return False
    if (ev.get("eventType") or "default") != "default":
        return False  # anniversaires des contacts, absences, e-mails Gmail… : gérés par Google
    org = ev.get("organizer")
    if not org:
        return True  # (aucun organisateur indiqué : évènement de l'agenda lui-même)
    return bool(org.get("self") or ev.get("guestsCanModify"))  # Google n'écrit « self » que pour toi


def occurrence(ev: dict, cache: dict, maitres: dict, exceptions: set) -> dict | None:
    """Instance Google (singleEvents=true) -> occurrence au format de agenda.occurrences()."""
    if ev.get("status") == "cancelled" or not ev.get("start"):
        return None
    serie_id = ev.get("recurringEventId")
    maitre = maitres.get(serie_id) if serie_id else None
    try:
        f = champs(ev, cache.get("defaut_rappels") or [], recurrence=(maitre or {}).get("recurrence") if serie_id else ev.get("recurrence"))
        debut_serie = _jour_local((maitre or {}).get("start")) if maitre else None
        if maitre:  # répétition lue sur la série (le début de la série, pas celui de l'occurrence)
            f["repeat"], f["until"] = repetition(maitre.get("recurrence"), debut_serie or agenda.parse_date(f["date"]))
        elif serie_id:
            f["repeat"], f["until"] = REPEAT_CUSTOM, None  # série commencée avant la période lue
        orig = _jour_local(ev.get("originalStartTime")) or agenda.parse_date(f["date"])
    except (KeyError, TypeError, ValueError):
        return None
    _, effectifs = _rappels_minutes(ev, cache.get("defaut_rappels") or [])
    try:
        maj = dt.datetime.fromisoformat(str(ev.get("updated") or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        maj = 0.0
    jour = agenda.parse_date(f["date"])
    age = jour.year - f["birth_year"] if f["birthday"] and f["birth_year"] else None
    return {
        "id": PREFIXE + ev["id"],
        "event_id": PREFIXE + (serie_id or ev["id"]),
        "google_id": ev["id"],
        "original_date": orig.isoformat(),
        "date": f["date"],
        "time": f["time"],
        "duration": f["duration"],
        "title": f["title"],
        "description": f["description"],
        "reminders": f["reminders"],
        "rappels_effectifs": effectifs,
        "defaut_rappels": cache.get("defaut_rappels") or [],
        "birthday": f["birthday"],
        "age": age if age and age > 0 else None,
        "birth_year": f["birth_year"],
        "repeat": f["repeat"],
        "until": f["until"],
        "series_start": (debut_serie or orig).isoformat(),
        "exception": ev["id"] in exceptions,
        "updated": maj,
        "source": "google",
        "lecture_seule": not _modifiable(ev, cache.get("acces") or ""),
        "lien": ev.get("htmlLink") if str(ev.get("htmlLink") or "").startswith("https://") else "",
    }


# --------------------------------------------------------------------------- #
#  Copie locale et relecture
# --------------------------------------------------------------------------- #
def _lire_cache() -> dict:
    global _cache
    with _lock:
        if _cache is None:
            try:
                c = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                _cache = c if isinstance(c, dict) else {}
            except (OSError, ValueError):
                _cache = {}
        if _cache and _cache.get("agenda") != reglages()["agenda"]:
            _cache = {}
        return _cache


def _ecrire_cache(c: dict) -> None:
    global _cache
    with _lock:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(c, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(CACHE_FILE)
        _cache = c
        _plages.clear()


def _vider_cache() -> None:
    global _cache
    with _lock:
        _cache = {}
        _plages.clear()
        CACHE_FILE.unlink(missing_ok=True)


def _lister(query: dict) -> list[dict]:
    items, page = [], None
    for _ in range(MAX_PAGES):
        q = dict(query, maxResults=2500, **({"pageToken": page} if page else {}))
        r = _appel("GET", _cal() + "/events", q) or {}
        items += [x for x in r.get("items") or [] if isinstance(x, dict) and x.get("id")]
        page = r.get("nextPageToken")
        if not page:
            break
    return items


def _infos_agenda() -> dict:
    r = _appel("GET", "/users/me/calendarList/" + _q(reglages()["agenda"])) or {}
    rappels = sorted({int(x.get("minutes") or 0) for x in r.get("defaultReminders") or [] if isinstance(x, dict)}, reverse=True)
    return {
        "agenda": reglages()["agenda"],
        "agenda_id": str(r.get("id") or reglages()["agenda"]),
        "nom": str(r.get("summaryOverride") or r.get("summary") or "Google Agenda")[:80],
        "fuseau": str(r.get("timeZone") or ""),
        "acces": str(r.get("accessRole") or "reader"),
        "defaut_rappels": rappels,
    }


def _lire_plage(debut: dt.date, fin: dt.date, infos: dict) -> list[dict]:
    q = {"timeMin": _rfc3339(dt.datetime.combine(debut, dt.time())), "timeMax": _rfc3339(dt.datetime.combine(fin + dt.timedelta(days=1), dt.time()))}
    maitres_liste = _lister(dict(q, singleEvents="false"))
    maitres = {e["id"]: e for e in maitres_liste if e.get("recurrence")}
    exceptions = {e["id"] for e in maitres_liste if e.get("recurringEventId")}
    out = []
    for ev in _lister(dict(q, singleEvents="true", orderBy="startTime")):
        o = occurrence(ev, infos, maitres, exceptions)
        if o and debut.isoformat() <= o["date"] <= fin.isoformat():
            out.append(o)
    return out


def _relire() -> dict:
    infos = _infos_agenda()
    today = dt.date.today()
    debut, fin = today - dt.timedelta(days=FENETRE_AVANT), today + dt.timedelta(days=FENETRE_APRES)
    occs = _lire_plage(debut, fin, infos)
    c = {**infos, "debut": debut.isoformat(), "fin": fin.isoformat(), "maj": time.time(), "occurrences": occs}
    _ecrire_cache(c)
    _etat["erreur"] = ""
    _etat["derniere"] = time.time()
    return c


def synchroniser(envoyer: bool = True) -> dict:
    """Relit Google Agenda (période autour d'aujourd'hui) et met la copie locale à jour ; puis, si l'envoi
    automatique est activé, envoie les évènements NEXUS encore locaux (et relit pour les afficher)."""
    if not connecte():
        return etat()
    with _sync_lock:
        try:
            c = _relire()
        except GoogleErreur as exc:
            _etat["erreur"] = str(exc)
            _journal(f"[Google Agenda] relecture impossible : {exc}")
            return etat()
        if envoyer and reglages()["envoi_auto"]:
            erreur_envoi = envoyer_evenements_nexus(c)
            if (_etat.get("envoi") or {}).get("envoyes"):
                try:
                    _relire()
                except GoogleErreur as exc:
                    _etat["erreur"] = str(exc)
            if erreur_envoi:
                _etat["erreur"] = erreur_envoi
    return etat()


# --------------------------------------------------------------------------- #
#  Envoi automatique des évènements NEXUS dans Google Agenda (sans doublon)
# --------------------------------------------------------------------------- #
CHAMPS_ENVOI = ("title", "date", "time", "duration", "description", "repeat", "until", "birthday", "birth_year", "reminders")


def id_envoi(agenda_id: str, eid: str) -> str:
    """Identifiant Google calculé depuis l'agenda et l'évènement NEXUS : toujours le même pour le même évènement
    (caractères a-v et 0-9, comme l'exige Google). Un second envoi est refusé par Google (409) : pas de doublon."""
    return "ag" + hashlib.sha1(f"{agenda_id}|{eid}".encode()).hexdigest()[:30]  # (identifiant, pas de sécurité)


def _lire_envois() -> dict:
    try:
        d = json.loads(ENVOIS_FILE.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _noter_envoi(cle: str, info: dict) -> None:
    with _lock:
        d = _lire_envois()
        d[cle] = info
        ENVOIS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = ENVOIS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(ENVOIS_FILE)


def _champs_envoi(e: dict) -> dict:
    f = agenda.validate({k: e.get(k) for k in CHAMPS_ENVOI})
    if f.get("reminders") is None and f.get("time"):
        # « rappels par défaut » de NEXUS : envoyés tels quels (Google aurait ses propres délais par défaut)
        f["reminders"] = sorted({int(x) for x in config.get("agenda").get("rappels_minutes") or [] if str(x).isdigit()}, reverse=True)
    return f


def _envoyer_un(e: dict, c: dict) -> str:
    """Crée (ou met à jour, s'il est déjà là) l'évènement NEXUS e dans Google, exceptions comprises. Renvoie son id Google."""
    fuseau = c.get("fuseau") or ""
    f = _champs_envoi(e)
    b = corps(f, fuseau)
    b["extendedProperties"]["private"]["nexus_id"] = str(e["id"])[:100]
    gid = id_envoi(c.get("agenda_id") or c.get("agenda") or "", e["id"])
    try:
        _appel("POST", _cal() + "/events", corps={**b, "id": gid})
    except DejaExistant:
        # déjà envoyé (envoi interrompu, ou évènement modifié dans NEXUS depuis) : mise à jour, jamais de doublon
        ev = _appel("GET", _cal() + "/events/" + _q(gid)) or {}
        if ev.get("status") == "cancelled":
            return gid  # supprimé entre-temps dans Google Agenda : on ne le recrée pas
        _appel("PATCH", _cal() + "/events/" + _q(gid), corps=b)
    for occ, x in sorted((e.get("exceptions") or {}).items()):
        if not agenda.DATE_RE.match(str(occ)) or not isinstance(x, dict):
            continue
        try:
            inst = _instance(gid, occ, {})
        except OccurrenceAbsente:
            continue  # déjà annulée (envoi repris) ou hors de la série
        if x.get("cancelled"):
            _appel("DELETE", _cal() + "/events/" + _q(inst["id"]))
            continue
        base = champs(inst, c.get("defaut_rappels") or [], recurrence=[])
        modif = {k: x[k] for k in agenda.ONE_FIELDS if k in x}
        if f.get("birthday"):
            modif.pop("time", None)
            modif.pop("duration", None)
        apres = {**base, **agenda.validate(modif, base=base)} if modif else base
        p = _differences(base, apres, fuseau, serie=False)
        if p:
            _appel("PATCH", _cal() + "/events/" + _q(inst["id"]), corps=p)
    return gid


def envoyer_evenements_nexus(c: dict | None = None) -> str:
    """Envoie dans Google Agenda les évènements NEXUS encore locaux (sauf « NEXUS seulement »), puis les retire de
    NEXUS. Réseau coupé ou refus : l'évènement reste dans NEXUS, nouvel essai à la relecture suivante.
    Renvoie le message d'erreur à afficher (vide si tout va bien)."""
    c = c or _lire_cache()
    a_envoyer = [e for e in agenda.load()["events"] if not e.get("seulement_nexus")]
    if not a_envoyer:
        return ""
    if c.get("acces") not in ("owner", "writer"):
        msg = f"{len(a_envoyer)} évènement(s) NEXUS non envoyé(s) : l'agenda Google relié est en lecture seule (choisis-en un autre dans ⚙ Réglages)."
        _etat["envoi"] = {"t": time.time(), "envoyes": 0, "restants": len(a_envoyer), "message": msg}
        return msg
    agenda_id = c.get("agenda_id") or c.get("agenda") or ""
    envois = _lire_envois()
    envoyes, refuses, erreur = 0, [], ""
    for e in a_envoyer[:ENVOI_MAX]:
        cle = f"{agenda_id}|{e['id']}"
        deja = envois.get(cle)
        try:
            if deja and deja.get("updated") == e.get("updated"):
                gid = deja["google_id"]  # envoyé, mais retrait de NEXUS interrompu : on le finit seulement
            else:
                gid = _envoyer_un(e, c)
                _noter_envoi(cle, {"google_id": gid, "titre": e.get("title", "")[:120], "updated": e.get("updated"), "t": time.time()})
        except Refuse as exc:
            refuses.append(f"« {e.get('title', '')[:40]} » : {exc}")
            continue
        except agenda.AgendaError as exc:
            if not isinstance(exc, GoogleErreur):  # données NEXUS invalides pour Google : cet évènement seulement
                refuses.append(f"« {e.get('title', '')[:40]} » : {exc}")
                continue
            erreur = f"Envoi vers Google Agenda interrompu : {exc} Nouvel essai à la prochaine relecture."
            break
        if agenda.retirer_envoye(e["id"], e.get("updated")):
            envoyes += 1
    restants = comptes_locaux()["a_envoyer"]
    if refuses and not erreur:
        erreur = f"{len(refuses)} évènement(s) NEXUS refusé(s) par Google, gardé(s) dans NEXUS : " + " ; ".join(refuses[:3])
    msg = f"{envoyes} évènement{'s' if envoyes > 1 else ''} NEXUS envoyé{'s' if envoyes > 1 else ''} dans Google Agenda" if envoyes else ""
    if envoyes or erreur:
        _etat["envoi"] = {"t": time.time(), "envoyes": envoyes, "restants": restants, "message": msg or erreur}
    if envoyes:
        _journal(f"[Google Agenda] {msg} ({restants} encore dans NEXUS)")
    return erreur


def occurrences(debut: dt.date, fin: dt.date, reseau: bool = True) -> list[dict]:
    """Occurrences Google entre debut et fin (copie locale ; hors de sa période : lues à la demande)."""
    if not connecte():
        return []
    c = _lire_cache()
    occs = c.get("occurrences") or []
    a, b = debut.isoformat(), fin.isoformat()
    if c.get("debut") and c["debut"] <= a and b <= c["fin"]:
        return [o for o in occs if a <= o["date"] <= b]
    if reseau and c.get("maj"):
        cle = (a, b)
        with _lock:
            deja = _plages.get(cle)
        if deja and time.time() - deja[0] < 600:
            return deja[1]
        try:
            lu = _lire_plage(debut, fin, c)
            with _lock:
                if len(_plages) > 12:
                    _plages.clear()
                _plages[cle] = (time.time(), lu)
            return lu
        except GoogleErreur as exc:
            _etat["erreur"] = str(exc)
    return [o for o in occs if a <= o["date"] <= b]


def occurrences_rappels(debut: dt.date, fin: dt.date) -> list[dict]:
    """Pour reminders.py : copie locale seulement (jamais de réseau), rappels effectifs de Google."""
    if not connecte() or not reglages()["rappels"]:
        return []
    return [{**o, "reminders": o.get("rappels_effectifs") or []} for o in occurrences(debut, fin, reseau=False)]


def agendas() -> list[dict]:
    """Agendas Google où NEXUS peut écrire (pour le choix dans ⚙ Réglages)."""
    r = _appel("GET", "/users/me/calendarList", {"minAccessRole": "writer", "maxResults": 250}) or {}
    out = [
        {"id": str(x.get("id")), "nom": str(x.get("summaryOverride") or x.get("summary") or x.get("id"))[:80], "principal": bool(x.get("primary"))}
        for x in r.get("items") or []
        if isinstance(x, dict) and x.get("id")
    ]
    out.sort(key=lambda x: (not x["principal"], x["nom"].lower()))
    return out


# --------------------------------------------------------------------------- #
#  Créer / modifier / supprimer depuis NEXUS
# --------------------------------------------------------------------------- #
def est_google(eid: str) -> bool:
    return str(eid or "").startswith(PREFIXE)


def _gid(eid: str) -> str:
    g = str(eid or "")[len(PREFIXE) :]
    if not re.fullmatch(r"[A-Za-z0-9_@.-]{1,1024}", g):
        raise GoogleErreur("Évènement Google invalide.")
    return g


def _ecriture_possible() -> dict:
    if not connecte():
        raise GoogleErreur("Google Agenda n'est pas relié : ⚙ Réglages → Google Agenda.")
    c = _lire_cache()
    if not c.get("maj"):
        synchroniser()
        c = _lire_cache()
    if not c.get("maj"):
        raise GoogleErreur(_etat.get("erreur") or "Google Agenda injoignable : réessaie plus tard.")
    if c.get("acces") not in ("owner", "writer"):
        raise GoogleErreur("Cet agenda Google est en lecture seule : choisis-en un autre dans ⚙ Réglages → Google Agenda.")
    return c


def _verifier_modifiable(ev: dict, c: dict) -> None:
    if not _modifiable(ev, c.get("acces") or ""):
        raise GoogleErreur("Cet évènement se modifie seulement dans Google Agenda (invitation, anniversaire d'un contact, évènement verrouillé…).")


def _apres() -> None:
    """Après une écriture : la copie locale est relue tout de suite (le panel voit la modification)."""
    synchroniser()


def creer(fields: dict) -> dict:
    c = _ecriture_possible()
    f = agenda.validate(fields)
    ev = _appel("POST", _cal() + "/events", corps=corps(f, c.get("fuseau") or "")) or {}
    _apres()
    return {"id": PREFIXE + str(ev.get("id") or ""), **f, "source": "google"}


def _instance(serie: str, occ: str, c: dict) -> dict:
    """Occurrence d'une série Google à sa date d'origine (date locale)."""
    for o in c.get("occurrences") or []:
        if o["event_id"] == PREFIXE + serie and o["original_date"] == occ:
            ev = _appel("GET", _cal() + "/events/" + _q(o["google_id"]))
            if ev and ev.get("status") != "cancelled":
                return ev
    d = agenda.parse_date(occ)
    q = {
        "timeMin": _rfc3339(dt.datetime.combine(d - dt.timedelta(days=1), dt.time())),
        "timeMax": _rfc3339(dt.datetime.combine(d + dt.timedelta(days=2), dt.time())),
    }
    r = _appel("GET", _cal() + "/events/" + _q(serie) + "/instances", dict(q, showDeleted="false")) or {}
    for ev in r.get("items") or []:
        if _jour_local(ev.get("originalStartTime")) == d and ev.get("status") != "cancelled":
            return ev
    raise OccurrenceAbsente("Cette occurrence n'existe plus dans Google Agenda.")


def _sans_repeat_custom(fields: dict) -> dict:
    f = dict(fields or {})
    if f.get("repeat") == REPEAT_CUSTOM:
        f.pop("repeat", None)
        f.pop("until", None)
    return f


def modifier(eid: str, fields: dict, occ: str | None = None, scope: str = "all") -> dict:
    c = _ecriture_possible()
    fuseau = c.get("fuseau") or ""
    gid = _gid(eid)
    maitre = _appel("GET", _cal() + "/events/" + _q(gid)) or {}
    _verifier_modifiable(maitre, c)
    serie = bool(maitre.get("recurrence"))
    avant = champs(maitre, c.get("defaut_rappels") or [])
    if not serie or scope not in agenda.SCOPES:
        scope = "all"
    debut_serie = avant["date"]
    if serie and occ and not agenda.DATE_RE.match(occ):
        raise GoogleErreur("Occurrence invalide.")
    if scope == "following" and occ == debut_serie:
        scope = "all"
    fields = _sans_repeat_custom(fields)

    if scope == "one":
        bad = [k for k in fields if k not in agenda.ONE_FIELDS]
        if bad:
            raise GoogleErreur("Pour une seule occurrence, on peut changer le titre, la date, l'heure, la durée, la description et les rappels.")
        inst = _instance(gid, occ or "", c)
        base = champs(inst, c.get("defaut_rappels") or [], recurrence=[])
        f = agenda.validate(fields, base=base)
        p = _differences(base, {**base, **f}, fuseau, serie=False)
        if p:
            _appel("PATCH", _cal() + "/events/" + _q(inst["id"]), corps=p)
        _apres()
        return {"id": PREFIXE + inst["id"], "source": "google"}

    if scope == "all":
        if serie and "date" in fields and occ:
            # NEXUS déplace TOUTE la série du même nombre de jours que l'occurrence modifiée
            try:
                delta = (agenda.parse_date(str(fields["date"])) - agenda.parse_date(occ)).days
            except ValueError:
                delta = 0
            fields = dict(fields, date=(agenda.parse_date(debut_serie) + dt.timedelta(days=delta)).isoformat())
            if delta and avant.get("until") and "until" not in fields:
                fields["until"] = (agenda.parse_date(avant["until"]) + dt.timedelta(days=delta)).isoformat()
        if avant["repeat"] == REPEAT_CUSTOM and fields.get("repeat") in (None, REPEAT_CUSTOM):
            fields.pop("repeat", None)
        f = agenda.validate(fields, base={**avant, "repeat": "none" if avant["repeat"] == REPEAT_CUSTOM else avant["repeat"]})
        apres = {**avant, **f}
        if avant["repeat"] == REPEAT_CUSTOM and "repeat" not in fields:
            apres["repeat"], apres["until"] = REPEAT_CUSTOM, avant["until"]
        p = _differences(avant, apres, fuseau, serie=True)
        if p:
            _appel("PATCH", _cal() + "/events/" + _q(gid), corps=p)
        _apres()
        return {"id": eid, "source": "google"}

    # scope == "following" : la série s'arrête la veille, une nouvelle commence à cette occurrence
    occ_d = agenda.parse_date(occ or "")
    inst = _instance(gid, occ or "", c)
    base = {**avant, **{k: v for k, v in champs(inst, c.get("defaut_rappels") or [], recurrence=[]).items() if k in ("date", "time", "duration")}}
    if avant["repeat"] == REPEAT_CUSTOM and "repeat" not in fields:
        p_regle, _ = _regle(maitre.get("recurrence"))
        if "COUNT" in p_regle:
            raise GoogleErreur("Cette série Google a un nombre fixe de répétitions : modifie « les suivantes » directement dans Google Agenda.")
    f = agenda.validate(fields, base={**base, "repeat": "none" if base["repeat"] == REPEAT_CUSTOM else base["repeat"]})
    apres = {**base, **f}
    nouveau = {
        k: v
        for k, v in maitre.items()
        if k
        not in (
            "id",
            "iCalUID",
            "etag",
            "htmlLink",
            "created",
            "updated",
            "sequence",
            "organizer",
            "creator",
            "recurringEventId",
            "originalStartTime",
            "hangoutLink",
            "conferenceData",
            "kind",
            "status",
        )
    }
    nouveau.update(
        summary=apres["title"],
        description=apres.get("description", "") if apres.get("description", "") != avant.get("description", "") else maitre.get("description", ""),
        reminders=_rappels_google(apres.get("reminders"), not apres.get("time")),
        **_horaires(apres, fuseau),
    )
    priv = dict(((maitre.get("extendedProperties") or {}).get("private")) or {})
    priv.update(_prive(apres))
    nouveau["extendedProperties"] = {**(maitre.get("extendedProperties") or {}), "private": priv}
    if apres["repeat"] == REPEAT_CUSTOM:
        nouveau["recurrence"] = [x for x in maitre.get("recurrence") or [] if not str(x).upper().startswith("EXDATE")]
    else:
        nouveau["recurrence"] = rrule(apres["repeat"], agenda.parse_date(apres["date"]), apres.get("until"), not apres.get("time")) or None
        if not nouveau["recurrence"]:
            nouveau.pop("recurrence")
    cree = _appel("POST", _cal() + "/events", corps=nouveau) or {}
    _appel("PATCH", _cal() + "/events/" + _q(gid), corps={"recurrence": _until_avant(maitre["recurrence"], occ_d, not avant.get("time"))})
    _apres()
    return {"id": PREFIXE + str(cree.get("id") or ""), "source": "google"}


def supprimer(eid: str, occ: str | None = None, scope: str = "all") -> None:
    c = _ecriture_possible()
    gid = _gid(eid)
    maitre = _appel("GET", _cal() + "/events/" + _q(gid)) or {}
    _verifier_modifiable(maitre, c)
    serie = bool(maitre.get("recurrence"))
    debut = champs(maitre, [])["date"]
    if not serie or scope not in agenda.SCOPES or (scope == "following" and occ == debut):
        scope = "all"
    if scope == "all":
        _appel("DELETE", _cal() + "/events/" + _q(gid))
    elif scope == "one":
        inst = _instance(gid, occ or "", c)
        _appel("DELETE", _cal() + "/events/" + _q(inst["id"]))
    else:
        if not occ or not agenda.DATE_RE.match(occ):
            raise GoogleErreur("Occurrence invalide.")
        _appel(
            "PATCH",
            _cal() + "/events/" + _q(gid),
            corps={"recurrence": _until_avant(maitre["recurrence"], agenda.parse_date(occ), not champs(maitre, [])["time"])},
        )
    _apres()


# --------------------------------------------------------------------------- #
#  Relecture en arrière-plan
# --------------------------------------------------------------------------- #
def reveiller() -> None:
    _reveil.set()


def demarrer() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()

    def boucle():
        _reveil.wait(15)  # laisse NEXUS démarrer
        while not _stop.is_set():
            _reveil.clear()
            try:
                if connecte():
                    synchroniser()
            except Exception as exc:  # une erreur inattendue n'arrête jamais le serveur
                _journal(f"[Google Agenda] erreur : {type(exc).__name__}: {exc}")
            _reveil.wait(reglages()["intervalle_minutes"] * 60)

    _thread = threading.Thread(target=boucle, daemon=True, name="google-agenda")
    _thread.start()


def arreter() -> None:
    _stop.set()
    _reveil.set()
    _arreter_serveur_connexion()
