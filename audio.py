"""Son : volume général de la sortie par défaut + volume / muet par application
(comme le mélangeur de volume de Windows), via pycaw (API Core Audio)."""

from __future__ import annotations

import gc
import queue
import sys
import threading
import time
from pathlib import Path

import psutil

# IMPORTANT (correctif 2.5.1) : COM en mode multi-thread (MTA). En mode par défaut (STA), un objet
# audio créé dans un thread mais libéré par le ramasse-miettes Python depuis un autre thread fait
# planter tout le serveur (violation d'accès 0xc0000005 dans _ctypes). Doit être fixé AVANT
# l'import de comtypes.
sys.coinit_flags = 0  # COINIT_MULTITHREADED

try:
    import comtypes
    import comtypes.client
    import paths

    # comtypes génère ses modules au premier usage : dans un exe installé, le dossier du
    # programme est en lecture seule. On les écrit dans les données utilisateur.
    _gen = paths.DATA_DIR / "comtypes"
    _gen.mkdir(parents=True, exist_ok=True)
    comtypes.client.gen_dir = str(_gen)

    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation

    AVAILABLE, IMPORT_ERROR = True, None
except Exception as exc:  # pycaw absent
    AVAILABLE, IMPORT_ERROR = False, str(exc)

SYSTEM_KEY = "__system__"
NICE_NAMES = {
    "discord.exe": "Discord",
    "opera.exe": "Opera GX",
    "spotify.exe": "Spotify",
    "steam.exe": "Steam",
    "steamwebhelper.exe": "Steam",
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
    "medal.exe": "Medal",
    "medalencoder.exe": "Medal (encodeur)",
    "voicemod.exe": "Voicemod",
    "riot client.exe": "Riot Client",
    "valorant-win64-shipping.exe": "VALORANT",
    "obs64.exe": "OBS Studio",
    "vlc.exe": "VLC",
    "claude.exe": "Claude",
    "rdr2.exe": "Red Dead Redemption 2",
}
STATE_TTL = 0.2  # s : l'état est relu au plus 5 fois par seconde
LEVELS_TTL = 0.04  # s : niveaux seuls (lecture légère), au plus 25 fois par seconde


def nice_name(exe: str) -> str:
    return NICE_NAMES.get(exe.lower(), Path(exe).stem)


