"""Réseau local : ping / qualité de connexion, appareils connectés.
(Le test de débit tourne dans le navigateur : voir static/js/network.js.)"""

from __future__ import annotations

import ctypes
import ipaddress
import re
import socket
import subprocess
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from ctypes import wintypes

import psutil

import store

CREATE_NO_WINDOW = 0x08000000

# --------------------------------------------------------------------------- #
#  Ping ICMP via iphlpapi (pas besoin des droits administrateur)
# --------------------------------------------------------------------------- #
_iphlpapi = ctypes.WinDLL("iphlpapi")


class _IPOptions(ctypes.Structure):
    _fields_ = [("Ttl", ctypes.c_ubyte), ("Tos", ctypes.c_ubyte), ("Flags", ctypes.c_ubyte), ("OptionsSize", ctypes.c_ubyte), ("OptionsData", ctypes.c_void_p)]


class _EchoReply(ctypes.Structure):
    _fields_ = [
        ("Address", ctypes.c_ulong),
        ("Status", ctypes.c_ulong),
        ("RoundTripTime", ctypes.c_ulong),
        ("DataSize", ctypes.c_ushort),
        ("Reserved", ctypes.c_ushort),
        ("Data", ctypes.c_void_p),
        ("Options", _IPOptions),
    ]


_iphlpapi.IcmpCreateFile.restype = wintypes.HANDLE
_iphlpapi.IcmpCloseHandle.argtypes = [wintypes.HANDLE]
_iphlpapi.IcmpSendEcho.argtypes = [
    wintypes.HANDLE,
    ctypes.c_ulong,
    ctypes.c_void_p,
    ctypes.c_ushort,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.c_ulong,
]
_iphlpapi.IcmpSendEcho.restype = ctypes.c_ulong


def ping(ip: str, timeout_ms: int = 1000) -> float | None:
    """Renvoie le temps de réponse en ms, ou None si pas de réponse."""
    try:
        addr = int.from_bytes(socket.inet_aton(ip), "little")
    except OSError:
        return None
    handle = _iphlpapi.IcmpCreateFile()
    if not handle or handle == wintypes.HANDLE(-1).value:
        return None
    try:
        payload = b"statspc-ping-32b-payload-abcdefg"
        size = ctypes.sizeof(_EchoReply) + len(payload) + 8
        buf = ctypes.create_string_buffer(size)
        t0 = time.perf_counter()
        n = _iphlpapi.IcmpSendEcho(handle, addr, payload, len(payload), None, buf, size, timeout_ms)
        elapsed = (time.perf_counter() - t0) * 1000
        if n == 0:
            return None
        reply = _EchoReply.from_buffer(buf)
        if reply.Status != 0:
            return None
        # RoundTripTime est en ms entières : on prend la mesure locale si elle est plus fine.
        return round(min(float(reply.RoundTripTime) if reply.RoundTripTime else elapsed, elapsed), 1)
    finally:
        _iphlpapi.IcmpCloseHandle(handle)


def default_gateway() -> str | None:
    try:
        out = subprocess.run(
            ["route", "print", "-4", "0.0.0.0"], capture_output=True, text=True, encoding="oem", errors="replace", timeout=5, creationflags=CREATE_NO_WINDOW
        ).stdout
    except Exception:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
            try:
                ipaddress.IPv4Address(parts[2])
                return parts[2]
            except ValueError:
                continue
    return None


# --------------------------------------------------------------------------- #
#  Surveillance du ping et de la qualité
# --------------------------------------------------------------------------- #
HISTORY = 300  # 5 minutes à 1 mesure/s
STATS_WINDOW = 60  # statistiques sur la dernière minute
OUTAGE_MIN = 3  # coupure si 3 s consécutives sans réponse d'Internet


class PingMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.gateway = default_gateway()
        self.targets = [("gateway", "Box / routeur", self.gateway), ("cloudflare", "Cloudflare", "1.1.1.1"), ("google", "Google", "8.8.8.8")]
        self.hist = {k: deque(maxlen=HISTORY) for k, _, _ in self.targets}
        self.outages: deque = deque(maxlen=30)
        self._down_since = None
        self._down_count = 0
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        pool = ThreadPoolExecutor(max_workers=len(self.targets))
        last_gw = time.time()
        while True:
            t0 = time.time()
            if time.time() - last_gw > 300:
                self.gateway = default_gateway() or self.gateway
                self.targets[0] = ("gateway", "Box / routeur", self.gateway)
                last_gw = time.time()
            try:
                futs = {k: pool.submit(ping, ip, 900) if ip else None for k, _, ip in self.targets}
            except RuntimeError:  # arrêt de Python en cours
                return
            res = {k: (f.result() if f else None) for k, f in futs.items()}
            with self._lock:
                for k, v in res.items():
                    self.hist[k].append(v)
                internet_down = res["cloudflare"] is None and res["google"] is None
                if internet_down:
                    self._down_count += 1
                    if self._down_count == 1:
                        self._down_since = t0
                    if self._down_count == OUTAGE_MIN:
                        self.outages.appendleft({"start": self._down_since, "end": None, "box_ok": res["gateway"] is not None})
                else:
                    if self._down_count >= OUTAGE_MIN and self.outages and self.outages[0]["end"] is None:
                        self.outages[0]["end"] = t0
                    self._down_count = 0
            time.sleep(max(0.05, 1 - (time.time() - t0)))

    @staticmethod
    def _stats(values: list) -> dict:
        ok = [v for v in values if v is not None]
        n = len(values)
        jitter = (sum(abs(a - b) for a, b in zip(ok, ok[1:])) / (len(ok) - 1)) if len(ok) > 1 else None
        return {
            "last": values[-1] if values else None,
            "avg": round(sum(ok) / len(ok), 1) if ok else None,
            "min": min(ok) if ok else None,
            "max": max(ok) if ok else None,
            "jitter": round(jitter, 1) if jitter is not None else None,
            "loss": round((n - len(ok)) / n * 100, 1) if n else None,
        }

    def state(self) -> dict:
        with self._lock:
            targets = []
            for key, label, ip in self.targets:
                values = list(self.hist[key])
                targets.append({"key": key, "label": label, "ip": ip, "history": values, **self._stats(values[-STATS_WINDOW:])})
            outages = list(self.outages)
            down = self._down_count >= OUTAGE_MIN
        net = [t for t in targets if t["key"] != "gateway"]
        avg = [t["avg"] for t in net if t["avg"] is not None]
        jit = [t["jitter"] for t in net if t["jitter"] is not None]
        loss = [t["loss"] for t in net if t["loss"] is not None]
        return {
            "targets": targets,
            "outages": outages,
            "internet_down": down,
            "quality": _quality(min(avg) if avg else None, min(jit) if jit else None, min(loss) if loss else None, down),
        }


def _quality(avg, jitter, loss, down) -> dict:
    if down:
        return {"grade": "coupure", "label": "Internet coupé", "score": 0}
    if avg is None:
        return {"grade": "inconnu", "label": "Mesure en cours…", "score": None}
    score = 100
    score -= max(0, min(40, (avg - 15) * 0.5))  # latence
    score -= max(0, min(30, ((jitter or 0) - 2) * 2))  # gigue
    score -= max(0, min(50, (loss or 0) * 6))  # pertes
    score = round(max(0, score))
    for limit, grade, label in ((90, "excellente", "Excellente"), (75, "bonne", "Bonne"), (50, "moyenne", "Moyenne"), (-1, "mauvaise", "Mauvaise")):
        if score >= limit:
            return {"grade": grade, "label": label, "score": score}


# --------------------------------------------------------------------------- #
#  Appareils connectés au réseau local
# --------------------------------------------------------------------------- #
SCAN_INTERVAL = 300
MAC_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-f]{2}(?:[-:][0-9a-f]{2}){5})", re.I)


def _local_network() -> tuple[str, str, ipaddress.IPv4Network] | None:
    """(ip locale, mac locale, réseau) de l'interface qui porte la route par défaut."""
    gw = default_gateway()
    for name, addrs in psutil.net_if_addrs().items():
        mac = next((a.address for a in addrs if a.family == psutil.AF_LINK), None)
        for a in addrs:
            if a.family == socket.AF_INET and a.netmask and not a.address.startswith("127."):
                net = ipaddress.IPv4Network(f"{a.address}/{a.netmask}", strict=False)
                if gw is None or ipaddress.IPv4Address(gw) in net:
                    return a.address, (mac or "").lower().replace(":", "-"), net
    return None


def _arp_table() -> dict[str, str]:
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True, encoding="oem", errors="replace", timeout=10, creationflags=CREATE_NO_WINDOW).stdout
    except Exception:
        return {}
    table = {}
    for ip, mac in MAC_RE.findall(out):
        mac = mac.lower().replace(":", "-")
        if mac.startswith("01-00-5e") or mac == "ff-ff-ff-ff-ff-ff" or ip.endswith(".255"):
            continue
        table[ip] = mac
    return table


