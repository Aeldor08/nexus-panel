r"""Rappels de l'agenda, calculés par le serveur (même quand aucune page n'est ouverte).

- Chaque occurrence a des rappels X minutes avant son début : ceux de l'évènement, sinon ceux de
  config.json (agenda.rappels_minutes, par défaut [60, 30]).
- Journée entière et anniversaires : le « début » est l'heure de référence (agenda.heure_reference, 09:00).
- Chaque rappel a une clé (occurrence + heure de début + délai) enregistrée dans data\rappels.json une fois
  envoyé : un redémarrage ne renvoie jamais un rappel en double, et ceux à venir partent à l'heure.
- Si une occurrence change d'heure (ou est supprimée), sa clé change : les anciens rappels ne partent plus
  et les nouveaux sont recalculés.
- Rappel dont l'heure est passée avant que l'évènement soit créé ou modifié : jamais envoyé
  (« seulement les rappels encore possibles »).
- NEXUS éteint au moment d'un rappel : au redémarrage, seul le plus récent rappel manqué est envoyé,
  et seulement si l'évènement n'a pas encore commencé.
- Évènements de Google Agenda (agenda_google.py, si relié et si « rappels » est activé) : leurs propres rappels
  (ceux de l'évènement, sinon ceux par défaut de l'agenda Google), lus dans la copie locale.
- Envoi : dans le panel (liste lue par les navigateurs) et sur Discord si le bot est configuré
  (nouvel essai tant que l'évènement n'a pas commencé si le bot est momentanément hors ligne).
"""

from __future__ import annotations

import datetime as dt
import json
import threading
import time
from collections.abc import Callable

import agenda
import agenda_google
import config
import store

STATE_FILE = store.DATA_DIR / "rappels.json"
TICK_SECONDS = 15
KEEP_SECONDS = 3 * 86400  # on oublie les rappels de plus de 3 jours
FIRED_KEEP = 40  # derniers rappels gardés pour le panel
START_GRACE = 60  # un rappel « 0 min avant » part encore jusqu'à 1 min après le début


def settings() -> tuple[list[int], str, bool]:
    cfg = config.get("agenda")
    try:
        mins = sorted({int(x) for x in cfg.get("rappels_minutes", [60, 30]) if 0 <= int(x) <= agenda.MAX_REMINDER_MIN}, reverse=True)
    except (TypeError, ValueError):
        mins = [60, 30]
    ref = str(cfg.get("heure_reference") or "09:00")
    if not agenda.TIME_RE.match(ref):
        ref = "09:00"
    return mins, ref, bool(cfg.get("rappels_discord", True))


def occurrence_start(o: dict, ref: str) -> dt.datetime:
    hh, mm = (o["time"] or ref).split(":")
    d = agenda.parse_date(o["date"])
    return dt.datetime(d.year, d.month, d.day, int(hh), int(mm))


def _in_words(minutes: int) -> str:
    if minutes <= 0:
        return "maintenant"
    if minutes < 60:
        return f"dans {minutes} min"
    h, m = divmod(minutes, 60)
    if h < 24:
        return f"dans {h} h" + (f" {m:02d}" if m else "")
    d = round(minutes / 1440)
    return f"dans {d} jour{'s' if d > 1 else ''}"


def message(o: dict, start: dt.datetime, now: dt.datetime) -> tuple[str, str]:
    """(titre, texte) du rappel."""
    remaining = max(0, round((start - now).total_seconds() / 60))
    day = agenda.parse_date(o["date"])
    when_day = "aujourd'hui" if day == now.date() else ("demain" if day == now.date() + dt.timedelta(days=1) else day.strftime("le %d/%m"))
    if o["birthday"]:
        age = f" ({o['age']} an{'s' if o['age'] > 1 else ''})" if o.get("age") else ""
        return "🎂 Anniversaire", f"Anniversaire de {o['title']}{age} {when_day}"
    if not o["time"]:
        return "📅 Rappel", f"{o['title']} — {when_day}, toute la journée"
    dur = f" (durée {o['duration']} min)" if o.get("duration") else ""
    return f"⏰ Rappel — {_in_words(remaining)}", f"{o['title']} — {when_day} à {o['time']}{dur}"


