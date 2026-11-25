"""Mode jeu : détecte un jeu en cours, allège le panel, et (si l'utilisateur l'active)
bascule le plan d'alimentation Windows entre « jeu » et « normal »."""

from __future__ import annotations

import re
import subprocess
import threading
import time

import psutil

import logs
import store

CREATE_NO_WINDOW = 0x08000000
CHECK_INTERVAL = 3       # s entre deux détections
EXIT_DELAY = 20          # s sans jeu avant de quitter le mode jeu (évite les allers-retours)

# Dossiers de jeux (comparaison en minuscules, sur le chemin de l'exécutable)
GAME_DIRS = ("\\steamapps\\common\\", "\\rockstar games\\", "\\xboxgames\\", "\\epic games\\",
             "\\riot games\\valorant\\", "\\riot games\\league of legends\\", "\\ea games\\",
             "\\ubisoft game launcher\\games\\", "\\battle.net\\", "\\gog galaxy\\games\\")
# Exécutables de jeux connus, utiles quand le chemin est illisible (anti-triche)
GAME_NAMES = re.compile(r"^(valorant-win64-shipping|rdr2|gta5|gta5_enhanced|redm_.*process|fivem_.*process|"
                        r"leagueoflegends|league of legends|cs2|fortniteclient-win64-shipping|"
                        r"r5apex|overwatch|cod|eldenring|minecraft\.windows|javaw-minecraft)\.exe$", re.I)
# Jamais considérés comme des jeux : lanceurs, outils, assistants
# (« overlay » : surcouches des plateformes, jamais des jeux : EOSOverlayRenderer d'Epic, gameoverlayui de Steam,
#  surcouches NVIDIA / Discord / Xbox…, souvent installées dans un dossier de jeux)
NOT_GAMES = re.compile(r"(launcher|crash|report|helper|updater|setup|install|redist|easyanticheat|eac|"
                       r"battleye|vanguard|unitycrashhandler|steamerrorreporter|epicwebhelper|"
                       r"riotclient|riot client|socialclub|cefprocess|webhelper|overlay)", re.I)
DEFAULT_IGNORE = ["wallpaper64.exe", "wallpaper32.exe", "LosslessScaling.exe", "webwallpaper32.exe"]
KNOWN_GUIDS = {"8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "performance",
               "381b4222-f694-41f0-9685-ff5bb260df2e": "balanced",
               "a1841308-3541-4fab-bc81-f71556f20b4a": "saver"}


def power_plans() -> tuple[list[dict], str | None]:
    """Plans d'alimentation disponibles et GUID actif (lecture seule)."""
    try:
        out = subprocess.run(["powercfg", "/list"], capture_output=True, text=True, timeout=10,
                             creationflags=CREATE_NO_WINDOW, encoding="oem", errors="replace").stdout
    except Exception:
        return [], None
    plans, active = [], None
    for m in re.finditer(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s+\((.+?)\)\s*(\*)?",
                         out, re.I):
        guid, name, star = m.group(1).lower(), m.group(2).strip(), m.group(3)
        plans.append({"guid": guid, "name": name, "kind": KNOWN_GUIDS.get(guid)})
        if star:
            active = guid
    return plans, active


