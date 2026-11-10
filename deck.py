"""Stream deck de NEXUS : boutons définis dans deck.json, exécutés côté serveur.

SÉCURITÉ
- Le navigateur (ou Discord) n'envoie QUE l'identifiant d'un bouton. L'action exécutée est lue dans
  deck.json, jamais dans la requête : pas de commande, de chemin ni de texte libre venant du client.
- Types d'actions : liste fermée (ACTION_TYPES). Chaque bouton est validé à la lecture ET à l'écriture.
- Scripts : uniquement des fichiers du dossier actions/, désignés par leur nom (pas de chemin).
- Éteindre / redémarrer / veille : seulement si le bouton a "confirm": true, et l'interface doit
  envoyer la confirmation explicite. Jamais déclenchable depuis Discord.
- Accès protégé par le mot de passe de config.json (session en cookie HttpOnly) + limite de requêtes.
- Chaque exécution est journalisée dans logs/deck.log.
"""

from __future__ import annotations

import ctypes
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
DECK_FILE = BASE / "deck.json"
EXAMPLE_FILE = BASE / "deck.example.json"
ACTIONS_DIR = BASE / "actions"
LOG_FILE = BASE / "logs" / "deck.log"
SESSIONS_FILE = BASE / "data" / "deck_sessions.json"
SESSION_COOKIE = "deck_session"
SESSION_DAYS = 30
MAX_BUTTONS = 60

CREATE_NO_WINDOW = 0x08000000
DETACHED = 0x00000008 | 0x00000200

# Touches multimédia Windows (codes de touches virtuelles)
MEDIA_KEYS = {"play_pause": 0xB3, "next": 0xB0, "prev": 0xB1, "volume_up": 0xAF, "volume_down": 0xAE, "mute": 0xAD}
MEDIA_LABELS = {"play_pause": "Lecture / pause", "next": "Suivant", "prev": "Précédent",
                "volume_up": "Volume +", "volume_down": "Volume −", "mute": "Muet"}
POWER_OPS = {"shutdown": "Éteindre", "restart": "Redémarrer", "sleep": "Mettre en veille"}
APP_EXTS = (".exe", ".lnk", ".url", ".appref-ms")
SCRIPT_RE = re.compile(r"^[\w][\w\-. ]{0,60}\.(bat|cmd|ps1|py)$", re.I)
ID_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# Liste FERMÉE des types d'actions (l'interface d'édition ne propose que ceux-ci)
ACTION_TYPES = {
    "app": "Ouvrir une application",
    "url": "Ouvrir une URL",
    "media": "Touche multimédia",
    "lock": "Verrouiller la session",
    "script": "Lancer un script (dossier actions/)",
    "power": "Éteindre / redémarrer / veille",
}


PBKDF2_ITERATIONS = 240_000


def hash_password(password: str) -> str:
    """Empreinte du mot de passe (PBKDF2-SHA256 salé) : c'est elle qu'écrit l'assistant de configuration,
    jamais le mot de passe en clair."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(cfg: dict, password: str) -> bool:
    stored = str(cfg.get("password_hash") or "")
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iters, salt, digest = stored.split("$")
            test = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters)).hex()
        except ValueError:
            return False
        return hmac.compare_digest(test, digest)
    plain = str(cfg.get("password") or "")           # ancienne config : mot de passe en clair
    return bool(plain) and hmac.compare_digest(password.encode(), plain.encode())


class DeckError(ValueError):
    pass


# --------------------------------------------------------------------------- #
#  Validation d'un bouton
# --------------------------------------------------------------------------- #
def list_scripts() -> list[str]:
    if not ACTIONS_DIR.is_dir():
        return []
    return sorted(p.name for p in ACTIONS_DIR.iterdir() if p.is_file() and SCRIPT_RE.match(p.name))


def script_path(name: str) -> Path:
    """Chemin d'un script de actions/, à partir de son seul nom de fichier."""
    if not isinstance(name, str) or not SCRIPT_RE.match(name):
        raise DeckError("nom de script invalide (fichier .bat, .cmd, .ps1 ou .py du dossier actions/)")
    p = (ACTIONS_DIR / name).resolve()
    if p.parent != ACTIONS_DIR.resolve() or not p.is_file():
        raise DeckError(f"script introuvable dans actions/ : {name}")
    return p