class ReminderService:
    def __init__(self, notifier: Callable[[str, str], bool | None] | None = None) -> None:
        self.notifier = notifier  # envoi Discord : True envoyé, False à réessayer, None pas de bot
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self.state = self._load()

    # -- état sur disque ---------------------------------------------------------
    def _load(self) -> dict:
        try:
            s = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(s, dict):
                return {"seen": s.get("seen") or {}, "sent": s.get("sent") or {}, "fired": s.get("fired") or [], "discord": s.get("discord") or {}}
        except (OSError, ValueError):
            pass
        return {"seen": {}, "sent": {}, "fired": [], "discord": {}}

    def _save(self) -> None:
        store.DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(STATE_FILE)

    # -- calcul ----------------------------------------------------------------------
    def tick(self, now: dt.datetime | None = None) -> list[dict]:
        """Une passe : envoie les rappels dus. Renvoie ceux envoyés (pour les tests)."""
        now = now or dt.datetime.now()
        now_ts = now.timestamp()
        defaults, ref, use_discord = settings()
        db = agenda.load()
        max_off = max([*defaults, *[max(e.get("reminders") or [0]) for e in db["events"]], 0])
        debut = (now - dt.timedelta(days=1)).date()
        occs = agenda.occurrences(db, debut, (now + dt.timedelta(minutes=max_off, days=2)).date())
        # copie locale de Google Agenda (jamais de réseau ici), jusqu'au plus long rappel possible (4 semaines)
        occs += agenda_google.occurrences_rappels(debut, (now + dt.timedelta(minutes=agenda.MAX_REMINDER_MIN, days=2)).date())
        fired = []
        with self._lock:
            seen, sent = self.state["seen"], self.state["sent"]
            for o in occs:
                start = occurrence_start(o, ref)
                if start.timestamp() + START_GRACE < now_ts:
                    continue  # déjà commencé
                offsets = o["reminders"] if o["reminders"] is not None else defaults
                if not offsets:
                    continue
                occ_key = f"{o['id']}|{start.isoformat(timespec='minutes')}"
                # 1re fois qu'on voit cette occurrence à cette heure : au plus tôt la dernière modification
                first = seen.get(occ_key)
                if first is None:
                    first = min(now_ts, o.get("updated") or now_ts)
                    seen[occ_key] = first
                due = []
                for off in sorted(set(offsets), reverse=True):
                    key = f"{occ_key}#{off}"
                    if key in sent:
                        continue
                    at = start - dt.timedelta(minutes=off)
                    if at.timestamp() > now_ts:
                        continue  # pas encore l'heure
                    if at.timestamp() < first - 30:
                        sent[key] = {"t": now_ts, "etat": "trop tard (créé ou modifié après l'heure du rappel)"}
                        continue
                    due.append((at, off, key))
                if not due:
                    continue
                due.sort()
                for _, _, key in due[:-1]:  # NEXUS éteint : seul le plus récent part
                    sent[key] = {"t": now_ts, "etat": "remplacé par un rappel plus récent"}
                at, off, key = due[-1]
                title, text = message(o, start, now)
                item = {
                    "id": key,
                    "titre": title,
                    "texte": text,
                    "occurrence": o["id"],
                    "date": o["date"],
                    "heure": o["time"],
                    "debut": start.isoformat(timespec="minutes"),
                    "delai": off,
                    "anniversaire": o["birthday"],
                    "envoye": now_ts,
                    "en_retard": (now - at).total_seconds() > 2 * TICK_SECONDS + 5,
                }
                sent[key] = {"t": now_ts, "etat": "envoyé"}
                self.state["fired"].append(item)
                if use_discord and self.notifier:
                    self.state["discord"][key] = {"titre": title, "texte": text, "fin": start.timestamp() + START_GRACE}
                fired.append(item)
            self._flush_discord(now_ts)
            self._prune(now_ts)
            self._save()
        return fired

    def _flush_discord(self, now_ts: float) -> None:
        for key, m in list(self.state["discord"].items()):
            if m["fin"] < now_ts:
                del self.state["discord"][key]  # trop tard : on abandonne
                continue
            try:
                ok = self.notifier(m["titre"], m["texte"]) if self.notifier else None
            except Exception as exc:
                print(f"[Rappels] envoi Discord impossible : {exc}")
                ok = False
            if ok is None or ok:  # envoyé, ou pas de bot : rien à réessayer
                del self.state["discord"][key]

    def _prune(self, now_ts: float) -> None:
        old = now_ts - KEEP_SECONDS
        self.state["seen"] = {k: v for k, v in self.state["seen"].items() if v >= old}
        self.state["sent"] = {k: v for k, v in self.state["sent"].items() if v.get("t", 0) >= old}
        self.state["fired"] = self.state["fired"][-FIRED_KEEP:]

    # -- pour le panel -------------------------------------------------------------
    def recent(self, seconds: int = 2 * 3600) -> list[dict]:
        limit = time.time() - seconds
        with self._lock:
            return [f for f in self.state["fired"] if f["envoye"] >= limit]

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def loop():
            while not self._stop.is_set():
                try:
                    self.tick()
                except Exception as exc:  # un agenda illisible ne doit pas arrêter le serveur
                    print(f"[Rappels] erreur : {exc}")
                self._stop.wait(TICK_SECONDS)

        self._thread = threading.Thread(target=loop, daemon=True, name="rappels")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
