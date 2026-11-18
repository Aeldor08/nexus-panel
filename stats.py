"""Capteurs du PC : CPU, RAM, disques, carte graphique (NVIDIA, AMD, Intel), températures, ventilateurs,
réseau, processus.

Module partagé par le serveur web (app.py), le bot Discord (bot.py) et le stream deck :
tout ce qui lit le matériel est ici, une seule fois.
- psutil            : CPU (global + par cœur), RAM, disques, réseau, processus
- carte graphique   : détectée automatiquement (detect_gpus) puis lue par la meilleure source :
                      NVML pour NVIDIA (repli nvidia-smi), LibreHardwareMonitor pour AMD / Intel,
                      sinon les compteurs de Windows (charge et VRAM) — voir GpuReader
- LibreHardwareMonitor (http://127.0.0.1:8085/data.json) : températures CPU / disques / GPU, ventilateurs
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request

import psutil

import paths
import winproc

# 127.0.0.1 plutôt que "localhost" : sous Windows, "localhost" peut d'abord essayer
# l'IPv6 (::1) et attendre le délai d'expiration avant de passer à l'IPv4.
LHM_URL = "http://127.0.0.1:8085/data.json"
LHM_TIMEOUT = 0.8          # secondes
LHM_POLL_INTERVAL = 2.0    # secondes entre deux lectures de LibreHardwareMonitor

# Seuils des alertes (modifiables)
ALERTS = {
    "cpu_temp": (80, 90),        # °C : avertissement, critique
    "gpu_temp": (80, 87),        # °C
    "disk_temp": (55, 65),       # °C
    "ram_percent": (90, 96),     # %
    "disk_percent": (90, 97),    # % d'espace utilisé
    "disk_free_gb": 10,          # critique sous ce nombre de Go libres
}

FAN_NAMES_FILE = paths.FAN_NAMES_FILE                    # noms personnalisés des ventilateurs (données perso)
_OLD_FAN_NAMES_FILE = paths.LEGACY_DIR / "fan_names.json"  # ancien emplacement, encore lu s'il existe


# --------------------------------------------------------------------------- #
#  Cartes graphiques : détection (toutes marques) + lecture
#   1. NVIDIA  : NVML (complet), repli nvidia-smi
#   2. AMD / Intel (ou NVIDIA sans NVML) : LibreHardwareMonitor (complet, températures comprises)
#   3. Sinon   : compteurs de performances de Windows (charge et VRAM, comme le Gestionnaire des tâches)
# --------------------------------------------------------------------------- #
GPU_VENDORS = {"10de": "NVIDIA", "1002": "AMD", "1022": "AMD", "8086": "Intel", "5143": "Qualcomm"}
SOURCE_LABELS = {"nvml": "pilote NVIDIA (NVML)", "smi": "nvidia-smi", "lhm": "LibreHardwareMonitor",
                 "windows": "compteurs Windows"}


def _vendor_of(text: str) -> str:
    t = (text or "").lower()
    m = re.search(r"ven_([0-9a-f]{4})", t)
    if m and m.group(1) in GPU_VENDORS:
        return GPU_VENDORS[m.group(1)]
    for key, name in (("nvidia", "NVIDIA"), ("geforce", "NVIDIA"), ("radeon", "AMD"), ("amd", "AMD"),
                      ("gpu-amd", "AMD"), ("ati", "AMD"), ("intel", "Intel"), ("arc", "Intel")):
        if key in t:
            return name
    return "autre"


def detect_gpus() -> list[dict]:
    """Liste les cartes graphiques présentes (nom, marque, VRAM), quelle que soit la marque.
    Windows : EnumDisplayDevices (cartes réellement branchées) + registre (taille de la VRAM)."""
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes
    import winreg

    class DISPLAY_DEVICEW(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR * 32), ("DeviceString", wintypes.WCHAR * 128),
                    ("StateFlags", wintypes.DWORD), ("DeviceID", wintypes.WCHAR * 128), ("DeviceKey", wintypes.WCHAR * 128)]

    found: dict[str, dict] = {}
    try:
        enum = ctypes.windll.user32.EnumDisplayDevicesW
        i = 0
        while i < 32:
            dd = DISPLAY_DEVICEW(); dd.cb = ctypes.sizeof(dd)
            if not enum(None, i, ctypes.byref(dd), 0):
                break
            i += 1
            dev_id = dd.DeviceID.upper()
            if not dev_id.startswith("PCI\\") or dd.StateFlags & 0x8:      # virtuelles, miroirs, bureau à distance
                continue
            key = dev_id.split("&SUBSYS")[0]
            if key in found:
                continue
            vram = None
            reg = dd.DeviceKey.split("\\Registry\\Machine\\", 1)[-1] if "\\Registry\\Machine\\" in dd.DeviceKey else None
            if reg:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg) as k:
                        for name in ("HardwareInformation.qwMemorySize", "HardwareInformation.MemorySize"):
                            try:
                                v, _ = winreg.QueryValueEx(k, name)
                            except OSError:
                                continue
                            if isinstance(v, bytes):
                                v = int.from_bytes(v[:8], "little")
                            if isinstance(v, int) and v > 0:
                                vram = v
                                break
                except OSError:
                    pass
            found[key] = {"name": dd.DeviceString.strip(), "vendor": _vendor_of(dev_id + " " + dd.DeviceString),
                          "vram_total": vram, "pci_id": key}
    except Exception:
        return list(found.values())
    # carte dédiée (plus de VRAM) en premier
    return sorted(found.values(), key=lambda a: -(a["vram_total"] or 0))


class WindowsGpuCounters:
    """Charge et mémoire vidéo via les compteurs de performances de Windows (« GPU Engine »,
    « GPU Adapter Memory ») : fonctionne pour toutes les marques, sans logiciel en plus."""

    PDH_FMT_DOUBLE = 0x00000200
    PDH_MORE_DATA = 0x800007D2

    def __init__(self) -> None:
        self.ok, self.error = False, None
        self._lock = threading.Lock()
        if sys.platform != "win32":
            self.error = "uniquement sous Windows"
            return
        try:
            import ctypes
            from ctypes import wintypes
            self._ct, self._wt = ctypes, wintypes

            class FMT(ctypes.Structure):
                _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]

            class ITEM(ctypes.Structure):
                _fields_ = [("szName", ctypes.c_wchar_p), ("FmtValue", FMT)]

            self._ITEM = ITEM
            pdh = ctypes.WinDLL("pdh")
            pdh.PdhOpenQueryW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
            pdh.PdhAddEnglishCounterW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
            pdh.PdhCollectQueryData.argtypes = [ctypes.c_void_p]
            pdh.PdhGetFormattedCounterArrayW.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                                         ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
            for fn in ("PdhOpenQueryW", "PdhAddEnglishCounterW", "PdhCollectQueryData", "PdhGetFormattedCounterArrayW"):
                getattr(pdh, fn).restype = wintypes.DWORD
            self._pdh = pdh
            self._q = ctypes.c_void_p()
            if pdh.PdhOpenQueryW(None, None, ctypes.byref(self._q)):
                raise OSError("ouverture des compteurs impossible")
            self._eng, self._mem = ctypes.c_void_p(), ctypes.c_void_p()
            for path, handle in ((r"\GPU Engine(*)\Utilization Percentage", self._eng),
                                 (r"\GPU Adapter Memory(*)\Dedicated Usage", self._mem)):
                st = pdh.PdhAddEnglishCounterW(self._q, path, None, ctypes.byref(handle))
                if st:
                    raise OSError(f"compteur « {path} » absent (Windows 10 1709 ou plus récent requis), code {st:#x}")
            pdh.PdhCollectQueryData(self._q)       # 1re mesure : la charge se calcule entre deux mesures
            self.ok = True
        except Exception as exc:
            self.error = str(exc)

    def _array(self, counter) -> dict[str, float]:
        ct, wt = self._ct, self._wt
        size, count = wt.DWORD(0), wt.DWORD(0)
        st = self._pdh.PdhGetFormattedCounterArrayW(counter, self.PDH_FMT_DOUBLE, ct.byref(size), ct.byref(count), None)
        if st != self.PDH_MORE_DATA or not size.value:
            return {}
        buf = (ct.c_byte * size.value)()
        if self._pdh.PdhGetFormattedCounterArrayW(counter, self.PDH_FMT_DOUBLE, ct.byref(size), ct.byref(count), buf):
            return {}
        items = ct.cast(buf, ct.POINTER(self._ITEM))
        return {items[i].szName: items[i].FmtValue.doubleValue for i in range(count.value)
                if items[i].FmtValue.CStatus in (0, 1) and items[i].szName}

    def read(self) -> list[dict]:
        """[{luid, load_percent, vram_used}] par carte, la plus utilisée en mémoire d'abord."""
        if not self.ok:
            return []
        with self._lock:
            if self._pdh.PdhCollectQueryData(self._q):
                return []
            engines, mem = self._array(self._eng), self._array(self._mem)
        per_engine: dict[tuple[str, str], float] = {}
        for name, v in engines.items():
            m = re.search(r"luid_(0x[0-9a-f]+_0x[0-9a-f]+)_phys_\d+_eng_(\d+)", name, re.I)
            if m:
                k = (m.group(1).lower(), m.group(2))
                per_engine[k] = per_engine.get(k, 0.0) + v
        load: dict[str, float] = {}
        for (luid, _), v in per_engine.items():         # comme le Gestionnaire des tâches : moteur le plus chargé
            load[luid] = max(load.get(luid, 0.0), v)
        used: dict[str, float] = {}
        for name, v in mem.items():
            m = re.search(r"luid_(0x[0-9a-f]+_0x[0-9a-f]+)", name, re.I)
            if m:
                used[m.group(1).lower()] = used.get(m.group(1).lower(), 0.0) + v
        luids = set(load) | set(used)
        rows = [{"luid": l, "load_percent": round(min(100.0, load.get(l, 0.0)), 1), "vram_used": int(used.get(l, 0))}
                for l in luids]
        return sorted(rows, key=lambda r: (-r["vram_used"], -r["load_percent"]))


