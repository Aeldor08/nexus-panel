"""Journal fichier de NEXUS : double la console (stdout/stderr) vers logs/nexus.log.

Utile quand l'application est lancée sans console (version installée, fenêtre native) :
les messages de démarrage, les erreurs et les traces restent consultables. Le fichier est
roulé à 5 Mo (nexus.log.1) pour ne pas grossir indéfiniment.

`install()` est appelé au démarrage, avant `sante.install()` qui double ensuite ce flux
pour la fenêtre « Santé ».
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paths

MAX_BYTES = 5 * 1024 * 1024
_installed = False


class Tee:
    """Écrit dans plusieurs flux ; ne lève jamais d'erreur d'écriture."""

    def __init__(self, *streams) -> None:
        self.streams = streams

    def write(self, text) -> int:
        for stream in self.streams:
            if stream is None:
                continue
            try:
                stream.write(text)
            except Exception:
                pass
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            if stream is None:
                continue
            try:
                stream.flush()
            except Exception:
                pass

    def __getattr__(self, name):
        for stream in self.streams:
            if stream is not None and hasattr(stream, name):
                return getattr(stream, name)
        raise AttributeError(name)


def _rotate() -> None:
    try:
        if paths.LOG_FILE.exists() and paths.LOG_FILE.stat().st_size > MAX_BYTES:
            backup = paths.LOG_FILE.with_name(paths.LOG_FILE.name + ".1")
            backup.unlink(missing_ok=True)
            paths.LOG_FILE.replace(backup)
    except OSError:
        pass


def install() -> Path | None:
    """Installe le double flux vers logs/nexus.log ; renvoie le chemin du journal."""
    global _installed
    if _installed:
        return paths.LOG_FILE
    try:
        paths.LOG_DIR.mkdir(parents=True, exist_ok=True)
        _rotate()
        handle = open(paths.LOG_FILE, "a", encoding="utf-8", buffering=1)
    except OSError:
        return None
    handle.write(f"\n===== NEXUS {time.strftime('%Y-%m-%d %H:%M:%S')} (pid {os.getpid()}) =====\n")
    sys.stdout = Tee(sys.stdout, handle)
    sys.stderr = Tee(sys.stderr, handle)
    _installed = True
    return paths.LOG_FILE