def _hostname(ip: str) -> str | None:
    try:
        name = socket.gethostbyaddr(ip)[0]
        return None if name == ip else name.removesuffix(".home").removesuffix(".lan").removesuffix(".local")
    except OSError:
        return None


class LanScanner:
    def __init__(self, gateway_getter, paused=lambda: False) -> None:
        self._lock = threading.Lock()
        self._gateway = gateway_getter
        self._paused = paused  # mode jeu : pas de scan automatique (64 pings en parallèle)
        self._manual = False
        self._scanning = False
        self.last_scan = None
        self.error = None
        self.devices: dict[str, dict] = {}  # mac -> infos du dernier scan
        self.known = store.load("devices", {}) or {}  # mac -> {label, first_seen, last_seen, ...}
        self._wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def request_scan(self) -> None:
        self._manual = True
        self._wake.set()

    def _loop(self) -> None:
        while True:
            if self._manual or not self._paused():
                try:
                    self._scan()
                    self.error = None
                except Exception as exc:
                    self.error = f"{type(exc).__name__}: {exc}"
            self._manual = False
            self._wake.wait(SCAN_INTERVAL)
            self._wake.clear()

    def _scan(self) -> None:
        local = _local_network()
        if not local:
            raise RuntimeError("aucun réseau local détecté")
        my_ip, my_mac, net = local
        if net.num_addresses > 1024:
            raise RuntimeError(f"réseau {net} trop grand pour être scanné")
        self._scanning = True
        try:
            hosts = [str(h) for h in net.hosts()]
            rtts: dict[str, float] = {}
            with ThreadPoolExecutor(64) as pool:
                futs = {pool.submit(ping, ip, 600): ip for ip in hosts}
                for f in as_completed(futs):
                    r = f.result()
                    if r is not None:
                        rtts[futs[f]] = r
            arp = _arp_table()
            online = {ip: mac for ip, mac in arp.items() if ipaddress.IPv4Address(ip) in net}
            online[my_ip] = my_mac
            for ip in rtts:  # répond au ping mais absent de l'ARP (rare)
                online.setdefault(ip, f"ip:{ip}")
            with ThreadPoolExecutor(32) as pool:
                names = dict(zip(online, pool.map(_hostname, online)))
            now = time.time()
            gw = self._gateway()
            devices = {}
            for ip, mac in online.items():
                k = self.known.setdefault(mac, {"first_seen": now})
                k.update(last_seen=now, last_ip=ip)
                if names.get(ip):
                    k["hostname"] = names[ip]
                devices[mac] = {"mac": mac, "ip": ip, "rtt": rtts.get(ip), "hostname": k.get("hostname"), "is_self": ip == my_ip, "is_gateway": ip == gw}
            with self._lock:
                self.devices = devices
                self.last_scan = now
                self.network = str(net)
            store.save("devices", self.known)
        finally:
            self._scanning = False

    def rename(self, mac: str, label: str) -> bool:
        with self._lock:
            if mac not in self.known:
                return False
            if label:
                self.known[mac]["label"] = label
            else:
                self.known[mac].pop("label", None)
            store.save("devices", self.known)
        return True

    def forget(self, mac: str) -> bool:
        with self._lock:
            if mac in self.devices or mac not in self.known:
                return False
            del self.known[mac]
            store.save("devices", self.known)
        return True

    def state(self) -> dict:
        with self._lock:
            out = []
            for mac, k in self.known.items():
                d = self.devices.get(mac)
                # Bit « administré localement » : adresse MAC aléatoire (téléphones, PC récents)
                try:
                    private = bool(int(mac[1], 16) & 0x2) if not mac.startswith("ip:") else False
                except ValueError:
                    private = False
                out.append(
                    {
                        "mac": mac,
                        "online": d is not None,
                        "ip": d["ip"] if d else k.get("last_ip"),
                        "rtt": d["rtt"] if d else None,
                        "hostname": k.get("hostname"),
                        "label": k.get("label"),
                        "first_seen": k.get("first_seen"),
                        "last_seen": k.get("last_seen"),
                        "private_mac": private,
                        "is_self": bool(d and d["is_self"]),
                        "is_gateway": bool(d and d["is_gateway"]),
                    }
                )
            out.sort(key=lambda x: (not x["online"], not x["is_gateway"], not x["is_self"], tuple(int(p) for p in (x["ip"] or "0.0.0.0").split("."))))
            return {"devices": out, "last_scan": self.last_scan, "scanning": self._scanning, "error": self.error, "network": getattr(self, "network", None)}