def _blank_gpu(i: int, name: str, vendor: str, source: str) -> dict:
    return {"index": i, "name": name, "vendor": vendor, "source": source, "load_percent": None,
            "vram_used": None, "vram_total": None, "vram_percent": None, "temperature": None, "hotspot": None,
            "power_w": None, "power_limit_w": None, "clock_core_mhz": None, "clock_mem_mhz": None,
            "fan_percent": None, "fan_rpm": None, "throttle": None}


def _finish_gpu(g: dict) -> dict:
    if g["vram_used"] is not None and g["vram_total"]:
        g["vram_percent"] = round(g["vram_used"] / g["vram_total"] * 100, 1)
    return g


def lhm_gpus(nodes: list[dict], adapters: list[dict]) -> list[dict]:
    """Cartes graphiques lues dans LibreHardwareMonitor (AMD, Intel, NVIDIA : mêmes noms de capteurs)."""
    out = []
    for i, n in enumerate(nodes):
        g = _blank_gpu(i, n["name"], _vendor_of(n["hid"] + " " + n["img"] + " " + n["name"]), "lhm")
        by = {}
        for stype, text, value, unit in n["sensors"]:
            by.setdefault(stype, []).append((text.lower(), value, unit))

        def pick(stype, *names):
            for want in names:
                for text, v, unit in by.get(stype, []):
                    if text == want:
                        return v, unit
            return None, None

        def first(stype):
            items = by.get(stype, [])
            return (items[0][1], items[0][2]) if items else (None, None)

        load = pick("load", "gpu core", "d3d 3d")[0]
        if load is None:
            load = max((v for t, v, u in by.get("load", []) if t.startswith("d3d")), default=None)
        g["load_percent"] = load
        g["temperature"] = pick("temperature", "gpu core", "gpu")[0] or first("temperature")[0]
        g["hotspot"] = pick("temperature", "gpu hot spot", "gpu hotspot")[0]

        def mem(*names):
            for st in ("smalldata", "data"):
                v, unit = pick(st, *names)
                if v is not None:
                    mult = {"gb": 1024**3, "mb": 1024**2, "kb": 1024}.get((unit or ("gb" if st == "data" else "mb")).lower(), 1024**2)
                    return int(v * mult)
            return None
        g["vram_used"] = mem("gpu memory used", "d3d dedicated memory used")
        g["vram_total"] = mem("gpu memory total")
        g["power_w"] = pick("power", "gpu package", "gpu core", "gpu power")[0] or first("power")[0]
        cc = pick("clock", "gpu core", "gpu shader")[0]
        cm = pick("clock", "gpu memory")[0]
        g["clock_core_mhz"] = round(cc) if cc else None
        g["clock_mem_mhz"] = round(cm) if cm else None
        fp = first("control")[0]
        g["fan_percent"] = round(fp) if fp is not None else None
        g["fan_rpm"] = first("fan")[0]
        if not g["vram_total"]:                       # complète avec la taille connue de Windows
            a = next((a for a in adapters if a["name"].lower() == n["name"].lower()), None) or \
                next((a for a in adapters if a["vendor"] == g["vendor"]), None)
            if a:
                g["vram_total"] = a["vram_total"]
        out.append(_finish_gpu(g))
    # carte dédiée d'abord (la plus de VRAM)
    out.sort(key=lambda d: -(d["vram_total"] or 0))
    for i, d in enumerate(out):
        d["index"] = i
    return out