def validate(b: dict) -> dict:
    if not isinstance(b, dict):
        raise DeckError("bouton invalide")
    bid = str(b.get("id") or "").strip().lower()
    if not ID_RE.match(bid):
        raise DeckError(f"identifiant invalide : « {bid} » (a-z, 0-9, - et _, 32 caractères max)")
    label = str(b.get("label") or "").strip()[:30]
    if not label:
        raise DeckError(f"« {label or bid} » : libellé manquant")
    typ = b.get("type")
    if typ not in ACTION_TYPES:
        raise DeckError(f"« {label or bid} » : type d'action non autorisé ({typ})")
    color = str(b.get("color") or "#00f0ff")
    if not COLOR_RE.match(color):
        raise DeckError(f"« {label or bid} » : couleur invalide ({color}), format #rrggbb")
    params = b.get("params") or {}
    if not isinstance(params, dict):
        raise DeckError(f"« {label or bid} » : paramètres invalides")
    confirm = bool(b.get("confirm", False))
    clean: dict = {}

    if typ == "app":
        path = str(params.get("path") or "").strip().strip('"')
        if not os.path.isabs(path) or not path.lower().endswith(APP_EXTS):
            raise DeckError(f"« {label or bid} » : chemin d'application absolu attendu ({', '.join(APP_EXTS)})")
        if not Path(path).is_file():
            raise DeckError(f"« {label or bid} » : application introuvable : {path}")
        args = params.get("args") or []
        if not isinstance(args, list) or len(args) > 10 or not all(isinstance(a, str) and len(a) <= 200 for a in args):
            raise DeckError(f"« {label or bid} » : arguments invalides (liste de 10 textes max)")
        clean = {"path": path, "args": args}
    elif typ == "url":
        url = str(params.get("url") or "").strip()
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.netloc or len(url) > 500:
            raise DeckError(f"« {label or bid} » : URL http(s) attendue")
        clean = {"url": url}
    elif typ == "media":
        key = params.get("key")
        if key not in MEDIA_KEYS:
            raise DeckError(f"« {label or bid} » : touche multimédia inconnue ({key})")
        clean = {"key": key}
    elif typ == "lock":
        clean = {}
    elif typ == "script":
        script_path(params.get("name"))            # lève une erreur si invalide ou absent
        clean = {"name": params["name"]}
    elif typ == "power":
        op = params.get("op")
        if op not in POWER_OPS:
            raise DeckError(f"« {label or bid} » : opération d'alimentation inconnue ({op})")
        if not confirm:
            raise DeckError(f"« {label or bid} » : « {POWER_OPS[op]} » exige \"confirm\": true")
        clean = {"op": op}

    icon = str(b.get("icon") or "").strip()[:8]
    # Discord : jamais pour un bouton qui demande une confirmation (ni pour l'alimentation)
    discord = bool(b.get("discord", False)) and not confirm and typ != "power"
    return {"id": bid, "label": label, "icon": icon, "color": color, "type": typ,
            "params": clean, "confirm": confirm, "discord": discord}


# --------------------------------------------------------------------------- #
#  Exécution
# --------------------------------------------------------------------------- #
def _press(vk: int) -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, 2, 0)            # KEYEVENTF_KEYUP


