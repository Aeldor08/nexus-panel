"""Faux Google (OAuth 2.0 + API Google Calendar v3) pour tester la liaison de l'Agenda sans compte ni réseau.

Utilisé par test_agenda_google.py ; lançable seul pour essayer l'interface sur une copie isolée de NEXUS :
    python outils/tests/faux_google.py 8790        (puis NEXUS avec NEXUS_GOOGLE_*_TEST, voir test_agenda_google.py)
Il ne connaît qu'un compte et deux agendas fictifs. Les répétitions sont développées dans l'heure locale du PC
(comme Google le fait dans le fuseau de l'agenda) : FREQ DAILY / WEEKLY / MONTHLY / YEARLY, INTERVAL, COUNT, UNTIL,
BYDAY (hebdomadaire) et BYMONTHDAY + BYSETPOS=-1 (fin de mois).
"""

from __future__ import annotations

import base64
import copy
import datetime as dt
import hashlib
import json
import re
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CLIENT_ID = "faux-client-nexus.apps.googleusercontent.com"
CLIENT_SECRET = "faux-secret-de-test-nexus"
JOURS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


def _local(s: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d.astimezone().replace(tzinfo=None) if d.tzinfo else d


def _iso(d: dt.datetime) -> str:
    return d.astimezone().isoformat(timespec="seconds")


def _days_in(y: int, m: int) -> int:
    return (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day


class Etat:
    def __init__(self) -> None:
        self.codes: dict[str, dict] = {}  # code -> {challenge, redirect_uri}
        self.refresh = set()
        self.acces = set()
        self.agendas = {
            "moi@exemple.fr": {
                "id": "moi@exemple.fr",
                "summary": "Agenda de test",
                "primary": True,
                "timeZone": "Europe/Paris",
                "accessRole": "owner",
                "defaultReminders": [{"method": "popup", "minutes": 15}],
            },
            "famille@exemple.fr": {
                "id": "famille@exemple.fr",
                "summary": "Famille (lecture)",
                "timeZone": "Europe/Paris",
                "accessRole": "reader",
                "defaultReminders": [],
            },
        }
        self.events: dict[str, dict[str, dict]] = {k: {} for k in self.agendas}  # agenda -> id -> évènement / exception
        self.journal: list[tuple[str, str, dict | None]] = []  # (méthode, chemin, corps)
        self.refuser_api = False
        self.utilises: set[str] = set()  # identifiants déjà pris (même supprimés), comme chez Google : 409
        self.ecritures_avant_coupure: int | None = None  # réseau coupé après N écritures (None = jamais)
        self.refuser_titre = ""  # évènements dont le titre contient ce texte : refusés (400)
        self.lock = threading.RLock()

    def cal(self, cid: str) -> str:
        return "moi@exemple.fr" if cid == "primary" else cid

    # -- développement des répétitions ------------------------------------------------
    def _debuts(self, ev: dict, fin: dt.datetime) -> list[dt.datetime | dt.date]:
        s = ev["start"]
        journee = "date" in s
        d0 = dt.date.fromisoformat(s["date"]) if journee else _local(s["dateTime"])
        rr = next((x[6:] for x in ev.get("recurrence") or [] if x.upper().startswith("RRULE:")), None)
        if not rr:
            return [d0]
        p = dict(kv.split("=", 1) for kv in rr.split(";") if "=" in kv)
        freq, inter = p["FREQ"], int(p.get("INTERVAL", "1"))
        count = int(p["COUNT"]) if "COUNT" in p else None
        until = None
        if "UNTIL" in p:
            u = p["UNTIL"]
            if "T" in u:
                ud = dt.datetime.strptime(u.rstrip("Z"), "%Y%m%dT%H%M%S")
                if u.endswith("Z"):
                    ud = ud.replace(tzinfo=dt.UTC).astimezone().replace(tzinfo=None)
                until = ud
            else:
                until = dt.datetime.combine(dt.datetime.strptime(u, "%Y%m%d").date(), dt.time(23, 59, 59))
        byday = p.get("BYDAY", "").split(",") if p.get("BYDAY") else None
        finmois = p.get("BYSETPOS") == "-1" and p.get("BYMONTHDAY")
        jour0 = d0 if journee else d0.date()
        heure = None if journee else d0.time()
        out = []
        d = jour0
        limite = fin.date() + dt.timedelta(days=1)
        while d <= limite and len(out) < 5000:
            ok = False
            delta = (d - jour0).days
            if freq == "DAILY":
                ok = delta % inter == 0
            elif freq == "WEEKLY":
                semaine = (d - (jour0 - dt.timedelta(days=jour0.weekday()))).days // 7
                ok = semaine % inter == 0 and (JOURS[d.weekday()] in byday if byday else d.weekday() == jour0.weekday())
            elif freq == "MONTHLY":
                mois = (d.year - jour0.year) * 12 + d.month - jour0.month
                cible = min(jour0.day, _days_in(d.year, d.month)) if finmois else jour0.day
                ok = mois % inter == 0 and d.day == cible
            elif freq == "YEARLY":
                cible = min(jour0.day, _days_in(d.year, d.month)) if finmois else jour0.day
                ok = (d.year - jour0.year) % inter == 0 and d.month == jour0.month and d.day == cible
            if ok:
                x = d if journee else dt.datetime.combine(d, heure)
                xd = dt.datetime.combine(d, heure or dt.time())
                if until and xd > until:
                    break
                out.append(x)
                if count and len(out) >= count:
                    break
            d += dt.timedelta(days=1)
        return out

    def _inst_id(self, mid: str, debut) -> str:
        if isinstance(debut, dt.datetime):
            return f"{mid}_{debut.astimezone().astimezone(dt.UTC):%Y%m%dT%H%M%SZ}"
        return f"{mid}_{debut:%Y%m%d}"

    def _instance(self, m: dict, debut) -> dict:
        x = copy.deepcopy(m)
        x.pop("recurrence", None)
        if isinstance(debut, dt.datetime):
            dur = _local(m["end"]["dateTime"]) - _local(m["start"]["dateTime"])
            x["start"] = {"dateTime": _iso(debut), "timeZone": m["start"].get("timeZone")}
            x["end"] = {"dateTime": _iso(debut + dur), "timeZone": m["end"].get("timeZone")}
            x["originalStartTime"] = {"dateTime": _iso(debut)}
        else:
            dur = dt.date.fromisoformat(m["end"]["date"]) - dt.date.fromisoformat(m["start"]["date"])
            x["start"], x["end"] = {"date": debut.isoformat()}, {"date": (debut + dur).isoformat()}
            x["originalStartTime"] = {"date": debut.isoformat()}
        x["id"] = self._inst_id(m["id"], debut)
        x["recurringEventId"] = m["id"]
        return x

    def instances(self, cal: str, mid: str, t0: dt.datetime, t1: dt.datetime) -> list[dict]:
        m = self.events[cal][mid]
        out = []
        for debut in self._debuts(m, t1):
            iid = self._inst_id(mid, debut)
            x = copy.deepcopy(self.events[cal].get(iid)) or self._instance(m, debut)
            if x.get("status") == "cancelled":
                continue
            if self._chevauche(x, t0, t1):
                out.append(x)
        return out

    def _chevauche(self, ev: dict, t0: dt.datetime, t1: dt.datetime) -> bool:
        s, e = ev["start"], ev["end"]
        a = dt.datetime.combine(dt.date.fromisoformat(s["date"]), dt.time()) if "date" in s else _local(s["dateTime"])
        b = dt.datetime.combine(dt.date.fromisoformat(e["date"]), dt.time()) if "date" in e else _local(e["dateTime"])
        return a < t1 and b > t0 if b > a else t0 <= a < t1

    def lister(self, cal: str, q: dict) -> list[dict]:
        t0, t1 = _local(q["timeMin"]), _local(q["timeMax"])
        out = []
        for ev in list(self.events[cal].values()):
            if ev.get("recurringEventId"):
                if q.get("singleEvents") != "true":
                    out.append(copy.deepcopy(ev))  # exceptions : à part en mode « séries »
                continue
            if ev.get("status") == "cancelled":
                continue
            if ev.get("recurrence"):
                if q.get("singleEvents") == "true":
                    out += self.instances(cal, ev["id"], t0, t1)
                elif self.instances(cal, ev["id"], t0, t1):
                    out.append(copy.deepcopy(ev))
            elif self._chevauche(ev, t0, t1):
                out.append(copy.deepcopy(ev))
        return out

    def trouver(self, cal: str, eid: str) -> dict | None:
        if eid in self.events[cal]:
            return self.events[cal][eid]
        if "_" in eid:  # occurrence pas encore modifiée : générée depuis sa série
            mid, _quand = eid.rsplit("_", 1)
            m = self.events[cal].get(mid)
            if m and m.get("recurrence"):
                for debut in self._debuts(m, dt.datetime.now() + dt.timedelta(days=800)):
                    if self._inst_id(mid, debut) == eid:
                        x = self._instance(m, debut)
                        self.events[cal][eid] = x
                        return x
        return None

    def ajouter(self, cal: str, ev: dict) -> dict:
        ev = copy.deepcopy(ev)
        ev.setdefault("id", secrets.token_hex(8))
        self.utilises.add(ev["id"])
        ev.setdefault("status", "confirmed")
        ev.setdefault("eventType", "default")
        ev.setdefault("organizer", {"email": "moi@exemple.fr", "self": True})
        ev.setdefault("updated", dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"))
        ev["htmlLink"] = f"https://calendar.google.com/calendar/event?eid={ev['id']}"
        self.events[cal][ev["id"]] = ev
        return ev


def serveur(port: int = 0) -> tuple[ThreadingHTTPServer, Etat]:
    etat = Etat()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, code: int, data) -> None:
            b = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _corps(self):
            n = int(self.headers.get("Content-Length") or 0)
            brut = self.rfile.read(n).decode() if n else ""
            if "json" in (self.headers.get("Content-Type") or ""):
                return json.loads(brut or "null")
            return dict(urllib.parse.parse_qsl(brut))

        def _api(self, methode: str):
            u = urllib.parse.urlparse(self.path)
            q = dict(urllib.parse.parse_qsl(u.query))
            corps = self._corps() if methode in ("POST", "PATCH", "PUT") else None
            if u.path.startswith("/token"):
                return self._token(corps)
            if u.path.startswith("/revoke"):
                etat.refresh.discard(corps.get("token"))
                return self._json(200, {})
            if u.path.startswith("/auth"):
                return self._auth(q)
            tok = (self.headers.get("Authorization") or "").removeprefix("Bearer ")
            if tok not in etat.acces:
                return self._json(401, {"error": {"code": 401, "message": "Invalid Credentials"}})
            if methode in ("POST", "PATCH", "DELETE") and etat.ecritures_avant_coupure is not None:
                if etat.ecritures_avant_coupure <= 0:
                    self.close_connection = True  # coupure : aucune réponse
                    return None
                etat.ecritures_avant_coupure -= 1
            if etat.refuser_api:
                return self._json(403, {"error": {"code": 403, "message": "Calendar API has not been used", "errors": [{"reason": "accessNotConfigured"}]}})
            chemin = [urllib.parse.unquote(x) for x in u.path.split("/") if x][2:]  # sans calendar/v3
            with etat.lock:
                etat.journal.append((methode, "/" + "/".join(chemin), corps))
                return self._calendrier(methode, chemin, q, corps)

        def _auth(self, q):
            if q.get("client_id") != CLIENT_ID or q.get("code_challenge_method") != "S256" or "calendar.events" not in q.get("scope", ""):
                return self._json(400, {"error": "invalid_request"})
            code = secrets.token_urlsafe(12)
            etat.codes[code] = {"challenge": q["code_challenge"], "redirect_uri": q["redirect_uri"]}
            self.send_response(302)
            self.send_header("Location", q["redirect_uri"] + "?" + urllib.parse.urlencode({"code": code, "state": q["state"], "scope": q["scope"]}))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        def _token(self, c):
            if c.get("client_id") != CLIENT_ID or c.get("client_secret") != CLIENT_SECRET:
                return self._json(401, {"error": "invalid_client"})
            acces = "acces-" + secrets.token_hex(8)
            if c.get("grant_type") == "authorization_code":
                info = etat.codes.pop(c.get("code"), None)
                attendu = info and base64.urlsafe_b64encode(hashlib.sha256(c.get("code_verifier", "").encode()).digest()).rstrip(b"=").decode()
                if not info or attendu != info["challenge"] or c.get("redirect_uri") != info["redirect_uri"]:
                    return self._json(400, {"error": "invalid_grant"})
                rt = "rafraichir-" + secrets.token_hex(8)
                etat.refresh.add(rt)
                etat.acces.add(acces)
                return self._json(200, {"access_token": acces, "refresh_token": rt, "expires_in": 3599, "token_type": "Bearer"})
            if c.get("grant_type") == "refresh_token" and c.get("refresh_token") in etat.refresh:
                etat.acces.add(acces)
                return self._json(200, {"access_token": acces, "expires_in": 3599, "token_type": "Bearer"})
            return self._json(400, {"error": "invalid_grant", "error_description": "Token has been expired or revoked."})

        def _calendrier(self, m, p, q, corps):
            if p[:2] == ["users", "me"] and p[2:3] == ["calendarList"]:
                if len(p) == 3:
                    items = [a for a in etat.agendas.values() if q.get("minAccessRole") != "writer" or a["accessRole"] in ("owner", "writer")]
                    return self._json(200, {"items": items})
                a = etat.agendas.get(etat.cal(p[3]))
                return self._json(200, a) if a else self._json(404, {"error": {"code": 404}})
            if p[0] != "calendars" or etat.cal(p[1]) not in etat.events:
                return self._json(404, {"error": {"code": 404, "message": "Not Found"}})
            cal = etat.cal(p[1])
            if len(p) == 3 and m == "GET":
                return self._json(200, {"items": etat.lister(cal, q)})
            if len(p) == 3 and m == "POST":
                if etat.agendas[cal]["accessRole"] not in ("owner", "writer"):
                    return self._json(403, {"error": {"code": 403, "message": "Forbidden"}})
                if "recurrence" in corps and not all(x.get("timeZone") for x in (corps["start"], corps["end"]) if "dateTime" in x):
                    return self._json(400, {"error": {"code": 400, "message": "Missing time zone definition for start time."}})
                if "id" in corps:
                    if not re.fullmatch(r"[a-v0-9]{5,1024}", str(corps["id"])):
                        return self._json(400, {"error": {"code": 400, "message": "Invalid resource id value."}})
                    if corps["id"] in etat.utilises:
                        return self._json(409, {"error": {"code": 409, "message": "The requested identifier already exists."}})
                if etat.refuser_titre and etat.refuser_titre in str(corps.get("summary")):
                    return self._json(400, {"error": {"code": 400, "message": "Invalid value"}})
                return self._json(200, etat.ajouter(cal, corps))
            ev = etat.trouver(cal, p[3])
            if ev is None or (ev.get("status") == "cancelled" and m != "DELETE"):
                return self._json(404, {"error": {"code": 404, "message": "Not Found"}})
            if len(p) == 5 and p[4] == "instances":
                return self._json(200, {"items": etat.instances(cal, ev["id"], _local(q["timeMin"]), _local(q["timeMax"]))})
            if m == "GET":
                return self._json(200, ev)
            if m == "DELETE":
                if ev.get("status") == "cancelled":
                    return self._json(410, {"error": {"code": 410, "message": "Resource has been deleted"}})
                if ev.get("recurringEventId"):
                    ev["status"] = "cancelled"
                else:
                    for k in [k for k, v in etat.events[cal].items() if k == ev["id"] or v.get("recurringEventId") == ev["id"]]:
                        del etat.events[cal][k]
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            if m == "PATCH":
                for k, v in corps.items():
                    if k == "extendedProperties":
                        priv = ev.setdefault("extendedProperties", {}).setdefault("private", {})
                        priv.update((v or {}).get("private") or {})
                    else:
                        ev[k] = v
                ev["updated"] = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
                return self._json(200, ev)
            return self._json(405, {"error": {"code": 405}})

        def do_GET(self):
            self._api("GET")

        def do_POST(self):
            self._api("POST")

        def do_PATCH(self):
            self._api("PATCH")

        def do_DELETE(self):
            self._api("DELETE")

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, etat


def env(port: int) -> dict:
    """Variables d'environnement qui pointent NEXUS vers ce faux Google."""
    base = f"http://127.0.0.1:{port}"
    return {
        "NEXUS_GOOGLE_AUTH_TEST": base + "/auth",
        "NEXUS_GOOGLE_TOKEN_TEST": base + "/token",
        "NEXUS_GOOGLE_REVOKE_TEST": base + "/revoke",
        "NEXUS_GOOGLE_API_TEST": base + "/calendar/v3",
        "NEXUS_IDENTIFIANTS": "memoire",
    }


def exemples(etat: Etat) -> None:
    """Quelques évènements d'exemple autour d'aujourd'hui (pour essayer l'interface)."""
    j = dt.date.today()
    cal = "moi@exemple.fr"
    at = lambda d, h, m=0: _iso(dt.datetime.combine(d, dt.time(h, m)))  # noqa: E731
    etat.ajouter(
        cal, {"summary": "Dentiste", "start": {"dateTime": at(j + dt.timedelta(days=2), 10)}, "end": {"dateTime": at(j + dt.timedelta(days=2), 10, 45)}}
    )
    etat.ajouter(
        cal,
        {
            "summary": "Sport",
            "start": {"dateTime": at(j, 18), "timeZone": "Europe/Paris"},
            "end": {"dateTime": at(j, 19), "timeZone": "Europe/Paris"},
            "recurrence": [f"RRULE:FREQ=WEEKLY;BYDAY={JOURS[j.weekday()]}"],
            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]},
        },
    )
    etat.ajouter(
        cal, {"summary": "Vacances", "start": {"date": (j + dt.timedelta(days=9)).isoformat()}, "end": {"date": (j + dt.timedelta(days=12)).isoformat()}}
    )
    etat.ajouter(
        cal,
        {
            "summary": "Réunion d'équipe (invitation)",
            "start": {"dateTime": at(j + dt.timedelta(days=1), 14)},
            "end": {"dateTime": at(j + dt.timedelta(days=1), 15)},
            "organizer": {"email": "chef@exemple.fr"},
            "attendees": [{"email": "moi@exemple.fr", "self": True}],
        },
    )


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8790
    s, e = serveur(port)
    if len(sys.argv) > 2:  # nom de l'agenda principal (ex. une longue adresse, pour essayer l'affichage)
        e.agendas["moi@exemple.fr"]["summary"] = sys.argv[2]
    exemples(e)
    print(f"Faux Google sur http://127.0.0.1:{port} (client : {CLIENT_ID} / {CLIENT_SECRET})", flush=True)
    threading.Event().wait()