class GpuReader:
    """Choisit automatiquement la meilleure source selon la carte détectée (voir plus haut)."""

    def __init__(self) -> None:
        self.mode = None          # "nvml" ou "smi" (NVIDIA) ; sinon lhm / windows choisi à chaque lecture
        self.error = None
        self.last_source = None
        self._nvml = None
        self._handles = []
        try:
            self.adapters = detect_gpus()
        except Exception:
            self.adapters = []
        self._win = None          # compteurs Windows : créés seulement si nécessaire
        try:
            import pynvml  # fourni par le paquet nvidia-ml-py

            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            if count == 0:
                raise RuntimeError("aucun GPU NVIDIA détecté")
            self._nvml = pynvml
            self._handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(count)]
            self.mode = "nvml"
        except Exception as exc:  # NVML absent, pilote absent, pas de GPU...
            self.error = f"NVML : {exc}"
            if shutil.which("nvidia-smi"):
                self.mode = "smi"

    def read(self, lhm: dict | None = None) -> list[dict] | None:
        try:
            if self.mode == "nvml":
                self.last_source = "nvml"
                return self._read_nvml()
            if self.mode == "smi":
                self.last_source = "smi"
                return self._read_smi()
        except Exception as exc:
            self.error = str(exc)
        # AMD, Intel… : LibreHardwareMonitor s'il tourne (tout, températures comprises)
        nodes = (lhm or {}).get("gpus") or []
        if nodes:
            gpus = lhm_gpus(nodes, self.adapters)
            if gpus:
                self.last_source = "lhm"
                return gpus
        # sinon : compteurs de Windows (charge + VRAM, pas de température)
        if self.adapters:
            if self._win is None:
                self._win = WindowsGpuCounters()
            if self._win.ok:
                rows = self._win.read()
                gpus = []
                for i, a in enumerate(self.adapters):
                    r = rows[i] if i < len(rows) else {}
                    g = _blank_gpu(i, a["name"], a["vendor"], "windows")
                    g["load_percent"] = r.get("load_percent", 0.0)
                    g["vram_used"] = r.get("vram_used")
                    g["vram_total"] = a["vram_total"]
                    gpus.append(_finish_gpu(g))
                self.last_source = "windows"
                return gpus
            self.error = f"compteurs Windows indisponibles ({self._win.error})"
        elif not self.error:
            self.error = "aucune carte graphique détectée"
        self.last_source = None
        return None

    def _read_nvml(self) -> list[dict]:
        nv = self._nvml
        gpus = []
        for i, h in enumerate(self._handles):
            name = nv.nvmlDeviceGetName(h)
            if isinstance(name, bytes):
                name = name.decode(errors="replace")
            util = nv.nvmlDeviceGetUtilizationRates(h)
            mem = nv.nvmlDeviceGetMemoryInfo(h)
            def opt(fn, *args):
                try:
                    return fn(h, *args)
                except Exception:
                    return None
            temp = opt(nv.nvmlDeviceGetTemperature, nv.NVML_TEMPERATURE_GPU)
            power = opt(nv.nvmlDeviceGetPowerUsage)                 # milliwatts
            limit = opt(nv.nvmlDeviceGetEnforcedPowerLimit)         # milliwatts
            clock_core = opt(nv.nvmlDeviceGetClockInfo, nv.NVML_CLOCK_GRAPHICS)
            clock_mem = opt(nv.nvmlDeviceGetClockInfo, nv.NVML_CLOCK_MEM)
            fan = opt(nv.nvmlDeviceGetFanSpeed)
            reasons_fn = getattr(nv, "nvmlDeviceGetCurrentClocksEventReasons", None) \
                or getattr(nv, "nvmlDeviceGetCurrentClocksThrottleReasons", None)
            reasons = opt(reasons_fn) if reasons_fn else None
            gpus.append({
                "power_w": round(power / 1000, 1) if power is not None else None,
                "power_limit_w": round(limit / 1000) if limit else None,
                "clock_core_mhz": clock_core,
                "clock_mem_mhz": clock_mem,
                "fan_percent": fan,
                "throttle": _throttle_text(reasons),
                "index": i,
                "name": name,
                "vendor": "NVIDIA", "source": "nvml", "hotspot": None, "fan_rpm": None,
                "load_percent": float(util.gpu),
                "vram_used": int(mem.used),
                "vram_total": int(mem.total),
                "vram_percent": round(mem.used / mem.total * 100, 1) if mem.total else 0.0,
                "temperature": float(temp) if temp is not None else None,
            })
        return gpus

    def _read_smi(self) -> list[dict]:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, encoding="oem", errors="replace", timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if out.returncode != 0:
            raise RuntimeError(out.stderr.strip() or "nvidia-smi a échoué")
        gpus = []
        for line in out.stdout.strip().splitlines():
            idx, name, util, used, total, temp = [p.strip() for p in line.split(",")]
            used_b, total_b = float(used) * 1024**2, float(total) * 1024**2
            gpus.append({
                "index": int(idx),
                "name": name,
                "load_percent": _num(util),
                "vram_used": int(used_b),
                "vram_total": int(total_b),
                "vram_percent": round(used_b / total_b * 100, 1) if total_b else 0.0,
                "temperature": _num(temp),
                "power_w": None, "power_limit_w": None, "clock_core_mhz": None,
                "clock_mem_mhz": None, "fan_percent": None, "throttle": None,
                "vendor": "NVIDIA", "source": "smi", "hotspot": None, "fan_rpm": None,
            })
        return gpus


