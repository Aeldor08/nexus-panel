"""Minuteur Pomodoro / mode focus (état sur le serveur : le même sur le PC et le téléphone).

Cycle : travail (25 min par défaut) → pause courte (5 min), et toutes les N séances une pause longue (15 min).
Pendant une phase de TRAVAIL, le temps compte dans la catégorie « travail » des statistiques personnelles
(statistiques.py). La page applique un profil sobre pendant la session si l'option est cochée (js/focus.js).
État gardé dans data/focus.json : un redémarrage du panel ne perd pas la séance en cours.
"""

from __future__ import annotations

import json
import threading
import time

import store

FICHIER = store.DATA_DIR / "focus.json"
DEFAUT = {"travail_min": 25, "pause_min": 5, "longue_min": 15, "cycles": 4, "profil_sobre": True}
LIMITES = {"travail_min": (5, 180), "pause_min": (1, 60), "longue_min": (1, 90), "cycles": (1, 12)}


class Focus:
    def __init__(self, journal=None) -> None:
        self.journal = journal or (lambda *a, **k: None)  # activite.noter
        self._lock = threading.Lock()
        try:
            self.e = json.loads(FICHIER.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.e = {}
        self.e = {"reglages": {**DEFAUT, **(self.e.get("reglages") or {})}, "session": self.e.get("session")}

    def _sauver(self) -> None:
        try:
            FICHIER.parent.mkdir(parents=True, exist_ok=True)
            tmp = FICHIER.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.e, ensure_ascii=False), encoding="utf-8")
            tmp.replace(FICHIER)
        except OSError:
            pass

    # -- phases ----------------------------------------------------------------
    def _duree(self, phase: str) -> float:
        r = self.e["reglages"]
        return 60 * float(r["travail_min"] if phase == "travail" else r["longue_min"] if phase == "longue" else r["pause_min"])

    def _avancer(self, now: float) -> None:
        s = self.e["session"]
        if not s or s.get("suspendu"):
            return
        change = False
        while now >= s["fin"]:
            debut = s["fin"]
            if s["phase"] == "travail":
                s["travail_s"] += self._duree("travail")
                s["seances"] += 1
                s["phase"] = "longue" if s["seances"] % int(self.e["reglages"]["cycles"]) == 0 else "pause"
            else:
                s["phase"] = "travail"
            s["fin"] = debut + self._duree(s["phase"])
            s["changement"] = debut  # la page joue un son / affiche un message
            change = True
        if change:
            self._sauver()

    def etat(self) -> dict:
        now = time.time()
        with self._lock:
            self._avancer(now)
            s = self.e["session"]
            out = {"reglages": dict(self.e["reglages"]), "actif": bool(s), "maintenant": now}
            if s:
                reste = s["reste"] if s.get("suspendu") else max(0.0, s["fin"] - now)
                cours = 0.0 if s["phase"] != "travail" else self._duree("travail") - reste
                out.update(
                    phase=s["phase"],
                    suspendu=bool(s.get("suspendu")),
                    reste_s=round(reste, 1),
                    duree_s=self._duree(s["phase"]),
                    seances=s["seances"],
                    debut=s["debut"],
                    changement=s.get("changement"),
                    travail_s=round(s["travail_s"] + cours),
                )
            return out

    def en_travail(self) -> bool:
        """Phase de travail en cours (non suspendue) : utilisé par les statistiques."""
        e = self.etat()
        return e["actif"] and e.get("phase") == "travail" and not e.get("suspendu")

    # -- actions ---------------------------------------------------------------
    def demarrer(self, reglages: dict | None = None) -> dict:
        if reglages:
            self.regler(reglages)
        now = time.time()
        with self._lock:
            self.e["session"] = {
                "phase": "travail",
                "debut": now,
                "fin": now + self._duree("travail"),
                "seances": 0,
                "travail_s": 0.0,
                "suspendu": False,
                "reste": None,
                "changement": None,
            }
            self._sauver()
        r = self.e["reglages"]
        self.journal("focus", "session démarrée", "ok", f"{r['travail_min']} min / {r['pause_min']} min")
        return self.etat()

    def suspendre(self) -> dict:
        with self._lock:
            self._avancer(time.time())
            s = self.e["session"]
            if s and not s.get("suspendu"):
                s["suspendu"], s["reste"] = True, max(0.0, s["fin"] - time.time())
                self._sauver()
        return self.etat()

    def reprendre(self) -> dict:
        with self._lock:
            s = self.e["session"]
            if s and s.get("suspendu"):
                s["fin"], s["suspendu"], s["reste"] = time.time() + float(s["reste"] or 0), False, None
                self._sauver()
        return self.etat()

    def passer(self) -> dict:
        """Passe directement à la phase suivante (fin de la séance ou de la pause)."""
        with self._lock:
            s = self.e["session"]
            if s:
                if s.get("suspendu"):
                    s["suspendu"], s["reste"] = False, None
                if s["phase"] == "travail":  # séance écourtée : seul le temps fait compte
                    s["travail_s"] += max(0.0, self._duree("travail") - max(0.0, s["fin"] - time.time())) - self._duree("travail")
                s["fin"] = time.time()
        return self.etat()

    def arreter(self) -> dict:
        e = self.etat()
        with self._lock:
            self.e["session"] = None
            self._sauver()
        if e["actif"]:
            self.journal("focus", "session terminée", "ok", f"{e['seances']} séance(s), {round(e['travail_s'] / 60)} min de travail")
        return self.etat()

    def regler(self, changes: dict) -> dict:
        with self._lock:
            r = self.e["reglages"]
            for k, (lo, hi) in LIMITES.items():
                if k in changes:
                    try:
                        r[k] = max(lo, min(hi, int(float(changes[k]))))
                    except (TypeError, ValueError):
                        pass
            if "profil_sobre" in changes:
                r["profil_sobre"] = bool(changes["profil_sobre"])
            self._sauver()
        return self.etat()