def execute(b: dict) -> str:
    """Exécute l'action d'un bouton DÉJÀ validé (venant de deck.json)."""
    t, p = b["type"], b["params"]
    if t == "app":
        if p["args"]:
            subprocess.Popen([p["path"], *p["args"]], cwd=str(Path(p["path"]).parent), creationflags=DETACHED, close_fds=True)
        else:
            os.startfile(p["path"])
        return "application lancée"
    if t == "url":
        os.startfile(p["url"])
        return "page ouverte"
    if t == "media":
        _press(MEDIA_KEYS[p["key"]])
        return MEDIA_LABELS[p["key"]]
    if t == "lock":
        if not ctypes.windll.user32.LockWorkStation():
            raise OSError("verrouillage refusé par Windows")
        return "session verrouillée"
    if t == "script":
        path = script_path(p["name"])
        ext = path.suffix.lower()
        cmd = (["cmd", "/c", str(path)] if ext in (".bat", ".cmd")
               else ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)] if ext == ".ps1"
               else [sys.executable, str(path)])
        subprocess.Popen(cmd, cwd=str(ACTIONS_DIR), creationflags=CREATE_NO_WINDOW, close_fds=True)
        return f"script {path.name} lancé"
    if t == "power":
        op = p["op"]
        if op == "shutdown":
            subprocess.Popen(["shutdown", "/s", "/t", "15", "/c", "Arrêt demandé depuis NEXUS (shutdown /a pour annuler)"],
                             creationflags=CREATE_NO_WINDOW)
            return "arrêt dans 15 s (annuler : shutdown /a)"
        if op == "restart":
            subprocess.Popen(["shutdown", "/r", "/t", "15", "/c", "Redémarrage demandé depuis NEXUS (shutdown /a pour annuler)"],
                             creationflags=CREATE_NO_WINDOW)
            return "redémarrage dans 15 s (annuler : shutdown /a)"
        if op == "sleep":
            threading.Timer(1.5, lambda: ctypes.windll.powrprof.SetSuspendState(False, True, False)).start()
            return "mise en veille"
    raise DeckError("type d'action non autorisé")