# Raisons de bridage des fréquences GPU (masques NVML)
THROTTLE_BITS = [
    (0x0004, "limite de puissance"),          # SW power cap
    (0x0008, "ralentissement matériel"),      # HW slowdown
    (0x0020, "bridage thermique logiciel"),   # SW thermal
    (0x0040, "bridage thermique matériel"),   # HW thermal
    (0x0080, "frein d'alimentation"),         # HW power brake
]


def _throttle_text(mask) -> str | None:
    if not mask:
        return None
    found = [label for bit, label in THROTTLE_BITS if mask & bit]
    return ", ".join(found) or None


def _num(text) -> float | None:
    """Extrait un nombre d'une chaîne ('45,3 °C', '45.3', 'N/A'...)."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(text))
    return float(m.group(0).replace(",", ".")) if m else None


# --------------------------------------------------------------------------- #
#  LibreHardwareMonitor (températures CPU / disques)
# --------------------------------------------------------------------------- #
CPU_PREFERRED = ("cpu package", "package", "core (tctl/tdie)", "tctl/tdie", "tdie", "tctl", "cpu")
DISK_IDS = ("/hdd", "/nvme", "/ssd", "/storage")
CPU_IDS = ("/intelcpu", "/amdcpu")
GPU_IDS = ("/gpu-nvidia", "/gpu-amd", "/gpu-intel", "/gpu")
BOARD_IDS = ("/lpc", "/motherboard", "/ec", "/superio")
# Nom des groupes de capteurs LHM -> type de capteur (pour les versions sans champ "Type")
GROUP_TYPES = {"temperatures": "temperature", "fans": "fan", "powers": "power",
               "clocks": "clock", "controls": "control", "loads": "load", "load": "load"}
# Icônes des nœuds « matériel » dans les anciennes versions de LHM (sans HardwareId)
HW_ICONS = ("cpu", "mainboard", "chip", "nvidia", "ati", "amd", "intel", "hdd", "ram", "nic", "bigng")


def _hw_kind(hw_id: str, img: str) -> str:
    hw_id, img = hw_id.lower(), img.lower()
    if hw_id.startswith(CPU_IDS) or "cpu.png" in img:
        return "cpu"
    if hw_id.startswith(GPU_IDS) or "nvidia" in img or "ati.png" in img:
        return "gpu"
    if hw_id.startswith(DISK_IDS) or "hdd" in img:
        return "disk"
    if hw_id.startswith(BOARD_IDS) or "mainboard" in img or "chip" in img:
        return "board"
    return "other"


def _is_hardware(node: dict) -> bool:
    """Un nœud « matériel » (CPU, GPU, disque, puce de la carte mère...) et non un groupe."""
    if not node.get("Children"):
        return False
    if node.get("HardwareId"):
        return True
    img = str(node.get("ImageURL", "")).lower()
    return any(f"/{k}" in img for k in HW_ICONS)


def parse_lhm(data: dict) -> dict:
    """Parcourt l'arbre JSON de LHM : températures, ventilateurs, puissances, fréquences."""
    cpu_sensors: list[tuple[str, float]] = []
    disks: dict[str, list[tuple[str, float]]] = {}
    fans: dict[tuple[str, str], dict] = {}
    controls: dict[tuple[str, str], float] = {}
    cpu_power = None
    cpu_clocks: list[float] = []
    gpu_nodes: dict[str, dict] = {}      # carte graphique -> capteurs (pour AMD / Intel)

    def walk(node: dict, hw: tuple[str, str] | None, group: str) -> None:
        nonlocal cpu_power
        children = node.get("Children") or []
        text = str(node.get("Text", "")).strip()
        if _is_hardware(node):
            hw = (_hw_kind(str(node.get("HardwareId", "")), str(node.get("ImageURL", ""))), text)
            if hw[0] == "gpu":
                gpu_nodes.setdefault(text, {"name": text, "hid": str(node.get("HardwareId", "")),
                                            "img": str(node.get("ImageURL", "")), "sensors": []})
        elif not children and hw:
            stype = str(node.get("Type", "")).lower() or GROUP_TYPES.get(group.lower(), "")
            if not stype and group.lower() in ("data", "smalldata"):
                stype = group.lower()
            value = _num(node.get("RawValue", node.get("Value")))
            kind, hw_name = hw
            if kind == "gpu" and value is not None and hw_name in gpu_nodes:
                um = re.search(r"\b([KMG]B)\b", str(node.get("Value", "")), re.I)
                gpu_nodes[hw_name]["sensors"].append((stype, text, value, um.group(1) if um else None))
            sid = str(node.get("SensorId", "")).lower()
            if sid.startswith(CPU_IDS):
                kind = "cpu"
            elif sid.startswith(DISK_IDS):
                kind = "disk"
            low = text.lower()
            if value is None:
                pass
            elif stype == "temperature" and 0 < value < 150:
                if kind == "cpu":
                    cpu_sensors.append((text, value))
                elif kind == "disk":
                    disks.setdefault(hw_name, []).append((text, value))
            elif stype == "fan":
                fans[(hw_name, text)] = {"kind": kind, "hardware": hw_name, "name": text,
                                         "rpm": value, "percent": None}
            elif stype == "control":
                controls[(hw_name, text)] = value
            elif stype == "power" and kind == "cpu" and low in ("cpu package", "package"):
                cpu_power = value
            elif stype == "clock" and kind == "cpu" and "core" in low and value > 0:
                cpu_clocks.append(value)
        for child in children:
            walk(child, hw, text)

    walk(data, None, "")

    cpu_temp, cpu_source = None, None
    lowered = [(n.lower(), n, v) for n, v in cpu_sensors]
    for wanted in CPU_PREFERRED:
        hit = next(((n, v) for low, n, v in lowered if low == wanted), None)
        if hit:
            cpu_source, cpu_temp = hit
            break
    if cpu_temp is None:
        cores = [v for low, n, v in lowered
                 if low.startswith(("core #", "cpu core #", "core")) and "distance" not in low
                 and "max" not in low and "average" not in low]
        if cores:
            cpu_temp = round(sum(cores) / len(cores), 1)
            cpu_source = f"moyenne de {len(cores)} cœurs"
    if cpu_temp is None:
        hit = next(((n, v) for low, n, v in lowered if "average" in low), None)
        if hit:
            cpu_source, cpu_temp = hit

    disk_temps = []
    for name, sensors in disks.items():
        # Priorité au capteur nommé "Temperature" / "Composite", sinon le premier.
        best = next((v for n, v in sensors if n.lower() in ("temperature", "composite temperature",
                                                             "composite")), sensors[0][1])
        disk_temps.append({"name": name.strip(), "temperature": best})

    fan_list = []
    for key, f in fans.items():
        f["percent"] = controls.get(key)
        fan_list.append(f)

    return {
        "cpu": cpu_temp, "cpu_source": cpu_source, "disks": disk_temps,
        "fans": fan_list,
        "gpus": list(gpu_nodes.values()),
        "cpu_power": cpu_power,
        "cpu_clock_avg": round(sum(cpu_clocks) / len(cpu_clocks)) if cpu_clocks else None,
        "cpu_clock_max": round(max(cpu_clocks)) if cpu_clocks else None,
    }


