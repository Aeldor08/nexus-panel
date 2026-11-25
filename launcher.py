"""Lanceur : jeux Steam / Epic détectés automatiquement + applications ajoutées à la main."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import winreg
from pathlib import Path

import store

ICON_DIR = store.DATA_DIR / "icons"
STEAM_SKIP = re.compile(r"redistributable|steamworks|proton|steamvr|steam linux runtime|"
                        r"directx|vcredist|dedicated server|soundtrack", re.I)
CREATE_NO_WINDOW = 0x08000000
DETACHED = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def _steam_path() -> Path | None:
    for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                      (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
        try:
            with winreg.OpenKey(hive, key) as k:
                for name in ("SteamPath", "InstallPath"):
                    try:
                        p = Path(winreg.QueryValueEx(k, name)[0])
                        if p.exists():
                            return p
                    except OSError:
                        pass
        except OSError:
            pass
    return None


def _vdf_values(text: str, key: str) -> list[str]:
    return [m.replace("\\\\", "\\") for m in re.findall(rf'"{key}"\s+"([^"]*)"', text, re.I)]


def steam_games() -> list[dict]:
    root = _steam_path()
    if not root:
        return []
    libs = {root}
    try:
        text = (root / "steamapps" / "libraryfolders.vdf").read_text(encoding="utf-8", errors="replace")
        libs |= {Path(p) for p in _vdf_values(text, "path")}
    except OSError:
        pass
    games = {}
    for lib in libs:
        for acf in (lib / "steamapps").glob("appmanifest_*.acf"):
            try:
                t = acf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            appid = (_vdf_values(t, "appid") or [""])[0]
            name = (_vdf_values(t, "name") or [""])[0]
            if not appid.isdigit() or not name or STEAM_SKIP.search(name):
                continue
            last = int((_vdf_values(t, "LastPlayed") or ["0"])[0] or 0)
            size = int((_vdf_values(t, "SizeOnDisk") or ["0"])[0] or 0)
            cover = _find_cover(root, appid)
            games[appid] = {
                "id": f"steam:{appid}", "kind": "game", "store": "Steam", "name": name,
                "last_played": last or None, "size": size or None,
                "cover": f"/api/launcher/cover/{appid}" if cover else None,
                "_target": f"steam://rungameid/{appid}",
            }
    return list(games.values())


def _find_cover(root: Path, appid: str) -> Path | None:
    """Image « header » (460x215) d'un jeu dans le cache local de Steam.
    Anciennes versions : librarycache/<appid>_header.jpg ou <appid>/header.jpg ;
    récentes : librarycache/<appid>/<hash>/library_header[_langue].jpg."""
    cache = root / "appcache" / "librarycache"
    for p in (cache / appid / "header.jpg", cache / f"{appid}_header.jpg"):
        if p.exists():
            return p
    folder = cache / appid
    if folder.is_dir():
        found = sorted(folder.glob("*/library_header*.jpg"), key=lambda p: "_" in p.stem.replace("library_header", ""))
        if found:
            return found[0]
    return None


def steam_cover(appid: str) -> Path | None:
    root = _steam_path()
    if not root or not appid.isdigit():
        return None
    return _find_cover(root, appid)


def epic_games() -> list[dict]:
    folder = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
    games = []
    for item in folder.glob("*.item"):
        try:
            m = json.loads(item.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            continue
        if not m.get("bIsApplication", True) or not m.get("AppName"):
            continue
        games.append({
            "id": f"epic:{m['AppName']}", "kind": "game", "store": "Epic", "name": m.get("DisplayName") or m["AppName"],
            "last_played": None, "size": m.get("InstallSize"), "cover": None,
            "_target": f"com.epicgames.launcher://apps/{m['AppName']}?action=launch&silent=true",
        })
    return games


def _default_apps() -> list[dict]:
    """Applications proposées au premier lancement, si elles sont installées."""
    la, ad = os.environ.get("LOCALAPPDATA", ""), os.environ.get("APPDATA", "")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = [
        ("Steam", "steam://open/main", []),
        ("Discord", rf"{la}\Discord\Update.exe", ["--processStart", "Discord.exe"]),
        ("Spotify", rf"{ad}\Spotify\Spotify.exe", []),
        ("Opera GX", rf"{la}\Programs\Opera GX\opera.exe", []),
        ("OBS Studio", rf"{pf}\obs-studio\bin\64bit\obs64.exe", []),
        ("Medal", rf"{la}\Medal\Medal.exe", []),
    ]
    apps = []
    for name, target, args in candidates:
        if "://" in target or Path(target).exists():
            apps.append({"id": "app:" + hashlib.md5(name.encode()).hexdigest()[:10],
                         "name": name, "target": target, "args": args})
    # Applis Microsoft Store : Spotify, Claude
    for app_id, name, package, entry in (("app:spotify", "Spotify", "SpotifyAB.SpotifyMusic", "Spotify"),
                                         ("app:claude", "Claude", "Claude", "Claude")):
        if any(a["name"] == name for a in apps):
            continue
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"(Get-AppxPackage {package}).PackageFamilyName"],
                capture_output=True, text=True, encoding="oem", errors="replace", timeout=10, creationflags=CREATE_NO_WINDOW).stdout.strip()
            if out:
                apps.append({"id": app_id, "name": name, "target": rf"shell:AppsFolder\{out}!{entry}", "args": []})
        except Exception:
            pass
    apps.append({"id": "app:claude-web", "name": "claude.ai", "target": "https://claude.ai", "args": [],
                 "icon_from": next((a["target"] for a in apps if a["id"] == "app:claude"), None)})
    return apps


def exe_icon(exe: str) -> Path | None:
    """Icône d'un .exe, extraite une fois et mise en cache en PNG dans data/icons/."""
    if not exe or not Path(exe).exists():
        return None
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    out = ICON_DIR / (hashlib.md5(exe.lower().encode()).hexdigest()[:12] + ".png")
    if not out.exists():
        # Chemins passés en base64 pour éviter tout problème d'échappement PowerShell.
        b = lambda s: base64.b64encode(s.encode("utf-16-le")).decode()
        ps = ("Add-Type -AssemblyName System.Drawing;"
              f"$e=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('{b(exe)}'));"
              f"$o=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('{b(str(out))}'));"
              "[System.Drawing.Icon]::ExtractAssociatedIcon($e).ToBitmap().Save($o,[System.Drawing.Imaging.ImageFormat]::Png)")
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=15,
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
        except Exception:
            return None
    return out if out.exists() else None