class AudioMixer:
    """Tout passe par un thread dédié (les objets COM ne se partagent pas entre threads)."""

    def __init__(self) -> None:
        self._jobs: queue.Queue = queue.Queue()
        self._state = {"available": AVAILABLE, "error": IMPORT_ERROR, "device": None, "apps": []}
        self._state_time = 0.0
        self._seq_lock = threading.Lock()  # ordre des réglages (voir set)
        self._gen = 0  # compteur de réglages (une lecture pendant un réglage n'est pas mise en cache)
        self._last_seq: dict[tuple, int] = {}
        self.exe_paths: dict[str, str] = {}  # clé appli -> chemin de l'exe (pour l'icône)
        if AVAILABLE:
            threading.Thread(target=self._run, daemon=True).start()

    # -- thread COM ---------------------------------------------------------------
    def _run(self) -> None:
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        while True:
            fn, done = self._jobs.get()
            try:
                done["result"] = fn()  # ne renvoie que des valeurs Python simples
            except Exception as exc:
                # Message texte uniquement : l'exception garderait des objets COM vivants dans l'autre thread.
                done["error"] = f"{type(exc).__name__}: {exc}"
            del fn
            gc.collect(0)  # libère les objets COM ici, dans le thread audio
            done["event"].set()

    def _call(self, fn, timeout: float = 3.0):
        done = {"event": threading.Event()}
        self._jobs.put((fn, done))
        if not done["event"].wait(timeout):
            raise TimeoutError("le service audio ne répond pas")
        if "error" in done:
            raise RuntimeError(done["error"])
        return done.get("result")

    # -- lecture ------------------------------------------------------------------
    @staticmethod
    def _speakers():
        return AudioUtilities.GetSpeakers()

    @staticmethod
    def _device_peak(dev) -> float | None:
        imm = getattr(dev, "_dev", None)
        if imm is None:
            return None
        try:
            # QueryInterface (et non cast) : cast ne compte pas la référence, l'objet serait libéré deux fois.
            meter = imm.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None).QueryInterface(IAudioMeterInformation)
            return round(float(meter.GetPeakValue()), 3)
        except Exception:
            return None

    def _groups(self) -> dict[str, dict]:
        """Sessions audio regroupées par application (un exe = une ligne, comme Windows)."""
        groups: dict[str, dict] = {}
        for s in AudioUtilities.GetAllSessions():
            p = s.Process
            if p is None:
                if not s.ProcessId and "AudioSrv.Dll" in (s.DisplayName or ""):
                    key, name, exe = SYSTEM_KEY, "Sons système", None
                else:
                    continue
            else:
                try:
                    exe_name = p.name()
                except (psutil.Error, OSError):
                    continue
                key, name = exe_name.lower(), nice_name(exe_name)
                try:
                    exe = p.exe()
                except (psutil.Error, OSError):
                    exe = None
            g = groups.setdefault(key, {"key": key, "name": name, "exe": exe, "sessions": []})
            g["exe"] = g["exe"] or exe
            g["sessions"].append(s)
        return groups

    def _read(self) -> dict:
        dev = self._speakers()
        ep = dev.EndpointVolume
        apps = []
        meters: dict[str, list] = {}  # compteurs de niveau gardés pour _levels (thread audio seulement)
        for key, g in self._groups().items():
            vols, mutes, peaks, active = [], [], [], False
            for s in g["sessions"]:
                sv = s.SimpleAudioVolume
                vols.append(float(sv.GetMasterVolume()))
                mutes.append(bool(sv.GetMute()))
                active = active or s.State == 1
                try:
                    meter = s._ctl.QueryInterface(IAudioMeterInformation)
                    peaks.append(float(meter.GetPeakValue()))
                    meters.setdefault(key, []).append(meter)
                except Exception:
                    pass
            if g["exe"]:
                self.exe_paths[key] = g["exe"]
            apps.append(
                {
                    "key": key,
                    "name": g["name"],
                    "volume": round(max(vols), 3),
                    "muted": all(mutes),
                    "peak": round(max(peaks), 3) if peaks else 0.0,
                    "active": active,
                    "sessions": len(g["sessions"]),
                    "has_icon": bool(g["exe"]),
                }
            )
        apps.sort(key=lambda a: (a["key"] == SYSTEM_KEY, not a["active"], a["name"].lower()))
        self._meters = meters  # remplace (et libère, ici même) les anciens compteurs
        self._dev_meter = None
        imm = getattr(dev, "_dev", None)
        if imm is not None:
            try:
                self._dev_meter = imm.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None).QueryInterface(IAudioMeterInformation)
            except Exception:
                pass
        return {
            "available": True,
            "error": None,
            "device": {
                "name": dev.FriendlyName,
                "volume": round(float(ep.GetMasterVolumeLevelScalar()), 3),
                "muted": bool(ep.GetMute()),
                "peak": self._device_peak(dev),
            },
            "apps": apps,
        }

    def _levels(self) -> dict:
        """Niveaux seuls (rapide) : relit les compteurs gardés par la dernière lecture complète."""
        apps = {}
        for key, ms in getattr(self, "_meters", {}).items():
            best = 0.0
            for m in ms:
                try:
                    best = max(best, float(m.GetPeakValue()))
                except Exception:
                    pass
            apps[key] = round(best, 3)
        master = None
        if getattr(self, "_dev_meter", None) is not None:
            try:
                master = round(float(self._dev_meter.GetPeakValue()), 3)
            except Exception:
                pass
        return {"master": master, "apps": apps}

    def levels(self) -> dict:
        """Tous les niveaux en une réponse (regroupés), au plus ~25 lectures par seconde quel que soit le nombre
        d'écrans ouverts. Une lecture complète (nouvelles applis, volumes) est faite si elle date de plus de 1 s."""
        if not AVAILABLE:
            return {"master": None, "apps": {}}
        now = time.time()
        if now - self._state_time > 1.0:
            self.state()
        if now - getattr(self, "_levels_time", 0) > LEVELS_TTL:
            try:
                self._levels_cache = self._call(self._levels, timeout=1.0)
            except Exception:
                self._levels_cache = getattr(self, "_levels_cache", {"master": None, "apps": {}})
            self._levels_time = now
        return self._levels_cache

    def state(self) -> dict:
        if not AVAILABLE:
            return self._state
        if time.time() - self._state_time > STATE_TTL:
            gen = self._gen
            try:
                self._state = self._call(self._read)
            except Exception as exc:
                self._state = {**self._state, "error": f"{type(exc).__name__}: {exc}"}
            # un réglage pendant la lecture : cette lecture date peut-être d'avant lui, on ne la garde pas en cache
            self._state_time = time.time() if gen == self._gen else 0
        return self._state

    # -- écriture -------------------------------------------------------------------
    def set(self, target: str, volume: float | None = None, muted: bool | None = None, seq: int | None = None, client: str | None = None) -> bool:
        """seq / client (facultatifs) : numéro d'ordre des réglages d'une même page. Une requête plus ANCIENNE
        qui arrive après une plus récente (réseau, threads) est ignorée : le dernier volume demandé gagne."""
        if not AVAILABLE:
            return False
        if volume is not None:
            volume = max(0.0, min(1.0, float(volume)))
        if seq is not None:
            with self._seq_lock:
                k = (client or "", target)
                if seq <= self._last_seq.get(k, 0):
                    return True  # déjà dépassé par un réglage plus récent : rien à faire
                self._last_seq[k] = seq
                if len(self._last_seq) > 500:  # (pages fermées : on oublie les plus vieilles)
                    for old in list(self._last_seq)[:250]:
                        del self._last_seq[old]
                return self._apply(target, volume, muted)
        return self._apply(target, volume, muted)

    def _apply(self, target: str, volume: float | None, muted: bool | None) -> bool:

        def apply():
            if target == "master":
                ep = self._speakers().EndpointVolume
                if volume is not None:
                    ep.SetMasterVolumeLevelScalar(volume, None)
                if muted is not None:
                    ep.SetMute(1 if muted else 0, None)
                return True
            g = self._groups().get(target)
            if not g:
                return False
            for s in g["sessions"]:
                sv = s.SimpleAudioVolume
                if volume is not None:
                    sv.SetMasterVolume(volume, None)
                if muted is not None:
                    sv.SetMute(1 if muted else 0, None)
            return True

        self._gen += 1
        try:
            ok = bool(self._call(apply))
        finally:
            del apply  # la fermeture ne doit rien retenir dans ce thread
            self._gen += 1
        self._state_time = 0  # prochaine lecture à jour
        return ok