class LhmPoller:
    """Interroge LHM dans un thread pour ne jamais ralentir /api/stats."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._result = self._empty("pas encore interrogé")
        threading.Thread(target=self._loop, daemon=True).start()

    @staticmethod
    def _empty(error: str) -> dict:
        return {"available": False, "error": error, "cpu": None, "cpu_source": None,
                "disks": [], "fans": [], "gpus": [], "cpu_power": None,
                "cpu_clock_avg": None, "cpu_clock_max": None}

    def _loop(self) -> None:
        while True:
            try:
                with urllib.request.urlopen(LHM_URL, timeout=LHM_TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                parsed = parse_lhm(data)
                result = {"available": True, "error": None, **parsed}
            except Exception as exc:
                result = self._empty(f"{type(exc).__name__}: {exc}")
            with self._lock:
                self._result = result
            time.sleep(LHM_POLL_INTERVAL)

    def get(self) -> dict:
        with self._lock:
            return dict(self._result)


# --------------------------------------------------------------------------- #
#  Réseau (Ethernet / Wi-Fi)
# --------------------------------------------------------------------------- #
NET_IGNORE = ("loopback", "pseudo-interface", "isatap", "teredo", "bluetooth")


class NetMonitor:
    """Calcule les débits (octets/s) par interface entre deux lectures."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._prev = psutil.net_io_counters(pernic=True)
        self._prev_t = time.monotonic()

    def read(self) -> dict:
        with self._lock:
            now = time.monotonic()
            counters = psutil.net_io_counters(pernic=True)
            dt = max(now - self._prev_t, 1e-3)
            prev, self._prev, self._prev_t = self._prev, counters, now

        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        interfaces = []
        for name, c in counters.items():
            if any(k in name.lower() for k in NET_IGNORE):
                continue
            st = stats.get(name)
            if st is None or not st.isup:
                continue
            p = prev.get(name, c)
            ipv4 = next((a.address for a in addrs.get(name, [])
                         if a.family == socket.AF_INET), None)
            mac = next((a.address for a in addrs.get(name, [])
                        if a.family == psutil.AF_LINK), None)
            low = name.lower()
            kind = ("wifi" if ("wi-fi" in low or "wifi" in low or "wlan" in low)
                    else "virtual" if ("vethernet" in low or "virtual" in low or "vmware" in low
                                       or "vpn" in low or "tailscale" in low or "zerotier" in low)
                    else "ethernet")
            interfaces.append({
                "name": name,
                "kind": kind,
                "speed_mbps": st.speed or None,
                "ipv4": ipv4,
                "mac": mac,
                "rx_rate": max(0.0, (c.bytes_recv - p.bytes_recv) / dt),
                "tx_rate": max(0.0, (c.bytes_sent - p.bytes_sent) / dt),
                "rx_total": c.bytes_recv,
                "tx_total": c.bytes_sent,
            })

        # Interface principale : Ethernet physique avec IPv4 en priorité, puis la plus active.
        def rank(i):
            return (i["kind"] == "ethernet", i["ipv4"] is not None, i["rx_total"] + i["tx_total"])
        interfaces.sort(key=rank, reverse=True)
        return {
            "rx_rate": sum(i["rx_rate"] for i in interfaces if i["kind"] != "virtual"),
            "tx_rate": sum(i["tx_rate"] for i in interfaces if i["kind"] != "virtual"),
            "primary": interfaces[0]["name"] if interfaces else None,
            "interfaces": interfaces,
        }


