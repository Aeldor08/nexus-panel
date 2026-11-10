"""Santé de NEXUS : collecte des dernières erreurs et avertissements du serveur (mémoire seulement).

install() (appelé au démarrage) :
- double les sorties console (stdout / stderr) : chaque ligne d'avertissement, d'erreur ou de trace Python
  (« Traceback ») est aussi gardée ici, la console reste identique ;
- capte les exceptions non rattrapées (fil principal et fils secondaires) ;
- capte les journaux « logging » de niveau WARNING et plus (uvicorn, bibliothèques).
Les 80 dernières sont affichées dans la fenêtre « Santé de NEXUS ».
"""
from __future__ import annotations

import collections
import logging
import re
import sys
import threading
import time
import traceback

ERREURS: collections.deque = collections.deque(maxlen=80)
_lock = threading.Lock()
_MOTIF = re.compile(r"\b(ERREUR|ERROR|AVERTISSEMENT|WARNING|CRITICAL|Exception|Error)\b|\" 5\d\d\b")
_installe = False


def noter(source: str, message: str, niveau: str = "erreur") -> None:
    message = str(message).strip()
    if not message:
        return
    with _lock:
        if ERREURS and ERREURS[-1]["message"] == message[:500]:       # même message répété : compteur
            ERREURS[-1]["n"] += 1
            ERREURS[-1]["t"] = time.time()
            return
        ERREURS.append({"t": time.time(), "source": source, "niveau": niveau, "message": message[:500], "n": 1})


def liste() -> list[dict]:
    with _lock:
        return list(reversed(ERREURS))


def _niveau(ligne: str) -> str:
    return "avertissement" if re.search(r"AVERTISSEMENT|WARNING", ligne) else "erreur"


class _Double:
    """Flux console doublé : écrit normalement ET garde les lignes d'erreur (une trace = un seul évènement)."""

    def __init__(self, flux, source: str) -> None:
        self._flux, self._source = flux, source
        self._reste = ""
        self._trace: list[str] | None = None

    def write(self, s):
        n = self._flux.write(s) if self._flux else len(s)
        try:
            self._reste += s
            while "\n" in self._reste:
                ligne, self._reste = self._reste.split("\n", 1)
                self._ligne(ligne.rstrip("\r"))
        except Exception:
            pass
        return n

    def _ligne(self, ligne: str) -> None:
        if self._trace is not None:
            if ligne.startswith((" ", "\t")) or not ligne.strip():
                self._trace.append(ligne)
                return
            noter(self._source, f"{ligne}  (trace : {self._trace[-2].strip() if len(self._trace) > 1 else ''})")
            self._trace = None
            return
        if ligne.startswith("Traceback (most recent call last)"):
            self._trace = [ligne]
        elif _MOTIF.search(ligne):
            noter(self._source, ligne, _niveau(ligne))

    def flush(self):
        if self._flux:
            self._flux.flush()

    def __getattr__(self, nom):
        return getattr(self._flux, nom)


class _Gestionnaire(logging.Handler):
    def emit(self, record):
        try:
            msg = record.getMessage()
            if record.exc_info:
                msg += " — " + "".join(traceback.format_exception_only(*record.exc_info[:2])).strip()
            noter(record.name, msg, "avertissement" if record.levelno < logging.ERROR else "erreur")
        except Exception:
            pass


def install() -> None:
    global _installe
    if _installe:
        return
    _installe = True
    sys.stdout = _Double(sys.stdout, "console")
    sys.stderr = _Double(sys.stderr, "console")
    g = _Gestionnaire(level=logging.WARNING)
    for nom in ("", "uvicorn", "uvicorn.error", "asyncio"):
        logging.getLogger(nom).addHandler(g)

    ancien = sys.excepthook

    def crochet(t, v, tb):
        noter("python", "".join(traceback.format_exception_only(t, v)).strip())
        ancien(t, v, tb)
    sys.excepthook = crochet

    ancien_fil = threading.excepthook

    def crochet_fil(args):
        noter(f"fil {args.thread.name if args.thread else '?'}",
              "".join(traceback.format_exception_only(args.exc_type, args.exc_value)).strip())
        ancien_fil(args)
    threading.excepthook = crochet_fil
