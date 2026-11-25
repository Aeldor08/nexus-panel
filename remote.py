"""Accès depuis le téléphone (réseau local uniquement).

Sécurité :
- désactivé par défaut ; quand il l'est, le serveur n'écoute que sur 127.0.0.1 ;
- activé : le serveur écoute aussi sur le réseau local, mais toute requête qui ne vient pas
  du PC lui-même doit présenter le jeton d'un appareil appairé (cookie HttpOnly) ;
- les adresses publiques (Internet) sont toujours refusées, même avec un jeton ;
- l'appairage se fait par QR code ou code à 6 chiffres, affichés sur le PC, valables 2 minutes,
  à usage unique, 5 essais maximum ;
- les jetons sont stockés hachés (SHA-256) : le fichier data/remote.json ne permet pas de se connecter ;
- seul le PC peut activer/désactiver l'accès, appairer ou révoquer un appareil.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import threading
import time

import store

COOKIE = "nexus_token"
COOKIE_MAX_AGE = 365 * 24 * 3600
PAIR_TTL = 120  # s de validité d'un code d'appairage
PAIR_MAX_TRIES = 5
CLAIM_RATE = 10  # essais d'appairage max par minute et par adresse IP


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def is_loopback(ip: str | None) -> bool:
    try:
        return ipaddress.ip_address(ip or "").is_loopback
    except ValueError:
        return False


def is_private(ip: str | None) -> bool:
    try:
        a = ipaddress.ip_address(ip or "")
    except ValueError:
        return False
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return (a.is_private or a.is_link_local) and not a.is_loopback


def device_label(user_agent: str) -> str:
    ua = user_agent or ""
    os_ = (
        "iPhone"
        if "iPhone" in ua
        else "iPad"
        if "iPad" in ua
        else "Android"
        if "Android" in ua
        else "Windows"
        if "Windows" in ua
        else "Mac"
        if "Mac OS" in ua
        else "Appareil"
    )
    br = (
        "Opera"
        if "OPR/" in ua
        else "Edge"
        if "Edg/" in ua
        else "Samsung Internet"
        if "SamsungBrowser" in ua
        else "Chrome"
        if "Chrome/" in ua
        else "Firefox"
        if "Firefox/" in ua
        else "Safari"
        if "Safari/" in ua
        else ""
    )
    return f"{os_} · {br}" if br else os_


class Remote:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        cfg = store.load("remote") or {}
        self.enabled = bool(cfg.get("enabled", False))
        self.devices: list[dict] = list(cfg.get("devices", []))
        self.active = False  # le serveur écoute-t-il vraiment sur le réseau ? (fixé au démarrage)
        self._pairing = None  # {"secret", "code", "expires", "tries"}
        self._claims: dict[str, list[float]] = {}
        self._dirty_seen = 0.0

    def _save(self) -> None:
        store.save("remote", {"enabled": self.enabled, "devices": self.devices})

    # -- configuration (depuis le PC uniquement) ------------------------------------
    def set_enabled(self, on: bool) -> bool:
        """Renvoie True si un redémarrage du serveur est nécessaire."""
        with self._lock:
            self.enabled = bool(on)
            self._save()
            return self.enabled != self.active

    def start_pairing(self) -> dict:
        with self._lock:
            self._pairing = {"secret": secrets.token_urlsafe(24), "code": f"{secrets.randbelow(10**6):06d}", "expires": time.time() + PAIR_TTL, "tries": 0}
            return dict(self._pairing)

    def pairing(self) -> dict | None:
        with self._lock:
            p = self._pairing
            if p and p["expires"] > time.time() and p["tries"] < PAIR_MAX_TRIES:
                return dict(p)
            self._pairing = None
            return None

    def cancel_pairing(self) -> None:
        with self._lock:
            self._pairing = None

    def revoke(self, dev_id: str) -> bool:
        with self._lock:
            before = len(self.devices)
            self.devices = [d for d in self.devices if d["id"] != dev_id]
            self._save()
            return len(self.devices) != before

    def rename(self, dev_id: str, name: str) -> bool:
        with self._lock:
            for d in self.devices:
                if d["id"] == dev_id:
                    d["name"] = name[:40] or d["name"]
                    self._save()
                    return True
            return False

    # -- appairage (depuis le téléphone) -----------------------------------------------
    def claim(self, ip: str, secret: str | None, code: str | None, name: str, user_agent: str) -> str | None:
        """Vérifie le secret (QR) ou le code (saisi) ; renvoie un nouveau jeton, sinon None."""
        now = time.time()
        with self._lock:
            hits = [t for t in self._claims.get(ip, []) if now - t < 60]
            hits.append(now)
            self._claims[ip] = hits
            if len(hits) > CLAIM_RATE:
                return None
            p = self._pairing
            if not p or p["expires"] < now or p["tries"] >= PAIR_MAX_TRIES:
                self._pairing = None
                return None
            p["tries"] += 1
            ok = (secret and hmac.compare_digest(secret, p["secret"])) or (code and hmac.compare_digest(code.strip(), p["code"]))
            if not ok:
                if p["tries"] >= PAIR_MAX_TRIES:
                    self._pairing = None
                return None
            self._pairing = None  # usage unique
            token = secrets.token_urlsafe(32)
            self.devices.append(
                {
                    "id": secrets.token_hex(6),
                    "name": (name or device_label(user_agent))[:40],
                    "token_hash": _hash(token),
                    "created": now,
                    "last_seen": now,
                    "last_ip": ip,
                    "agent": device_label(user_agent),
                }
            )
            self._save()
            return token

    # -- contrôle de chaque requête venant du réseau -----------------------------------
    def check(self, token: str | None, ip: str) -> dict | None:
        if not token:
            return None
        h = _hash(token)
        with self._lock:
            for d in self.devices:
                if hmac.compare_digest(d["token_hash"], h):
                    now = time.time()
                    d["last_seen"], d["last_ip"] = now, ip
                    if now - self._dirty_seen > 300:  # on n'écrit « vu à » que toutes les 5 min
                        self._dirty_seen = now
                        self._save()
                    return d
        return None

    def state(self) -> dict:
        with self._lock:
            return {
                "enabled": self.enabled,
                "active": self.active,
                "restart_needed": self.enabled != self.active,
                "devices": [{k: v for k, v in d.items() if k != "token_hash"} for d in self.devices],
            }