# --------------------------------------------------------------------------- #
#  Processus les plus gourmands
# --------------------------------------------------------------------------- #
PROC_INTERVAL = 2.0
PROC_IGNORE = {"system idle process", "idle", "system", "registry", "memory compression"}
# Jamais fermés depuis le panel : processus vitaux de Windows (les fermer planterait ou déconnecterait la session)
PROC_PROTEGES = {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
                 "lsass.exe", "lsaiso.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe", "explorer.exe", "sihost.exe",
                 "ctfmon.exe", "spoolsv.exe", "audiodg.exe", "secure system", "memory compression", "wudfhost.exe",
                 "msmpeng.exe", "searchindexer.exe", "taskhostw.exe", "runtimebroker.exe", "startmenuexperiencehost.exe",
                 "shellexperiencehost.exe", "textinputhost.exe", "conhost.exe", "dllhost.exe", "lsm.exe", "wlanext.exe"}


class ProcessMonitor:
    """Échantillonne les processus toutes les 2 s, regroupés par nom (ex. chrome.exe ×24)."""

    def __init__(self, paused=lambda: False) -> None:
        self._is_paused = paused           # mode jeu : fourni par le serveur
        self._lock = threading.Lock()
        self._procs: dict[int, psutil.Process] = {}
        self._result = {"top_cpu": [], "top_ram": [], "count": 0}
        self._tous: list[dict] = []          # tous les groupes (classement complet)
        self._cpu_prec: dict[int, float] = {}   # temps processeur au relevé précédent (pid -> s)
        self._t_prec = 0.0
        self._ncpu = psutil.cpu_count(logical=True) or 1
        threading.Thread(target=self._loop, daemon=True).start()

    paused = False

    def _loop(self) -> None:
        samples = 0
        while True:
            # Mode jeu : on arrête de parcourir les ~300 processus (le résultat reste affiché, figé).
            # On garde au moins 2 mesures (la 1re donne toujours 0 % de CPU).
            self.paused = samples >= 2 and bool(self._is_paused())
            if not self.paused:
                try:
                    self._sample()
                    samples += 1
                except Exception:
                    pass
            time.sleep(PROC_INTERVAL)

    def _sample(self) -> None:
        groups: dict[str, dict] = {}
        count = 0
        liste = winproc.processus()          # un seul appel système (~2 ms au lieu de ~400 ms avec psutil)
        if liste is not None:
            now = time.monotonic()
            prec, dt_ = self._cpu_prec, now - self._t_prec if self._t_prec else 0
            cpu_now = {}
            for pid, _ppid, name, cpu_s, rss in liste:
                if name.lower() in PROC_IGNORE:
                    continue
                cpu_now[pid] = cpu_s
                old = prec.get(pid)
                cpu = max(0.0, (cpu_s - old) / dt_ / self._ncpu * 100) if old is not None and dt_ > 0 else 0.0
                count += 1
                g = groups.setdefault(name, {"name": name, "cpu": 0.0, "ram": 0, "count": 0, "pids": []})
                g["pids"].append(pid)
                g["cpu"] += min(cpu, 100.0)
                g["ram"] += rss
                g["count"] += 1
            self._cpu_prec, self._t_prec = cpu_now, now
        else:                                # repli : psutil, processus par processus
            alive: dict[int, psutil.Process] = {}
            for p in psutil.process_iter(["name"]):
                proc = self._procs.get(p.pid, p)
                try:
                    name = proc.info["name"] if hasattr(proc, "info") and proc.info else proc.name()
                    name = name or f"pid {p.pid}"
                    if name.lower() in PROC_IGNORE or p.pid == 0:
                        continue
                    cpu = proc.cpu_percent(None) / self._ncpu   # 0-100 % de tout le CPU
                    rss = proc.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
                    continue
                alive[p.pid] = proc
                count += 1
                g = groups.setdefault(name, {"name": name, "cpu": 0.0, "ram": 0, "count": 0, "pids": []})
                g["pids"].append(p.pid)
                g["cpu"] += cpu
                g["ram"] += rss
                g["count"] += 1
            self._procs = alive
        items = list(groups.values())
        for g in items:
            g["cpu"] = round(g["cpu"], 1)
        court = [{k: v for k, v in g.items() if k != "pids"} for g in items]
        with self._lock:
            self._tous = items
            self._result = {
                "top_cpu": sorted(court, key=lambda g: g["cpu"], reverse=True)[:6],
                "top_ram": sorted(court, key=lambda g: g["ram"], reverse=True)[:6],
                "count": count,
            }

    def get(self) -> dict:
        with self._lock:
            return {**self._result, "paused": self.paused}

    def classement(self, tri: str = "cpu", limite: int = 500) -> dict:
        """Tous les programmes (regroupés par nom), du plus gourmand au moins gourmand."""
        with self._lock:
            items = list(self._tous)
        cle = (lambda g: g["ram"]) if tri == "ram" else (lambda g: (g["cpu"], g["ram"]))
        moi = _pids_nexus()
        out = []
        for g in sorted(items, key=cle, reverse=True)[:limite]:
            n = g["name"].lower()
            out.append({"name": g["name"], "cpu": g["cpu"], "ram": g["ram"], "count": g["count"],
                        "protege": n in PROC_PROTEGES or any(pid in moi for pid in g["pids"])})
        return {"tri": "ram" if tri == "ram" else "cpu", "processus": out, "total": len(items), "paused": self.paused}

    def fermer(self, nom: str, delai: float = 3.0) -> dict:
        """Ferme TOUS les processus de ce nom (comme « Fin de tâche ») : demande polie, puis arrêt forcé après
        quelques secondes pour ceux qui résistent. Jamais un processus vital de Windows ni NEXUS lui-même."""
        nom_l = str(nom or "").strip().lower()
        if not nom_l:
            raise ValueError("nom de processus manquant")
        if nom_l in PROC_PROTEGES:
            raise ValueError(f"{nom} est un processus vital de Windows : il ne peut pas être fermé depuis le panel")
        moi = _pids_nexus()
        cibles = []
        for p in psutil.process_iter(["name"]):
            if (p.info.get("name") or "").lower() == nom_l:
                if p.pid in moi:
                    raise ValueError("c'est NEXUS lui-même : utilise plutôt la fenêtre de NEXUS pour l'arrêter")
                cibles.append(p)
        if not cibles:
            raise ValueError(f"aucun processus « {nom} » en cours")
        refuses = 0
        for p in cibles:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                refuses += 1
        _, restants = psutil.wait_procs(cibles, timeout=delai)
        for p in restants:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                refuses += 1
        _, encore = psutil.wait_procs(restants, timeout=2) if restants else ([], [])
        return {"nom": nom, "trouves": len(cibles), "fermes": len(cibles) - len(encore), "forces": len(restants),
                "refuses": len(encore)}