def _store_app_exe(family: str, name: str) -> str | None:
    """Exécutable d'une appli Microsoft Store (pour en extraire l'icône)."""
    if not re.fullmatch(r"[\w.\-]+", family):
        return None
    try:
        loc = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-AppxPackage | Where-Object PackageFamilyName -eq '{family}').InstallLocation"],
            capture_output=True, text=True, encoding="oem", errors="replace", timeout=10, creationflags=CREATE_NO_WINDOW).stdout.strip()
    except Exception:
        return None
    if not loc or not Path(loc).is_dir():
        return None
    exes = list(Path(loc).glob("*.exe")) + list(Path(loc).glob("app/*.exe"))
    best = next((e for e in exes if e.stem.lower() in name.lower().replace(" ", "")), None)
    return str(best or (exes[0] if exes else "")) or None


class Launcher:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: tuple[float, list[dict]] | None = None
        cfg = store.load("launcher")
        if not isinstance(cfg, dict):
            cfg = {"apps": _default_apps(), "hidden": []}
            store.save("launcher", cfg)

    def config(self) -> dict:
        cfg = store.load("launcher", {}) or {}
        cfg.setdefault("apps", [])
        cfg.setdefault("hidden", [])
        return cfg

    def _games(self) -> list[dict]:
        with self._lock:
            if self._cache and time.time() - self._cache[0] < 60:
                return self._cache[1]
            games = steam_games() + epic_games()
            games.sort(key=lambda g: (g["last_played"] or 0, g["name"].lower()), reverse=True)
            self._cache = (time.time(), games)
            return games

    def items(self) -> dict:
        cfg = self.config()
        hidden = set(cfg["hidden"])
        apps = [{"id": a["id"], "kind": "app", "name": a["name"], "target": a["target"],
                 "icon": f"/api/launcher/icon/{a['id']}"} for a in cfg["apps"]]
        games = [{k: v for k, v in g.items() if not k.startswith("_")} | {"hidden": g["id"] in hidden}
                 for g in self._games()]
        return {"games": games, "apps": apps}

    def _find(self, item_id: str) -> tuple[str, list[str]] | None:
        for g in self._games():
            if g["id"] == item_id:
                return g["_target"], []
        for a in self.config()["apps"]:
            if a["id"] == item_id:
                return a["target"], list(a.get("args") or [])
        return None

    def launch(self, item_id: str) -> bool:
        found = self._find(item_id)
        if not found:
            return False
        target, args = found
        if "://" in target or target.lower().startswith("shell:") or not args:
            os.startfile(target)   # protocoles (steam://), applis Store, .exe/.lnk sans argument
        else:
            subprocess.Popen([target, *args], cwd=str(Path(target).parent), creationflags=DETACHED,
                             close_fds=True)
        return True

    def icon(self, item_id: str) -> Path | None:
        """Icône d'une appli, extraite une fois de son .exe et mise en cache (PNG)."""
        app = next((a for a in self.config()["apps"] if a["id"] == item_id), None)
        if not app:
            return None
        target = app.get("icon_from") or app["target"]   # icon_from : icône d'une autre appli (ex. lien web)
        exe = target if target.lower().endswith((".exe", ".lnk")) and Path(target).exists() else None
        if target.lower().startswith("steam://") and _steam_path():
            exe = str(_steam_path() / "steam.exe")
        elif target.lower().startswith("shell:appsfolder\\"):
            exe = _store_app_exe(target.split("\\", 1)[1].split("!")[0], app["name"])
        if exe and exe.lower().endswith("update.exe") and "discord" in exe.lower():
            # L'icône de Discord est dans app-x.y.z\Discord.exe
            versions = sorted(Path(exe).parent.glob("app-*/Discord.exe"))
            exe = str(versions[-1]) if versions else exe
        return exe_icon(exe) if exe else None

    @staticmethod
    def new_app_id(name: str) -> str:
        return "app:" + hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:10]
