r"""Agenda de NEXUS : évènements (répétitions, exceptions, rappels), to-do et notes — data\agenda.json.

Format 2 (depuis la v3.9) :
{
  "format": 2,
  "events": [{
     "id", "title", "date": "AAAA-MM-JJ" (1re occurrence), "time": "HH:MM" | null (journée entière),
     "duration": minutes | null, "description": "", "repeat": none|daily|weekly|monthly|yearly,
     "until": "AAAA-MM-JJ" | null (dernière occurrence possible), "birthday": bool, "birth_year": int | null,
     "reminders": [minutes…] | null (null = délais par défaut de config.json),
     "exceptions": { "AAAA-MM-JJ d'origine": {"cancelled": true} | {champs modifiés : title, date, time,
                     duration, description, reminders} },
     "created", "updated": horodatages (secondes),
     "seulement_nexus": true si créé avec le choix « NEXUS (sur ce PC seulement) » : jamais envoyé dans Google Agenda
  }],
  "todos": [...], "notes": [...]
}
Les anniversaires sont toujours en journée entière et répétés chaque année.

Modifier / supprimer une occurrence d'une série, avec trois portées :
  "one"       : cette occurrence seulement (exception, le reste ne bouge pas)
  "following" : cette occurrence et les suivantes (la série est coupée la veille, une nouvelle commence là)
  "all"       : toute la série

Le format 1 (avant la v3.9) est migré automatiquement, après une copie de sauvegarde dans data\backups\.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import re
import secrets
import shutil
import threading
import time
from pathlib import Path

import store

FORMAT = 2
REPEATS = ("none", "daily", "weekly", "monthly", "yearly")
REPEAT_LABELS = {"none": "Une fois", "daily": "Tous les jours", "weekly": "Toutes les semaines", "monthly": "Tous les mois", "yearly": "Tous les ans"}
SCOPES = ("one", "following", "all")
MAX_EVENTS = 3000
MAX_REMINDER_MIN = 28 * 24 * 60  # 4 semaines
MAX_DURATION_MIN = 14 * 24 * 60  # 2 semaines
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
BACKUP_DIR = store.DATA_DIR / "backups"

_lock = threading.RLock()


class AgendaError(ValueError):
    """Erreur lisible ; champs = {nom du champ: message} pour les afficher dans le formulaire."""

    def __init__(self, message: str, champs: dict | None = None) -> None:
        super().__init__(message)
        self.champs = champs or {}


# --------------------------------------------------------------------------- #
#  Dates
# --------------------------------------------------------------------------- #
def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _days_in(y: int, m: int) -> int:
    return (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day


def _base_occurs(e: dict, d: dt.date) -> bool:
    """La série tombe-t-elle ce jour-là ? (sans tenir compte des exceptions)"""
    start = parse_date(e["date"])
    if d < start:
        return False
    if e.get("until") and d > parse_date(e["until"]):
        return False
    r = e.get("repeat") or "none"
    if r == "none":
        return d == start
    if r == "daily":
        return True
    if r == "weekly":
        return d.weekday() == start.weekday()
    # 31 d'un mois de 30 jours / 29 février d'une année non bissextile : dernier jour du mois
    same_day = d.day == min(start.day, _days_in(d.year, d.month))
    if r == "monthly":
        return same_day
    if r == "yearly":
        return d.month == start.month and same_day
    return False


def _age(e: dict, d: dt.date) -> int | None:
    by = e.get("birth_year")
    if e.get("birthday") and by:
        a = d.year - int(by)
        return a if a > 0 else None
    return None


def occurrences(db: dict, start: dt.date, end: dt.date) -> list[dict]:
    """Toutes les occurrences entre start et end inclus, exceptions appliquées."""
    out = []
    span = (end - start).days
    for e in db.get("events", []):
        exc = e.get("exceptions") or {}
        keys = set()
        if (e.get("repeat") or "none") == "none":
            keys.add(parse_date(e["date"]))
        else:
            for i in range(span + 1):
                d = start + dt.timedelta(days=i)
                if _base_occurs(e, d):
                    keys.add(d)
        # occurrences déplacées depuis une date hors de la plage
        for k, x in exc.items():
            if x.get("date") and not x.get("cancelled"):
                try:
                    nd, kd = parse_date(x["date"]), parse_date(k)
                except ValueError:
                    continue
                if start <= nd <= end and _base_occurs(e, kd):
                    keys.add(kd)
        for k in keys:
            ks = k.isoformat()
            x = exc.get(ks) or {}
            if x.get("cancelled"):
                continue
            day = parse_date(x["date"]) if x.get("date") else k
            if not (start <= day <= end):
                continue
            o = {
                "id": f"{e['id']}@{ks}",
                "event_id": e["id"],
                "original_date": ks,
                "date": day.isoformat(),
                "time": x.get("time", e.get("time")) if not e.get("birthday") else None,
                "duration": x.get("duration", e.get("duration")),
                "title": x.get("title", e["title"]),
                "description": x.get("description", e.get("description", "")),
                "reminders": x.get("reminders", e.get("reminders")),
                "birthday": bool(e.get("birthday")),
                "age": _age(e, day),
                "birth_year": e.get("birth_year"),
                "repeat": e.get("repeat") or "none",
                "until": e.get("until"),
                "series_start": e["date"],
                "exception": bool(x),
                "seulement_nexus": bool(e.get("seulement_nexus")),
                "updated": max(e.get("updated") or 0, x.get("updated") or 0),
            }
            out.append(o)
    out.sort(key=lambda o: (o["date"], 0 if o["time"] is None else 1, o["time"] or "", o["title"].lower()))
    return out


def label(o: dict) -> str:
    if o["birthday"]:
        return f"🎂 {o['title']}" + (f" ({o['age']} an{'s' if o['age'] > 1 else ''})" if o.get("age") else "")
    return o["title"]


# --------------------------------------------------------------------------- #
#  Lecture, migration, sauvegarde
# --------------------------------------------------------------------------- #
def _backup(raw, reason: str) -> Path | None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"agenda-{reason}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    src = store.DATA_DIR / "agenda.json"
    if src.exists():
        shutil.copy2(src, path)
    else:
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def migrate(raw) -> tuple[dict, bool]:
    """Format 1 -> 2, sans rien perdre. Renvoie (données, migré ?)."""
    raw = raw if isinstance(raw, dict) else {}
    if raw.get("format") == FORMAT:
        raw.setdefault("events", [])
        raw.setdefault("todos", [])
        raw.setdefault("notes", [])
        return raw, False
    now = time.time()
    events = []
    for e in raw.get("events") or []:
        if not isinstance(e, dict) or not e.get("date"):
            continue
        birthday = bool(e.get("birthday"))
        exc = {d: {"cancelled": True} for d in (e.get("skip") or []) if isinstance(d, str) and DATE_RE.match(d)}
        ne = {
            "id": str(e.get("id") or secrets.token_hex(6)),
            "title": str(e.get("title") or "Sans titre")[:120],
            "date": e["date"],
            "time": None if birthday else (e.get("time") or None),  # anniversaire = journée entière
            "duration": None,
            "description": "",
            "repeat": "yearly" if birthday else (e.get("repeat") if e.get("repeat") in REPEATS else "none"),
            "until": e.get("until") or None,
            "birthday": birthday,
            "birth_year": e.get("birth_year") if birthday else None,
            "reminders": None,
            "exceptions": exc,
            "created": now,
            "updated": now,
        }
        if birthday and e.get("time"):
            ne["ancienne_heure"] = e["time"]  # gardée pour mémoire (format 1)
        events.append(ne)
    n_old = sum(1 for e in raw.get("events") or [] if isinstance(e, dict) and e.get("date"))
    if len(events) != n_old:
        raise RuntimeError("migration de l'agenda : nombre d'évènements différent, rien n'a été modifié")
    db = {"format": FORMAT, "events": events, "todos": raw.get("todos") or [], "notes": raw.get("notes") or []}
    return db, True


def load() -> dict:
    with _lock:
        raw = store.load("agenda", {})
        db, migrated = migrate(copy.deepcopy(raw))
        if migrated and (raw.get("events") or raw.get("todos") or raw.get("notes")):
            path = _backup(raw, "avant-format2")
            store.save("agenda", db)
            print(f"[Agenda] Données passées au format 2 ({len(db['events'])} évènement(s)) ; sauvegarde de l'ancien fichier : data\\backups\\{path.name}")
        return db


def save(db: dict) -> None:
    with _lock:
        db["format"] = FORMAT
        store.save("agenda", db)


# --------------------------------------------------------------------------- #
#  Validation
# --------------------------------------------------------------------------- #
ONE_FIELDS = ("title", "date", "time", "duration", "description", "reminders")


def validate(f: dict, base: dict | None = None) -> dict:
    """Vérifie les champs envoyés (partiels si base est fourni) et renvoie des valeurs propres."""
    if not isinstance(f, dict):
        raise AgendaError("données invalides")
    err: dict[str, str] = {}
    out: dict = {}
    full = base is None
    merged = {**(base or {}), **f}

    if "title" in f or full:
        t = str(f.get("title") or "").strip()
        if not t:
            err["title"] = "Le titre est obligatoire."
        elif len(t) > 120:
            err["title"] = "Titre trop long (120 caractères maximum)."
        out["title"] = t[:120]
    if "date" in f or full:
        d = str(f.get("date") or "")
        try:
            if not DATE_RE.match(d):
                raise ValueError
            parse_date(d)
            out["date"] = d
        except ValueError:
            err["date"] = "Date invalide (format attendu : jj/mm/aaaa)."
    if "time" in f or full:
        t = f.get("time")
        if t in (None, ""):
            out["time"] = None
        elif isinstance(t, str) and TIME_RE.match(t):
            out["time"] = t
        else:
            err["time"] = "Heure invalide (format HH:MM, ex. 14:30)."
    if "duration" in f or full:
        v = f.get("duration")
        if v in (None, "", 0, "0"):
            out["duration"] = None
        else:
            try:
                v = int(v)
                if v <= 0:
                    raise ValueError
                if v > MAX_DURATION_MIN:
                    err["duration"] = "Durée trop longue (2 semaines maximum)."
                out["duration"] = v
            except (TypeError, ValueError):
                err["duration"] = "La durée doit être un nombre de minutes positif."
    if "description" in f or full:
        s = str(f.get("description") or "")
        if len(s) > 2000:
            err["description"] = "Description trop longue (2000 caractères maximum)."
        out["description"] = s[:2000]
    if "repeat" in f or full:
        r = f.get("repeat") or "none"
        if r not in REPEATS:
            err["repeat"] = "Répétition inconnue."
        out["repeat"] = r
    if "until" in f or full:
        u = f.get("until") or None
        if u:
            try:
                if not DATE_RE.match(str(u)):
                    raise ValueError
                parse_date(u)
            except ValueError:
                err["until"] = "Date de fin invalide."
        out["until"] = u
    if "birthday" in f or full:
        out["birthday"] = bool(f.get("birthday"))
    if "birth_year" in f or full:
        by = f.get("birth_year")
        if by in (None, ""):
            out["birth_year"] = None
        else:
            try:
                by = int(by)
                if not 1900 <= by <= dt.date.today().year:
                    raise ValueError
                out["birth_year"] = by
            except (TypeError, ValueError):
                err["birth_year"] = f"Année de naissance invalide (entre 1900 et {dt.date.today().year})."
    if "reminders" in f or full:
        rem = f.get("reminders")
        if rem is None:
            out["reminders"] = None
        else:
            if isinstance(rem, str):
                rem = [x for x in re.split(r"[,; ]+", rem) if x]
            try:
                vals = sorted({int(x) for x in rem}, reverse=True)
                if len(vals) > 6 or any(v < 0 or v > MAX_REMINDER_MIN for v in vals):
                    raise ValueError
                out["reminders"] = vals
            except (TypeError, ValueError):
                err["reminders"] = "Rappels : jusqu'à 6 délais en minutes, entre 0 et 40320 (ex. 60, 30)."

    # règles entre champs
    birthday = out.get("birthday", merged.get("birthday"))
    if birthday:
        out["time"] = None
        out["duration"] = None
        out["repeat"] = "yearly"
    start = out.get("date", merged.get("date"))
    until = out.get("until", merged.get("until"))
    if start and until and "date" not in err and "until" not in err and until < start:
        err["until"] = "La date de fin doit être après la date de début."
    if err:
        raise AgendaError("Certains champs sont invalides : " + " ".join(err.values()), err)
    return out


# --------------------------------------------------------------------------- #
#  Opérations
# --------------------------------------------------------------------------- #
def _find(db: dict, eid: str) -> dict:
    for e in db["events"]:
        if e["id"] == eid:
            return e
    raise AgendaError("Évènement introuvable (il a peut-être été supprimé ailleurs).")


def _shift(d: str, days: int) -> str:
    return (parse_date(d) + dt.timedelta(days=days)).isoformat()


def _check_occ(e: dict, occ: str | None) -> str:
    if not occ or not DATE_RE.match(occ):
        raise AgendaError("Occurrence invalide.")
    if not _base_occurs(e, parse_date(occ)):
        raise AgendaError("Cette date ne fait pas partie de la série.")
    return occ


def create(fields: dict, seulement_nexus: bool = False) -> dict:
    """seulement_nexus : choix explicite « NEXUS (sur ce PC seulement) » (jamais envoyé dans Google Agenda)."""
    with _lock:
        db = load()
        if len(db["events"]) >= MAX_EVENTS:
            raise AgendaError(f"Trop d'évènements ({MAX_EVENTS} maximum).")
        f = validate(fields)
        now = time.time()
        e = {"id": secrets.token_hex(6), **f, "exceptions": {}, "created": now, "updated": now}
        if seulement_nexus:
            e["seulement_nexus"] = True
        if not e["birthday"]:
            e["birth_year"] = None
        db["events"].append(e)
        save(db)
        return e


def update(eid: str, fields: dict, occ: str | None = None, scope: str = "all") -> dict:
    """Modifie un évènement. Pour une série : scope = one / following / all, occ = date d'origine de l'occurrence."""
    with _lock:
        db = load()
        e = _find(db, eid)
        now = time.time()
        repeating = (e.get("repeat") or "none") != "none"
        if not repeating or scope not in SCOPES:
            scope = "all"
        if scope != "all" or "date" in fields:
            occ = _check_occ(e, occ) if (repeating and occ) else (occ or e["date"])
        if scope == "following" and occ == e["date"]:
            scope = "all"  # depuis la 1re occurrence : c'est toute la série

        if scope == "one":
            bad = [k for k in fields if k not in ONE_FIELDS]
            if bad:
                raise AgendaError(
                    "Pour une seule occurrence, on peut changer le titre, la date, l'heure, la durée, "
                    "la description et les rappels. Pour la répétition, choisis « toute la série » "
                    "ou « cette occurrence et les suivantes »."
                )
            f = validate(fields, base={**e, "date": occ})
            x = dict((e.get("exceptions") or {}).get(occ) or {})
            x.pop("cancelled", None)
            for k, v in f.items():
                if k in ONE_FIELDS:
                    if k == "date" and v == occ:
                        x.pop("date", None)
                    elif k != "date" and v == e.get(k):
                        x.pop(k, None)
                    else:
                        x[k] = v
            x["updated"] = now
            e.setdefault("exceptions", {})[occ] = x
            e["updated"] = now
            save(db)
            return e

        f = validate(fields, base=e)
        if scope == "all":
            if "date" in f and repeating and occ:
                delta = (parse_date(f["date"]) - parse_date(occ)).days  # on décale toute la série
                f["date"] = _shift(e["date"], delta)
                if delta:
                    e["exceptions"] = {_shift(k, delta): v for k, v in (e.get("exceptions") or {}).items()}
                    if e.get("until") and "until" not in f:
                        f["until"] = _shift(e["until"], delta)
            e.update(f)
            if not e.get("birthday"):
                e["birth_year"] = None
            if e.get("until") and e["until"] < e["date"]:
                raise AgendaError("La date de fin doit être après la date de début.", {"until": "Fin avant le début."})
            e["updated"] = now
            save(db)
            return e

        # scope == "following" : on coupe la série la veille de occ et on en crée une nouvelle
        new = copy.deepcopy(e)
        new["id"] = secrets.token_hex(6)
        new_start = f.get("date", occ)
        delta = (parse_date(new_start) - parse_date(occ)).days
        new.update({k: v for k, v in f.items() if k != "date"})
        new["date"] = new_start
        new["exceptions"] = {_shift(k, delta): v for k, v in (e.get("exceptions") or {}).items() if k >= occ and v.get("cancelled")}
        if "until" not in f:
            new["until"] = _shift(e["until"], delta) if e.get("until") else None
        if new.get("until") and new["until"] < new["date"]:
            raise AgendaError("La date de fin doit être après la date de début.", {"until": "Fin avant le début."})
        if not new.get("birthday"):
            new["birth_year"] = None
        new["created"] = new["updated"] = now
        e["until"] = _shift(occ, -1)
        e["exceptions"] = {k: v for k, v in (e.get("exceptions") or {}).items() if k < occ}
        e["updated"] = now
        db["events"].append(new)
        save(db)
        return new


def delete(eid: str, occ: str | None = None, scope: str = "all") -> None:
    with _lock:
        db = load()
        e = _find(db, eid)
        repeating = (e.get("repeat") or "none") != "none"
        if not repeating or scope not in SCOPES or (scope == "following" and occ == e["date"]):
            scope = "all"
        if scope == "all":
            db["events"] = [x for x in db["events"] if x["id"] != eid]
        else:
            occ = _check_occ(e, occ)
            if scope == "one":
                e.setdefault("exceptions", {})[occ] = {"cancelled": True, "updated": time.time()}
            else:
                e["until"] = _shift(occ, -1)
                e["exceptions"] = {k: v for k, v in (e.get("exceptions") or {}).items() if k < occ}
            e["updated"] = time.time()
        save(db)


def retirer_envoye(eid: str, updated) -> bool:
    """Retire un évènement envoyé dans Google Agenda (agenda_google.py), seulement s'il n'a pas changé depuis
    l'envoi (sinon il reste, et son nouvel état repart au prochain envoi). Renvoie True s'il a été retiré."""
    with _lock:
        db = load()
        reste = [e for e in db["events"] if not (e["id"] == eid and e.get("updated") == updated)]
        if len(reste) == len(db["events"]):
            return False
        db["events"] = reste
        save(db)
        return True


def save_notebook(todos, notes) -> None:
    """To-do et notes (enregistrés par le navigateur), sans toucher aux évènements."""
    if not isinstance(todos, list) or not isinstance(notes, list):
        raise AgendaError("données invalides")
    with _lock:
        db = load()
        db["todos"], db["notes"] = todos, notes
        save(db)