def _pids_nexus() -> set[int]:
    """NEXUS et ses parents (python, fenêtre de lancer.bat) : jamais proposés à la fermeture.
    (Pas ses enfants : un jeu ou une appli lancés depuis le Lanceur ou le Deck doivent pouvoir être fermés.)"""
    out = set()
    try:
        p = psutil.Process()
        out.add(p.pid)
        for a in p.parents():
            out.add(a.pid)
    except psutil.Error:
        pass
    return out


# --------------------------------------------------------------------------- #
#  Alertes
# --------------------------------------------------------------------------- #
def compute_alerts(cpu_temp, gpus, ram_percent, disks, disk_temps) -> list[dict]:
    alerts = []

    def check(key, label, value, unit, thresholds):
        if value is None:
            return
        warn, crit = thresholds
        if value >= crit:
            alerts.append({"id": key, "level": "crit", "text": f"{label} : {value:.0f}{unit}"})
        elif value >= warn:
            alerts.append({"id": key, "level": "warn", "text": f"{label} : {value:.0f}{unit}"})

    check("cpu_temp", "Température CPU", cpu_temp, " °C", ALERTS["cpu_temp"])
    for g in gpus or []:
        check(f"gpu_temp_{g['index']}", "Température GPU", g["temperature"], " °C", ALERTS["gpu_temp"])
    check("ram", "RAM utilisée", ram_percent, " %", ALERTS["ram_percent"])
    for d in disk_temps:
        check(f"disk_temp_{d['name']}", f"Température {d['name']}", d["temperature"], " °C",
              ALERTS["disk_temp"])
    for d in disks:
        free_gb = d["free"] / 1024**3
        key = f"disk_{d['mountpoint']}"
        text = f"Disque {d['mountpoint']} plein à {d['percent']:.0f} % ({free_gb:.1f} Go libres)"
        if free_gb < ALERTS["disk_free_gb"] or d["percent"] >= ALERTS["disk_percent"][1]:
            alerts.append({"id": key, "level": "crit", "text": text})
        elif d["percent"] >= ALERTS["disk_percent"][0]:
            alerts.append({"id": key, "level": "warn", "text": text})
    alerts.sort(key=lambda a: a["level"] != "crit")
    return alerts


# --------------------------------------------------------------------------- #
#  Disques
# --------------------------------------------------------------------------- #
def read_disks() -> list[dict]:
    disks = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        disks.append({
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "total": u.total,
            "used": u.used,
            "free": u.free,
            "percent": u.percent,
        })
    return disks


# --------------------------------------------------------------------------- #
#  Noms personnalisés des ventilateurs (fan_names.json)
# --------------------------------------------------------------------------- #
_fan_lock = threading.Lock()


def load_fan_names() -> dict[str, str]:
    src = FAN_NAMES_FILE if FAN_NAMES_FILE.exists() or not _OLD_FAN_NAMES_FILE.exists() else _OLD_FAN_NAMES_FILE
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_fan_name(fan_id: str, label: str) -> dict[str, str]:
    with _fan_lock:
        names = load_fan_names()
        if label:
            names[fan_id] = label
        else:
            names.pop(fan_id, None)
        FAN_NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FAN_NAMES_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(FAN_NAMES_FILE)
        return names


