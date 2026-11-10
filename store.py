"""Petit stockage JSON local (dossier data/) pour l'agenda, les horloges, le lanceur..."""

from __future__ import annotations

import json
import threading
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
# Clés autorisées : rien d'autre ne peut être écrit sur le disque.
KEYS = {"agenda", "clocks", "launcher", "devices", "speedtests", "gamemode", "remote"}
MAX_BYTES = 2 * 1024 * 1024

_lock = threading.Lock()


def _path(key: str) -> Path:
    if key not in KEYS:
        raise KeyError(key)
    return DATA_DIR / f"{key}.json"


def load(key: str, default=None):
    try:
        return json.loads(_path(key).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save(key: str, value) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=1)
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("données trop volumineuses")
    path = _path(key)
    with _lock:
        DATA_DIR.mkdir(exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