# --------------------------------------------------------------------------- #
#  Deck : chargement, sauvegarde, exécution, journal, sessions, limites
# --------------------------------------------------------------------------- #
class Deck:
    def __init__(self, executor=execute) -> None:
        self._lock = threading.Lock()
        self._executor = executor                   # remplaçable pour les tests (aucune action réelle)
        self.warnings: list[str] = []
        self.buttons: list[dict] = []
        self._sessions: dict[str, float] = {}      # hash du jeton -> expiration
        self._hits: dict[tuple[str, str], list[float]] = {}
        ACTIONS_DIR.mkdir(exist_ok=True)
        if not DECK_FILE.exists() and EXAMPLE_FILE.exists():
            shutil.copy(EXAMPLE_FILE, DECK_FILE)
        self.load()
        self._load_sessions()

    # -- fichier deck.json ---------------------------------------------------------
    def load(self) -> None:
        self.warnings = []
        try:
            raw = json.loads(DECK_FILE.read_text(encoding="utf-8"))
            items = raw.get("buttons", []) if isinstance(raw, dict) else raw
        except (OSError, ValueError) as exc:
            self.warnings.append(f"deck.json illisible : {exc}")
            items = []
        good, seen = [], set()
        for b in items[:MAX_BUTTONS]:
            try:
                v = validate(b)
                if v["id"] in seen:
                    raise DeckError(f"identifiant en double : {v['id']}")
                seen.add(v["id"])
                good.append(v)
            except DeckError as exc:
                self.warnings.append(f"bouton ignoré — {exc}")
        with self._lock:
            self.buttons = good
        for w in self.warnings:
            print(f"[Deck] {w}")

    def save(self, items: list) -> list[dict]:
        if not isinstance(items, list) or len(items) > MAX_BUTTONS:
            raise DeckError(f"liste de {MAX_BUTTONS} boutons max attendue")
        clean, seen = [], set()
        for b in items:
            if isinstance(b, dict) and not b.get("id"):
                b = {**b, "id": "b" + secrets.token_hex(4)}
            v = validate(b)
            if v["id"] in seen:
                raise DeckError(f"identifiant en double : {v['id']}")
            seen.add(v["id"])
            clean.append(v)
        tmp = DECK_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"buttons": clean}, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DECK_FILE)
        with self._lock:
            self.buttons = clean
        return clean

    def get(self, bid: str) -> dict | None:
        with self._lock:
            return next((b for b in self.buttons if b["id"] == bid), None)

    def discord_buttons(self) -> list[dict]:
        with self._lock:
            return [b for b in self.buttons if b["discord"] and not b["confirm"] and b["type"] != "power"]

    def find_for_discord(self, name: str) -> dict | None:
        name = (name or "").strip().lower()
        return next((b for b in self.discord_buttons() if b["label"].lower() == name or b["id"] == name), None)

    # -- exécution -------------------------------------------------------------------
    def run(self, bid: str, source: str = "web", ip: str = "", confirmed: bool = False) -> tuple[bool, str]:
        b = self.get(str(bid))
        if not b:
            self._log(source, ip, bid, "?", "refusé", "bouton inconnu")
            return False, "bouton inconnu"
        if source == "discord" and (not b["discord"] or b["confirm"] or b["type"] == "power"):
            self._log(source, ip, bid, b["label"], "refusé", "non autorisé depuis Discord")
            return False, "ce bouton n'est pas autorisé depuis Discord"
        if b["confirm"] and not confirmed:
            self._log(source, ip, bid, b["label"], "refusé", "confirmation manquante")
            return False, "confirmation requise"
        try:
            msg = self._executor(b)
        except Exception as exc:
            self._log(source, ip, bid, b["label"], "erreur", f"{type(exc).__name__}: {exc}")
            return False, f"échec : {exc}"
        self._log(source, ip, bid, b["label"], "ok", msg)
        return True, msg

    def _log(self, source, ip, bid, label, result, detail) -> None:
        LOG_FILE.parent.mkdir(exist_ok=True)
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {source:<7} | {ip or '-':<15} | {bid} | {label} | {result} | {detail}\n"
        with self._lock, open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)

    def recent_log(self, n: int = 15) -> list[str]:
        try:
            return LOG_FILE.read_text(encoding="utf-8").splitlines()[-n:][::-1]
        except OSError:
            return []

    # -- mot de passe, sessions, limite de requêtes ----------------------------------------
    @staticmethod
    def password_set(cfg: dict) -> bool:
        if str(cfg.get("password_hash") or "").startswith("pbkdf2_sha256$"):
            return True
        pw = str(cfg.get("password") or "")
        return bool(pw) and "CHOISIS" not in pw

    def login(self, cfg: dict, password: str) -> str | None:
        if not self.password_set(cfg) or not verify_password(cfg, str(password)):
            return None
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[hashlib.sha256(token.encode()).hexdigest()] = time.time() + SESSION_DAYS * 86400
            self._save_sessions()
        return token

    def check_session(self, token: str | None) -> bool:
        if not token:
            return False
        h = hashlib.sha256(token.encode()).hexdigest()
        with self._lock:
            exp = self._sessions.get(h)
            if exp and exp > time.time():
                return True
            if exp:
                del self._sessions[h]
        return False

    def logout(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)
                self._save_sessions()

    def revoke_all_sessions(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._save_sessions()

    def _load_sessions(self) -> None:
        try:
            data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
            now = time.time()
            self._sessions = {k: v for k, v in data.items() if isinstance(v, (int, float)) and v > now}
        except (OSError, ValueError):
            self._sessions = {}

    def _save_sessions(self) -> None:
        SESSIONS_FILE.parent.mkdir(exist_ok=True)
        SESSIONS_FILE.write_text(json.dumps(self._sessions), encoding="utf-8")

    def rate_ok(self, ip: str, bucket: str, per_minute: int) -> bool:
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get((ip, bucket), []) if now - t < 60]
            ok = len(hits) < per_minute
            if ok:
                hits.append(now)
            self._hits[(ip, bucket)] = hits
            return ok