def label_fans(fans: list[dict]) -> list[dict]:
    names = load_fan_names()
    out = []
    for f in fans:
        fan_id = f"{f['hardware']}|{f['name']}"
        out.append({**f, "id": fan_id, "label": names.get(fan_id)})
    return out


# --------------------------------------------------------------------------- #
#  Lecture groupée (utilisée par le serveur ET par le bot Discord)
# --------------------------------------------------------------------------- #
class Sensors:
    """Démarre les lecteurs une seule fois et fournit des instantanés."""

    def __init__(self, game_paused=lambda: False) -> None:
        self.gpu = GpuReader()
        self.lhm = LhmPoller()
        self.net = NetMonitor()
        self.procs = ProcessMonitor(game_paused)
        psutil.cpu_percent(percpu=True)   # amorce : le 1er appel renvoie toujours 0

    def core(self) -> dict:
        """CPU, RAM, disques, GPU, températures : le nécessaire pour Discord et les alertes.
        (Sans le réseau ni les processus, pour ne pas fausser les mesures de la page web.)"""
        per_core = psutil.cpu_percent(percpu=True)
        vm = psutil.virtual_memory()
        temps = self.lhm.get()
        gpus = self.gpu.read(temps)
        src = self.gpu.last_source
        hint = None
        if gpus and src == "windows":
            hint = "Température, fréquences et ventilateur : installe LibreHardwareMonitor (étape 5 du README)."
        return {
            "timestamp": time.time(),
            "cpu": {
                "percent": round(sum(per_core) / len(per_core), 1) if per_core else 0.0,
                "per_core": per_core,
                "logical_cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False),
                "temperature": temps["cpu"],
                "temperature_source": temps["cpu_source"],
                "power_w": temps["cpu_power"],
                "clock_avg_mhz": temps["cpu_clock_avg"],
                "clock_max_mhz": temps["cpu_clock_max"],
            },
            "ram": {"used": vm.used, "total": vm.total, "available": vm.available, "percent": vm.percent},
            "disks": read_disks(),
            "disk_temperatures": temps["disks"],
            "gpu": {
                "available": bool(gpus),
                "error": None if gpus else (self.gpu.error or "aucune carte graphique détectée"),
                "source": src,
                "source_label": SOURCE_LABELS.get(src),
                "hint": hint,
                "adapters": [{"name": a["name"], "vendor": a["vendor"], "vram_total": a["vram_total"]}
                             for a in self.gpu.adapters],
                "devices": gpus or [],
            },
            "lhm": {"available": temps["available"], "error": temps["error"], "url": LHM_URL},
            "_fans": temps["fans"],
        }

    def hardware_report(self, wait_lhm: float = 3.0) -> list[str]:
        """Diagnostic affiché au démarrage : ce qui sera disponible ou non, en clair (jamais de plantage)."""
        lines = []
        deadline = time.time() + wait_lhm          # laisse le temps à LHM de répondre à la 1re lecture
        while time.time() < deadline and self.lhm.get()["error"] == "pas encore interrogé":
            time.sleep(.2)
        lhm = self.lhm.get()

        # --- Cartes graphiques : ce qui est branché, et comment NEXUS va les lire
        for a in self.gpu.adapters:
            vram = f", {a['vram_total'] / 1024**3:.0f} Go" if a["vram_total"] else ""
            lines.append(f"[Matériel] Carte graphique détectée : {a['name']} ({a['vendor']}{vram})")
        gpus = self.gpu.read(lhm) or []
        src = self.gpu.last_source
        if src in ("nvml", "smi"):
            lines.append(f"[Matériel] GPU lu par le {SOURCE_LABELS[src]} : charge, VRAM, température, conso, fréquences")
        elif src == "lhm":
            lines.append(f"[Matériel] GPU {', '.join(g['vendor'] for g in gpus[:1])} lu par LibreHardwareMonitor : "
                         "charge, VRAM, température, conso, fréquences, ventilateur")
        elif src == "windows":
            vendors = ", ".join(sorted({g["vendor"] for g in gpus}))
            lines.append(f"[Matériel] GPU {vendors} lu par les compteurs Windows : charge et VRAM. Pour la température, "
                         "la conso et le ventilateur, installe LibreHardwareMonitor (étape 5 du README).")
        else:
            lines.append(f"[Matériel] INFO : carte graphique non lue ({self.gpu.error or 'aucune détectée'}). "
                         "La partie GPU affichera « indisponible », tout le reste fonctionne.")
        exe = paths.INSTALL_DIR / "LibreHardwareMonitor" / "LibreHardwareMonitor.exe"
        if lhm["available"]:
            lines.append("[Matériel] LibreHardwareMonitor connecté : températures CPU, disques et ventilateurs disponibles")
        elif not exe.exists():
            lines.append("[Matériel] INFO : LibreHardwareMonitor n'est pas installé : températures CPU / disques et "
                         "ventilateurs « indisponibles ». Pour les avoir, voir l'étape 5 du README.")
        else:
            lines.append("[Matériel] INFO : LibreHardwareMonitor installé mais ne répond pas (pas encore démarré, "
                         "fenêtre administrateur refusée ou serveur web désactivé). Températures CPU « indisponibles » "
                         "en attendant ; voir la section Dépannage du README.")
        return lines

    def full(self) -> dict:
        """Tout ce qu'affiche la page web."""
        s = self.core()
        fans = s.pop("_fans")
        s["network"] = self.net.read()
        s["processes"] = self.procs.get()
        s["fans"] = label_fans(fans)
        s["alerts"] = compute_alerts(s["cpu"]["temperature"], s["gpu"]["devices"], s["ram"]["percent"],
                                     s["disks"], s["disk_temperatures"])
        return s
