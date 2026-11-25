r"""Journal quotidien : une entrée par jour (humeur, activités, texte libre), base SQLite locale.

- Humeurs : liste fixe d'émojis (MOODS). Activités : liste modifiable dans config.json (section « journal »).
- Option « verrou » : le Journal demande le mot de passe du panel (celui du stream deck) même si la session
  est ouverte ; il se reverrouille après LOCK_IDLE sans activité (jeton en mémoire, cookie HttpOnly).
- Export texte ou Markdown, téléchargé par l'utilisateur uniquement (jamais envoyé ailleurs, jamais lu par le bot).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import secrets
import threading
import time

import config
import db

MOODS = [("😄", "Super"), ("🙂", "Bien"), ("😐", "Bof"), ("😕", "Pas top"), ("😢", "Triste"), ("😡", "En colère"), ("😴", "Fatigué"), ("🤒", "Malade")]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_TEXT = 50_000
LOCK_IDLE = 15 * 60
COOKIE = "nexus_journal"

_tokens: dict[str, float] = {}  # empreinte du jeton -> dernière activité
_tlock = threading.Lock()


class JournalError(ValueError):
    pass


def activities() -> list[dict]:
    raw = config.get("journal").get("activites") or []
    out = []
    for a in raw[:20]:
        if isinstance(a, dict) and a.get("emoji"):
            out.append({"emoji": str(a["emoji"])[:8], "nom": str(a.get("nom") or "")[:30]})
        elif isinstance(a, str) and a:
            out.append({"emoji": a[:8], "nom": ""})
    return out


def _day(day: str) -> str:
    try:
        if not DATE_RE.match(day or ""):
            raise ValueError
        dt.date.fromisoformat(day)
    except ValueError:
        raise JournalError("date invalide")
    return day


def _entry(r) -> dict:
    return {"jour": r["jour"], "humeur": r["humeur"], "activites": json.loads(r["activites"] or "[]"), "texte": r["texte"], "modifie": r["modifie"]}


def get(day: str) -> dict:
    day = _day(day)
    r = db.conn().execute("SELECT * FROM journal WHERE jour = ?", (day,)).fetchone()
    return _entry(r) if r else {"jour": day, "humeur": "", "activites": [], "texte": "", "modifie": None}


def save(day: str, humeur: str, acts: list, texte: str) -> dict:
    day = _day(day)
    moods = {m for m, _ in MOODS}
    if humeur and humeur not in moods:
        raise JournalError("humeur inconnue")
    allowed = {a["emoji"] for a in activities()}
    acts = [a for a in (acts or []) if isinstance(a, str) and a in allowed][:20]
    texte = str(texte or "")
    if len(texte) > MAX_TEXT:
        raise JournalError(f"texte trop long ({MAX_TEXT} caractères maximum)")
    c = db.conn()
    if not humeur and not acts and not texte.strip():
        c.execute("DELETE FROM journal WHERE jour = ?", (day,))  # entrée vidée : on n'en garde pas de trace
    else:
        c.execute(
            """INSERT INTO journal(jour, humeur, activites, texte, modifie) VALUES(?,?,?,?,?)
                     ON CONFLICT(jour) DO UPDATE SET humeur = excluded.humeur, activites = excluded.activites,
                     texte = excluded.texte, modifie = excluded.modifie""",
            (day, humeur, json.dumps(acts, ensure_ascii=False), texte, time.time()),
        )
    return get(day)


def month(m: str) -> dict[str, dict]:
    if not re.match(r"^\d{4}-\d{2}$", m or ""):
        raise JournalError("mois invalide")
    return {
        r["jour"]: {"humeur": r["humeur"], "rempli": True, "activites": json.loads(r["activites"] or "[]")}
        for r in db.conn().execute("SELECT jour, humeur, activites FROM journal WHERE jour LIKE ?", (m + "-%",))
    }


def search(q: str) -> list[dict]:
    q = (q or "").strip()
    if len(q) < 2:
        return []
    like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    out = []
    for r in db.conn().execute("SELECT * FROM journal WHERE texte LIKE ? ESCAPE '\\' ORDER BY jour DESC LIMIT 50", (like,)):
        t = r["texte"]
        i = t.lower().find(q.lower())
        start = max(0, i - 50)
        out.append(
            {
                "jour": r["jour"],
                "humeur": r["humeur"],
                "extrait": ("…" if start else "") + t[start : i + len(q) + 80] + ("…" if i + len(q) + 80 < len(t) else ""),
            }
        )
    return out


def export(fmt: str) -> tuple[str, str]:
    acts = {a["emoji"]: a["nom"] for a in activities()}
    names = dict(MOODS)
    rows = list(db.conn().execute("SELECT * FROM journal ORDER BY jour"))
    md = fmt == "md"
    lines = ["# Journal NEXUS" if md else "JOURNAL NEXUS", ""]
    for r in rows:
        e = _entry(r)
        d = dt.date.fromisoformat(e["jour"])
        title = d.strftime("%d/%m/%Y")
        lines.append(f"## {title}" if md else f"=== {title} ===")
        if e["humeur"]:
            lines.append(f"Humeur : {e['humeur']} {names.get(e['humeur'], '')}".rstrip())
        if e["activites"]:
            lines.append("Activités : " + ", ".join(f"{a} {acts.get(a, '')}".strip() for a in e["activites"]))
        if e["texte"].strip():
            lines.append("")
            lines.append(e["texte"].rstrip())
        lines.append("")
    return ("journal-nexus.md" if md else "journal-nexus.txt"), "\n".join(lines)


def summary(day: str) -> dict:
    e = get(day)
    n = db.conn().execute("SELECT COUNT(*) FROM journal").fetchone()[0]
    return {"humeur": e["humeur"], "ecrit": bool(e["texte"].strip()), "jours": n}


# --------------------------------------------------------------------------- #
#  Verrou (mot de passe du panel = celui du stream deck)
# --------------------------------------------------------------------------- #
def lock_enabled() -> bool:
    return bool(db.get_setting("journal_verrou", False))


def unlocked(token: str | None) -> bool:
    if not lock_enabled():
        return True
    if not token:
        return False
    h = hashlib.sha256(token.encode()).hexdigest()
    now = time.time()
    with _tlock:
        last = _tokens.get(h)
        if last and now - last < LOCK_IDLE:
            _tokens[h] = now  # chaque action prolonge le déverrouillage
            return True
        _tokens.pop(h, None)
    return False


def unlock(password: str, verify) -> str | None:
    if not verify(password):
        return None
    token = secrets.token_urlsafe(32)
    with _tlock:
        _tokens[hashlib.sha256(token.encode()).hexdigest()] = time.time()
    return token


def relock() -> None:
    with _tlock:
        _tokens.clear()