def set_power_plan(guid: str) -> bool:
    if not re.fullmatch(r"[0-9a-f-]{36}", guid):
        return False
    try:
        r = subprocess.run(["powercfg", "/setactive", guid], capture_output=True, timeout=10,
                           creationflags=CREATE_NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


class GameMode:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.in_game = False
        self.game = None
        self.since = None
        self._last_seen = 0.0
        self.last_switch = None     # {"time", "plan", "ok"}
        self.cfg = self._load()
        threading.Thread(target=self._loop, daemon=True).start()

    # -- configuration (data/gamemode.json) -------------------------------------
    @staticmethod
    def _load() -> dict:
        cfg = store.load("gamemode") or {}
        cfg.setdefault("enabled", True)              # mode jeu actif (bouton « Désactiver le mode jeu »)
        cfg.setdefault("power_enabled", False)       # désactivé tant que l'utilisateur ne l'active pas
        cfg.setdefault("game_plan", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")
        cfg.setdefault("normal_plan", "381b4222-f694-41f0-9685-ff5bb260df2e")
        cfg.setdefault("extra_games", [])
        cfg.setdefault("ignore", list(DEFAULT_IGNORE))
        return cfg

    @property
    def active(self) -> bool:
        """Mode jeu en vigueur : un jeu est détecté ET le mode jeu n'est pas désactivé par l'utilisateur.
        (La détection, elle, continue : les statistiques comptent toujours le temps de jeu.)"""
        return self.in_game and self.cfg["enabled"]

    def update_config(self, changes: dict) -> dict:
        switch_to = None
        with self._lock:
            was = self.active
            for key in ("enabled", "power_enabled"):
                if key in changes:
                    self.cfg[key] = bool(changes[key])
            # (dés)activé pendant une partie : le plan d'alimentation suit aussitôt, comme à l'entrée / sortie d'un jeu
            if self.cfg["power_enabled"] and was != self.active:
                switch_to = self.cfg["game_plan"] if self.active else self.cfg["normal_plan"]
            for key in ("game_plan", "normal_plan"):
                if key in changes and re.fullmatch(r"[0-9a-f-]{36}", str(changes[key])):
                    self.cfg[key] = str(changes[key])
            for key in ("extra_games", "ignore"):
                if key in changes and isinstance(changes[key], list):
                    self.cfg[key] = sorted({str(x).strip()[:80] for x in changes[key] if str(x).strip()})[:50]
            # le jeu en cours vient d'être mis dans les exceptions : on sort du mode jeu tout de suite
            if self.in_game and self.game and self.game.lower() in {x.lower() for x in self.cfg["ignore"]}:
                if self.cfg["power_enabled"] and self.active:
                    switch_to = self.cfg["normal_plan"]
                self.in_game, self.game, self.since = False, None, None
            store.save("gamemode", self.cfg)
            cfg = dict(self.cfg)
        if switch_to:
            ok = set_power_plan(switch_to)
            self.last_switch = {"time": time.time(), "plan": switch_to, "ok": ok}
        return cfg

    # -- détection -----------------------------------------------------------------
    def _detect(self) -> str | None:
        extra = {x.lower() for x in self.cfg["extra_games"]}
        ignore = {x.lower() for x in self.cfg["ignore"]}
        for p in psutil.process_iter(["name"]):
            name = (p.info.get("name") or "")
            low = name.lower()
            if not low or low in ignore:
                continue
            if low in extra or GAME_NAMES.match(low):
                return name
            if NOT_GAMES.search(low):
                continue
            try:
                exe = (p.exe() or "").lower()
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                continue
            if exe and any(d in exe for d in GAME_DIRS) and "\\launcher" not in exe:
                return name
        return None

    def _loop(self) -> None:
        while True:
            try:
                game = self._detect()
                now = time.time()
                switch_to = None
                with self._lock:
                    on = self.cfg["power_enabled"] and self.cfg["enabled"]   # (désactivé : plan jamais touché)
                    if game:
                        self._last_seen = now
                        if not self.in_game:
                            self.in_game, self.game, self.since = True, game, now
                            switch_to = self.cfg["game_plan"] if on else None
                        else:
                            self.game = game
                    elif self.in_game and now - self._last_seen > EXIT_DELAY:
                        self.in_game, self.game, self.since = False, None, None
                        switch_to = self.cfg["normal_plan"] if on else None
                if switch_to:
                    ok = set_power_plan(switch_to)
                    self.last_switch = {"time": now, "plan": switch_to, "ok": ok}
            except Exception as exc:
                logs.signaler("Mode jeu", exc)
            time.sleep(CHECK_INTERVAL)

    def state(self) -> dict:
        with self._lock:
            # in_game : mode jeu EN VIGUEUR (allège le panel) ; detected / game : ce que la détection voit
            # (les statistiques comptent le temps de jeu même si le mode jeu est désactivé)
            return {"in_game": self.active, "detected": self.in_game, "game": self.game, "since": self.since,
                    "enabled": self.cfg["enabled"], "power_enabled": self.cfg["power_enabled"], "last_switch": self.last_switch}

    def details(self) -> dict:
        plans, active = power_plans()
        with self._lock:
            cfg = dict(self.cfg)
        return {**self.state(), "config": cfg, "plans": plans, "active_plan": active}
