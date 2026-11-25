"""Lanceur natif Windows de NEXUS (Phase 1).

- fenêtre native WebView2 (pywebview), pas de navigateur ni de console en version installée ;
- icône dans la zone de notification (pystray) : ouvrir, statistiques, deck, quitter ;
- fermeture de la fenêtre = réduction dans le tray (option « Quitter » pour arrêter) ;
- notifications Windows natives (winotify) pour les rappels, alertes et Philibert ;
- instance unique : un deuxième lancement ramène la fenêtre existante au premier plan ;
- port local libre + jeton, données dans %LOCALAPPDATA%\\NEXUS en version installée ;
- version portable : un fichier ``portable.flag`` à côté de l'exe met les données dans ce dossier
  et désactive le démarrage automatique ;
- démarrage automatique optionnel (HKCU\\...\\Run), uniquement en version installée.

Utilisation (source) :
    .venv\\Scripts\\python.exe nexus_launcher.py
    .venv\\Scripts\\python.exe nexus_launcher.py --minimized
    .venv\\Scripts\\python.exe nexus_launcher.py --portable
    .venv\\Scripts\\python.exe nexus_launcher.py --install-autostart
    .venv\\Scripts\\python.exe nexus_launcher.py --remove-autostart

Le serveur reste app.py ; ce fichier ne fait que l'emballer.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

APP_NAME = "NEXUS"
_MUTEX_HANDLE = None
_WINDOW = None
_WINDOW_HANDLE = None
_TRAY = None
_SERVER = None
_SERVER_THREAD = None
_QUITTING = False
_STOP = threading.Event()
_ARGS = None


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NEXUS — lanceur natif Windows")
    p.add_argument("--port", type=int, default=0, help="port local (0 = port libre)")
    p.add_argument("--minimized", action="store_true", help="démarrer réduit dans la zone de notification")
    p.add_argument("--no-tray", action="store_true", help="fermer la fenêtre quitte NEXUS (pas de tray)")
    p.add_argument("--debug", action="store_true", help="outils de développement WebView2")
    p.add_argument("--portable", action="store_true", help="données à côté de l'exécutable")
    p.add_argument("--data-dir", default="", help="dossier de données personnalisé")
    p.add_argument("--importer", default="", metavar="DOSSIER", help="reprendre les données d'une ancienne version source de NEXUS (dossier avec lancer.bat)")
    p.add_argument("--install-autostart", action="store_true", help="ajouter NEXUS au démarrage Windows")
    p.add_argument("--remove-autostart", action="store_true", help="retirer NEXUS du démarrage Windows")
    p.add_argument("--configure", action="store_true", help="ouvrir la fenêtre de configuration")
    p.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--notify-test", action="store_true", help=argparse.SUPPRESS)
    return p


# --------------------------------------------------------------------------- #
#  Mode portable
# --------------------------------------------------------------------------- #
def _portable_flag(base: Path | None = None) -> bool:
    """Vrai si ``portable.flag`` est à côté de l'exécutable (build portable)."""
    if not getattr(sys, "frozen", False):
        return False
    dossier = base or Path(sys.executable).resolve().parent
    try:
        return (Path(dossier) / "portable.flag").is_file()
    except OSError:
        return False


def _mutex_name() -> str:
    """Nom du mutex : propre à chaque dossier en portable, global sinon."""
    user = (os.environ.get("USERNAME") or "utilisateur").replace("\\", "_")
    suffixe = ""
    if os.environ.get("NEXUS_PORTABLE") == "1":
        import hashlib

        dossier = str(Path(sys.executable).resolve().parent).lower()
        suffixe = "-" + hashlib.sha1(dossier.encode("utf-8")).hexdigest()[:10]
    return f"Local\\NEXUS-{user}{suffixe}"


# --------------------------------------------------------------------------- #
#  Instance unique et activation de la fenêtre existante
# --------------------------------------------------------------------------- #
def _single_instance() -> bool:
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, _mutex_name())
    if not _MUTEX_HANDLE:
        return True
    return kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def _activate_existing() -> bool:
    """Demande à l'instance déjà lancée de montrer sa fenêtre ; repli : navigateur."""
    import paths

    runtime = paths.read_runtime()
    try:
        port = int(runtime.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    token = str(runtime.get("token") or "")
    if not port:
        return False
    url = f"http://127.0.0.1:{port}/api/activate"
    if token:
        url += "?token=" + urllib.parse.quote(token, safe="")
    for _ in range(12):
        try:
            req = urllib.request.Request(url, data=b"{}", method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as rep:
                if 200 <= rep.status < 300:
                    return True
        except Exception:
            time.sleep(0.25)
    try:  # repli : ouvrir l'interface dans le navigateur
        import webbrowser

        q = ("/?token=" + urllib.parse.quote(token, safe="")) if token else "/"
        webbrowser.open(f"http://127.0.0.1:{port}{q}")
        return True
    except Exception:
        return False


def _message(texte: str, titre: str = APP_NAME) -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.MessageBoxW(0, texte, titre, 0x40)
            return
        except Exception:
            pass
    print(texte)


# --------------------------------------------------------------------------- #
#  Première configuration (fenêtre native, sans console)
# --------------------------------------------------------------------------- #
_SETUP_WINDOW = None

_SETUP_HTML = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Configuration NEXUS</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #06060a; color: #e8f6ff; font: 15px "Segoe UI", sans-serif; }
  main { max-width: 640px; margin: 0 auto; padding: 28px 26px 34px; }
  h1 { font-size: 28px; letter-spacing: 5px; margin: 0 0 4px; color: #00ff9c; }
  h1 em { color: #ff2bd6; font-style: normal; }
  .sub { color: #8fa3b8; margin: 0 0 24px; }
  label { display: block; margin: 14px 0 5px; color: #cfe6f5; font-size: 14px; }
  input { width: 100%; padding: 9px 11px; background: #0b0b12; color: #e8f6ff;
          border: 1px solid rgba(0,255,156,.28); border-radius: 4px; font: inherit; }
  input:focus { outline: none; border-color: #00ff9c; box-shadow: 0 0 0 2px rgba(0,255,156,.14); }
  details { margin-top: 18px; border: 1px solid rgba(0,255,156,.16); padding: 10px 12px; border-radius: 4px; }
  summary { cursor: pointer; color: #8fa3b8; }
  .hint { color: #7e8fa5; font-size: 12.5px; line-height: 1.45; margin-top: 5px; }
  .row { display: flex; gap: 10px; }
  .row > div { flex: 1; }
  button { margin-top: 24px; width: 100%; padding: 12px; border: 1px solid #00ff9c;
           background: rgba(0,255,156,.10); color: #00ff9c; font: 600 16px "Segoe UI", sans-serif;
           letter-spacing: 1px; border-radius: 4px; cursor: pointer; }
  button:hover { background: rgba(0,255,156,.20); }
  .err { min-height: 22px; color: #ff6b86; margin-top: 12px; white-space: pre-wrap; }
  .ok { color: #39ff88; }
  code { color: #f6e600; }
</style></head>
<body><main>
  <h1>NEX<em>/</em>US</h1>
  <p class="sub">Première configuration — tout reste sur ce PC.</p>
  <form id="form">
    <label for="pw">Mot de passe du stream deck (obligatoire)</label>
    <input id="pw" type="password" autocomplete="new-password" required autofocus>
    <div class="hint">Au moins 6 caractères. Il protège les boutons qui lancent des applications,
      verrouillent ou mettent le PC en veille. Seule une empreinte est enregistrée.</div>
    <label for="pw2">Confirme le mot de passe</label>
    <input id="pw2" type="password" autocomplete="new-password" required>

    <details>
      <summary>Bot Discord (facultatif)</summary>
      <div class="hint">Laisse les trois champs vides pour ne pas activer le bot.</div>
      <label for="token">Jeton du bot</label>
      <input id="token" type="password" autocomplete="off" placeholder="Bot → Reset Token → Copy">
      <div class="row">
        <div><label for="uid">Ton ID utilisateur</label><input id="uid" inputmode="numeric" placeholder="17 à 20 chiffres"></div>
        <div><label for="cid">ID du salon des alertes</label><input id="cid" inputmode="numeric" placeholder="17 à 20 chiffres"></div>
      </div>
    </details>

    <details>
      <summary>Mises à jour (facultatif)</summary>
      <label for="depot">Dépôt GitHub à surveiller</label>
      <input id="depot" placeholder="proprietaire/nexus-panel" autocomplete="off">
      <div class="hint">Laisse vide pour utiliser le dépôt par défaut (fichier DEPOT). Écris « non » pour désactiver les mises à jour.</div>
    </details>

    <div id="err" class="err" role="alert"></div>
    <button type="submit">Enregistrer la configuration</button>
  </form>
</main>
<script>
  const $ = id => document.getElementById(id);
  $("form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = $("err");
    err.textContent = "";
    const v = id => $(id).value;
    if (v("pw").length < 6) { err.textContent = "Le mot de passe doit faire au moins 6 caractères."; return; }
    if (v("pw") !== v("pw2")) { err.textContent = "Les deux mots de passe ne correspondent pas."; return; }
    try {
      const r = await pywebview.api.save(v("pw"), v("pw2"), v("token"), v("uid"), v("cid"), v("depot"));
      if (r !== "ok") { err.textContent = r; return; }
      document.querySelector("main").innerHTML =
        '<h1>NEX<em>/</em>US</h1><p class="sub ok">Configuration enregistrée.<br>Relance NEXUS si sa fenêtre est déjà ouverte.</p>';
      setTimeout(() => pywebview.api.close(), 800);
    } catch (ex) {
      err.textContent = "Erreur : " + ex;
    }
  });
</script>
</body></html>
"""


class _SetupApi:
    """API JS de la fenêtre de configuration."""

    def save(self, password, confirm, token="", user_id="", channel_id="", depot=""):
        try:
            import config
            import paths
            from deck import hash_password

            password = str(password or "")
            if len(password) < 6:
                return "Le mot de passe doit faire au moins 6 caractères."
            if password != str(confirm or ""):
                return "Les deux mots de passe ne correspondent pas."

            token = str(token or "").strip()
            user_id = str(user_id or "").strip()
            channel_id = str(channel_id or "").strip()
            if any((token, user_id, channel_id)) and not all((token, user_id, channel_id)):
                return "Pour Discord, renseigne le jeton, ton ID et l'ID du salon (ou laisse tout vide)."
            if user_id and not re.fullmatch(r"\d{15,22}", user_id):
                return "L'ID utilisateur Discord doit être un nombre d'environ 18 chiffres."
            if channel_id and not re.fullmatch(r"\d{15,22}", channel_id):
                return "L'ID du salon Discord doit être un nombre d'environ 18 chiffres."

            depot = str(depot or "").strip().removeprefix("https://github.com/").strip("/")
            no_update = depot.lower() == "non"
            if no_update:
                depot = ""
            if depot and not re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}", depot):
                return "Dépôt invalide : écris proprietaire/nom (ex. mon-pseudo/nexus-panel), ou « non »."
            if not depot and not no_update:
                try:
                    if paths.DEPOT_FILE.is_file():
                        depot = paths.DEPOT_FILE.read_text(encoding="utf-8").strip()
                except OSError:
                    depot = ""

            try:
                cfg = json.loads(paths.CONFIG_FILE.read_text(encoding="utf-8-sig"))
                if not isinstance(cfg, dict):
                    cfg = {}
            except (OSError, ValueError):
                cfg = {}

            old_deck = cfg.get("deck") if isinstance(cfg.get("deck"), dict) else {}
            rate = old_deck.get("rate_limit_per_minute", config.DEFAULTS["deck"]["rate_limit_per_minute"])
            cfg["deck"] = {"password_hash": hash_password(password), "password": "", "rate_limit_per_minute": rate}
            cfg["discord"] = {"enabled": bool(token and user_id and channel_id), "token": token, "user_id": user_id, "alert_channel_id": channel_id}
            for key in ("alerts", "agenda", "journal"):
                cfg.setdefault(key, copy.deepcopy(config.DEFAULTS[key]))
            maj = dict(cfg.get("mises_a_jour") or {})
            maj.update({"depot": depot, "actif": True, "intervalle_heures": maj.get("intervalle_heures", 6), "discord": bool(maj.get("discord", False))})
            cfg["mises_a_jour"] = maj

            paths.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = paths.CONFIG_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp.replace(paths.CONFIG_FILE)
            config.ranger_secrets()  # jeton du bot : dans le gestionnaire d'identifiants de Windows
            try:  # mot de passe changé : anciennes sessions invalides
                (paths.DATA_DIR / "deck_sessions.json").unlink(missing_ok=True)
            except OSError:
                pass
            config.load(force=True)
            return "ok"
        except Exception as exc:
            return f"Configuration impossible : {type(exc).__name__}: {exc}"

    def close(self):
        if _SETUP_WINDOW is not None:
            try:
                _SETUP_WINDOW.destroy()
            except Exception:
                pass
        return "ok"


def _run_setup() -> int:
    """Ouvre la fenêtre de configuration native (processus séparé au premier lancement)."""
    global _SETUP_WINDOW
    import paths

    paths.prepare()
    import logs

    logs.install()
    try:
        import config

        config.migrer()
        config.load(force=True)
    except Exception as exc:
        print(f"[Config] AVERTISSEMENT : {exc}")
    try:
        import webview
    except Exception as exc:
        _message(f"La fenêtre de configuration nécessite pywebview.\n\n{type(exc).__name__}: {exc}\n\nLance lancer_native.bat pour l'installer.")
        return 1
    _SETUP_WINDOW = webview.create_window(
        "Configuration NEXUS",
        html=_SETUP_HTML,
        js_api=_SetupApi(),
        width=680,
        height=840,
        min_size=(560, 620),
        resizable=True,
        background_color="#06060a",
        text_select=True,
    )
    try:
        (paths.DATA_DIR / "webview").mkdir(parents=True, exist_ok=True)
        webview.start(
            debug=bool(_ARGS and _ARGS.debug),
            private_mode=False,
            storage_path=str(paths.DATA_DIR / "webview"),
            icon=str(paths.APP_DIR / "panel.ico") if (paths.APP_DIR / "panel.ico").is_file() else None,
        )
    except Exception as exc:
        _message(f"Impossible d'ouvrir la configuration : {type(exc).__name__}: {exc}")
        return 1
    return 0


# --------------------------------------------------------------------------- #
#  Démarrage automatique (HKCU)
# --------------------------------------------------------------------------- #
def _autostart_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")  # pas de console au démarrage
    if pythonw.is_file():
        exe = pythonw
    return f'"{exe}" "{Path(__file__).resolve()}" --minimized'


def _set_autostart(actif: bool) -> bool:
    if sys.platform != "win32":
        return False
    if actif and os.environ.get("NEXUS_PORTABLE") == "1":
        return False
    import winreg

    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
            if actif:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, _autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        print(f"[Démarrage] {exc}")
        return False


# --------------------------------------------------------------------------- #
#  Notifications Windows
# --------------------------------------------------------------------------- #
def _init_native_notifier():
    """Renvoie une fonction toast, ou None si winotify n'est pas disponible."""
    try:
        from winotify import Notification
    except Exception as exc:
        print(f"[Notifications] winotify indisponible : {exc}")
        return None
    import paths

    icon = paths.APP_DIR / "panel.ico"

    def notify(titre: str, texte: str) -> bool:
        try:
            n = Notification(app_id=APP_NAME, title=str(titre)[:64], msg=str(texte)[:256], icon=str(icon) if icon.is_file() else "")
            n.show()
            return True
        except Exception as exc:
            print(f"[Notifications] {exc}")
            return False

    return notify


# --------------------------------------------------------------------------- #
#  Fenêtre, tray, arrêt (Win32 pour les appels depuis le tray / HTTP)
# --------------------------------------------------------------------------- #
def _find_window_handle(require_title: bool = False) -> int | None:
    """Handle de la fenêtre NEXUS (titre « NEXUS »), sinon la plus grande fenêtre du processus.

    Attention : un lanceur python.exe de venv peut créer un processus enfant ; c'est ce
    processus qui exécute le script et possède la fenêtre, d'où l'utilisation de os.getpid()
    ici (et non du PID du lanceur).
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    user32 = ctypes.windll.user32
    pid = os.getpid()
    found: list[tuple[int, int, int]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _lparam):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid:
            r = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            area = max(0, r.right - r.left) * max(0, r.bottom - r.top)
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            titre = buf.value.strip()
            # Titre exact de la fenêtre pywebview (« NEXUS » ou « ⚠ NEXUS »).
            # Ne pas accepter « GDI+ Window (NEXUS.exe) », qui est un autre handle.
            if re.match(r"^(?:⚠\s*)?NEXUS(?:\s|$)", titre, re.I):
                found.append((1 << 60, area, int(hwnd)))
            elif not require_title:
                found.append((area, area, int(hwnd)))
        return True

    user32.EnumWindows(cb, 0)
    return max(found)[2] if found else None


def _watch_window() -> None:
    """Appelé par pywebview après le démarrage de la boucle graphique."""
    global _WINDOW_HANDLE
    for _ in range(100):
        _WINDOW_HANDLE = _find_window_handle(require_title=True)
        if _WINDOW_HANDLE:
            break
        time.sleep(0.1)
    if _WINDOW_HANDLE is None:  # titre pas encore posé : repli
        _WINDOW_HANDLE = _find_window_handle()
    if _ARGS is not None and _ARGS.minimized and _WINDOW_HANDLE and sys.platform == "win32":
        ctypes.windll.user32.ShowWindow(_WINDOW_HANDLE, 0)  # SW_HIDE : démarrage dans le tray


def _show_window(*_args) -> None:
    global _WINDOW_HANDLE
    if sys.platform == "win32":
        if _WINDOW_HANDLE and not ctypes.windll.user32.IsWindow(_WINDOW_HANDLE):
            _WINDOW_HANDLE = None
        _WINDOW_HANDLE = _WINDOW_HANDLE or _find_window_handle(require_title=True) or _find_window_handle()
        if _WINDOW_HANDLE:
            ctypes.windll.user32.ShowWindow(_WINDOW_HANDLE, 5)  # SW_SHOW
            ctypes.windll.user32.ShowWindow(_WINDOW_HANDLE, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(_WINDOW_HANDLE)
            if ctypes.windll.user32.IsWindowVisible(_WINDOW_HANDLE):
                return
    if _WINDOW is None:
        return
    try:
        _WINDOW.show()
    except Exception:
        pass
    try:
        _WINDOW.restore()
    except Exception:
        pass


def _show_tab(tab: str, *_args) -> None:
    _show_window()
    if _WINDOW is not None:  # dans un fil : ne bloque jamais le tray

        def aller():
            try:
                _WINDOW.evaluate_js(f"location.hash = '#{tab}'")
            except Exception:
                pass

        threading.Thread(target=aller, daemon=True, name="onglet").start()


def _on_closing() -> bool:
    if _QUITTING or _ARGS is None or _ARGS.no_tray or _TRAY is None:
        return True
    if sys.platform == "win32":
        handle = _WINDOW_HANDLE or _find_window_handle(require_title=True)
        if handle and ctypes.windll.user32.IsWindow(handle):
            ctypes.windll.user32.ShowWindow(handle, 0)  # SW_HIDE (le handle reste vivant)
            try:
                _TRAY.notify("NEXUS continue en arrière-plan", APP_NAME)
            except Exception:
                pass
            return False
    try:
        _WINDOW.hide()
        _TRAY.notify("NEXUS continue en arrière-plan", APP_NAME)
    except Exception:
        pass
    return False


def _quit(*_args) -> None:
    global _QUITTING
    _QUITTING = True
    _STOP.set()
    if _TRAY is not None:
        try:
            _TRAY.stop()
        except Exception:
            pass
    if sys.platform == "win32":
        handle = _WINDOW_HANDLE or _find_window_handle(require_title=True)
        if handle and ctypes.windll.user32.IsWindow(handle) and ctypes.windll.user32.PostMessageW(handle, 0x0010, 0, 0):  # WM_CLOSE
            return
    if _WINDOW is not None:
        try:
            _WINDOW.destroy()
        except Exception:
            pass


def _start_tray() -> None:
    global _TRAY
    if _ARGS is None or _ARGS.no_tray:
        return
    try:
        import pystray
        from PIL import Image

        import paths

        icon_path = paths.APP_DIR / "panel.ico"
        image = Image.open(icon_path).convert("RGBA") if icon_path.is_file() else Image.new("RGBA", (64, 64), (0, 240, 255, 255))
        menu = pystray.Menu(
            pystray.MenuItem("Ouvrir NEXUS", _show_window, default=True),
            pystray.MenuItem("Statistiques", lambda *_: _show_tab("statistiques")),
            pystray.MenuItem("Deck", lambda *_: _show_tab("deck")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter NEXUS", _quit),
        )
        _TRAY = pystray.Icon(APP_NAME, image, "NEXUS — tableau de bord", menu)
        _TRAY.run_detached()
    except Exception as exc:
        print(f"[Tray] indisponible : {exc}")
        _TRAY = None


# --------------------------------------------------------------------------- #
#  Serveur
# --------------------------------------------------------------------------- #
def _run_server(host: str, port: int) -> None:
    global _SERVER
    import uvicorn

    import app

    config = uvicorn.Config(app.app, host=host, port=port, log_level="warning", access_log=False)
    _SERVER = uvicorn.Server(config)
    _SERVER.run()


def _demarrer_lhm() -> None:
    """Démarre LibreHardwareMonitor (températures CPU, disques, ventilateurs) s'il est posé à côté de NEXUS.exe
    (dossier « LibreHardwareMonitor ») et ne tourne pas déjà. En mode source, c'est superviseur.py qui s'en charge ;
    la version exe (installée ou portable) ne le lançait jamais : elle ne profitait que d'un LHM déjà démarré.
    Windows demande l'autorisation administrateur (sans elle, pas de température processeur). Dans un fil à part :
    la demande d'autorisation ne bloque pas l'ouverture de la fenêtre."""
    if os.name != "nt":
        return
    try:
        import paths

        exe = paths.INSTALL_DIR / "LibreHardwareMonitor" / "LibreHardwareMonitor.exe"
        if not exe.is_file():
            return
        cfg = exe.with_name("LibreHardwareMonitor.config")
        modele = paths.APP_DIR / "outils" / "LibreHardwareMonitor.config"  # serveur web 8085 activé, réduit
        if not cfg.exists() and modele.is_file():
            import shutil

            shutil.copyfile(modele, cfg)
        import psutil

        if any((p.info.get("name") or "").lower() == "librehardwaremonitor.exe" for p in psutil.process_iter(["name"])):
            return
        print("[Matériel] démarrage de LibreHardwareMonitor (fenêtre administrateur de Windows)")
        r = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(exe), None, str(exe.parent), 7)  # 7 : réduit
        if r <= 32:
            print("[Matériel] LibreHardwareMonitor non démarré (autorisation refusée ?) : températures CPU indisponibles")
    except Exception as exc:
        print(f"[Matériel] LibreHardwareMonitor : démarrage impossible ({type(exc).__name__}: {exc})")


def _restart_server(port: int) -> None:
    """Accès téléphone activé ou coupé : relance le serveur web sur la nouvelle adresse (0.0.0.0 ou 127.0.0.1)
    sans quitter NEXUS. La fenêtre garde son jeton et retrouve le serveur sur le même port."""
    global _SERVER, _SERVER_THREAD
    import app

    if _QUITTING:
        return
    ancien, fil = _SERVER, _SERVER_THREAD
    if ancien is not None:
        ancien.should_exit = True
    if fil is not None:
        fil.join(10)
    app.remote_svc.active = app.remote_svc.enabled
    host = "0.0.0.0" if app.remote_svc.enabled else "127.0.0.1"
    for _essai in range(20):  # le port peut rester occupé un court instant
        _SERVER = None  # sinon _server_ready verrait l'ancien serveur « started »
        _SERVER_THREAD = threading.Thread(target=_run_server, args=(host, port), daemon=True, name="serveur")
        _SERVER_THREAD.start()
        if _server_ready(10):
            print(f"[Serveur] relancé sur {host}:{port} (accès téléphone {'activé' if app.remote_svc.active else 'désactivé'})")
            return
        time.sleep(0.5)
    print("[Serveur] ERREUR : relance impossible, redémarre NEXUS")


def _server_ready(timeout: float = 30.0) -> bool:
    fin = time.time() + timeout
    while time.time() < fin:
        if _SERVER is not None and getattr(_SERVER, "started", False):
            return True
        if _SERVER_THREAD is not None and not _SERVER_THREAD.is_alive():
            return False
        time.sleep(0.1)
    return False


def _shutdown() -> None:
    global _QUITTING
    _QUITTING = True
    if _SERVER is not None:
        try:
            _SERVER.should_exit = True
        except Exception:
            pass
    if _SERVER_THREAD is not None:
        _SERVER_THREAD.join(5)
    try:
        import app

        app.stop_services()
    except Exception:
        pass
    try:
        import paths

        paths.clear_runtime()
    except Exception:
        pass


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #
def main() -> int:
    global _ARGS, _SERVER_THREAD, _WINDOW

    _ARGS = _parser().parse_args()
    # Détecté avant les commandes --install-autostart et --configure : le drapeau
    # portable doit être connu de paths.py et du lanceur.
    if _ARGS.portable or _portable_flag():
        os.environ["NEXUS_PORTABLE"] = "1"
    if _ARGS.notify_test:
        notifier = _init_native_notifier()
        if notifier is None:
            return 1
        return 0 if notifier("NEXUS", "Notification native de test.") else 1
    if _ARGS.install_autostart:
        ok = _set_autostart(True)
        if os.environ.get("NEXUS_PORTABLE") == "1":
            print("Le démarrage automatique n'est pas disponible en version portable.")
        else:
            print("Démarrage automatique activé." if ok else "Impossible d'activer le démarrage automatique.")
        return 0 if ok else 1
    if _ARGS.remove_autostart:
        ok = _set_autostart(False)
        print("Démarrage automatique retiré." if ok else "Impossible de modifier le démarrage automatique.")
        return 0 if ok else 1

    # Les variables doivent être posées AVANT d'importer paths/app.
    if _ARGS.data_dir:
        os.environ["NEXUS_DATA_DIR"] = _ARGS.data_dir
    if _ARGS.importer:
        os.environ["NEXUS_IMPORTER"] = _ARGS.importer  # lu par paths.prepare() (copie, jamais d'écrasement)
    if _ARGS.configure:
        return _run_setup()
    if not _single_instance():
        if not _activate_existing():
            _message("NEXUS tourne déjà dans cette session.")
        return 0

    token = secrets.token_urlsafe(32)
    # Port stable (localStorage du thème, disposition, etc.) ; on bascule sur un port libre
    # seulement si le port habituel est occupé. 8765 est distinct du mode navigateur (8000).
    port = _ARGS.port or int(os.environ.get("NEXUS_PORT") or 0) or _preferred_port()
    os.environ["NEXUS_TOKEN"] = token
    os.environ["NEXUS_NATIVE"] = "1"
    os.environ["NEXUS_OPEN_BROWSER"] = "0"
    os.environ["NEXUS_PORT"] = str(port)

    import paths

    paths.prepare()  # _dire() est sûr même avec pythonw (stdout None)
    paths.clear_runtime()  # enlève un éventuel runtime.json laissé par un crash
    import logs

    log_path = logs.install()
    for message in paths.MESSAGES:  # (écrits avant l'ouverture du journal : migration des données…)
        print(message)
    import sante

    sante.install()

    import config

    try:
        config.migrer()
    except Exception as exc:
        print(f"[Config] AVERTISSEMENT : migration impossible ({exc})")
    config.load(force=True)
    for warning in config.warnings:
        print(f"[Config] AVERTISSEMENT : {warning}")

    # Première installation : la fenêtre de configuration s'ouvre dans un processus séparé
    # (pywebview ne peut démarrer qu'une fois par processus).
    from deck import Deck

    if not Deck.password_set(config.get("deck")) and not _ARGS.smoke_test:
        cmd = [sys.executable, "--configure"] if getattr(sys, "frozen", False) else [sys.executable, str(Path(__file__).resolve()), "--configure"]
        try:
            subprocess.run(cmd, cwd=str(Path(__file__).resolve().parent), timeout=900)
        except Exception as exc:
            print(f"[Config] fenêtre de configuration impossible : {type(exc).__name__}: {exc}")
        config.load(force=True)
        if not Deck.password_set(config.get("deck")):
            _message(
                "Le mot de passe du stream deck n'est pas défini.\n"
                "Le Deck restera désactivé jusqu'à la configuration "
                "(menu Démarrer → Configurer NEXUS, ou NEXUS.exe --configure)."
            )

    import app

    app.PORT = port
    try:
        app._journaliser_resultat_maj()
    except Exception:
        pass
    notifier = _init_native_notifier()
    if notifier is not None:
        app.set_native_notifier(notifier)
    app.set_activate_callback(_show_window)
    app.remote_svc.active = app.remote_svc.enabled
    host = "0.0.0.0" if app.remote_svc.enabled else "127.0.0.1"
    app.RESTART_HOOK = lambda: _restart_server(port)

    _SERVER_THREAD = threading.Thread(target=_run_server, args=(host, port), daemon=True, name="serveur")
    _SERVER_THREAD.start()
    if not _server_ready():
        _message("NEXUS n'a pas pu démarrer.\n\nConsultez le journal :\n" + str(log_path or paths.LOG_FILE))
        _shutdown()
        return 1
    paths.write_runtime(port, token)
    app.start_services()
    if not _ARGS.smoke_test:
        threading.Thread(target=_demarrer_lhm, daemon=True, name="lhm").start()

    try:
        import webview
    except Exception as exc:
        print(f"[Fenêtre] pywebview indisponible : {exc}")
        import webbrowser

        q = "/?token=" + urllib.parse.quote(token, safe="") + ("&native=1" if notifier is not None else "&native=0")
        webbrowser.open(f"http://127.0.0.1:{port}{q}")
        _message(
            "La fenêtre native n'est pas disponible (pywebview manquant).\nL'interface s'ouvre dans le navigateur.\n\nFermez cette fenêtre pour arrêter NEXUS."
        )
        try:
            while not _STOP.wait(1):
                pass
        except KeyboardInterrupt:
            pass
        _shutdown()
        return 1

    _start_tray()
    demarre_reduit = bool(_ARGS.minimized and _TRAY is not None)
    q = "/?token=" + urllib.parse.quote(token, safe="")
    q += "&native=1" if notifier is not None else "&native=0"
    url = f"http://127.0.0.1:{port}{q}"
    _WINDOW = webview.create_window(
        APP_NAME,
        url,
        width=1280,
        height=860,
        min_size=(1024, 700),
        minimized=demarre_reduit,
        focus=not demarre_reduit,
        background_color="#06060a",
        text_select=True,
    )
    _WINDOW.events.closing += _on_closing

    if _ARGS.smoke_test:

        def _fermer_bientot():
            time.sleep(4)
            _quit()

        threading.Thread(target=_fermer_bientot, daemon=True, name="smoke-test").start()

    try:
        webview_dir = paths.DATA_DIR / "webview"
        webview_dir.mkdir(parents=True, exist_ok=True)
        webview.start(
            _watch_window,
            debug=_ARGS.debug,
            private_mode=False,
            storage_path=str(webview_dir),
            icon=str(paths.APP_DIR / "panel.ico") if (paths.APP_DIR / "panel.ico").is_file() else None,
        )
    finally:
        _shutdown()
    return 0


def _port_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", int(port)))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _preferred_port() -> int:
    """Port stable pour conserver le localStorage (thème, disposition, réglages)."""
    for port in (8765, 8766, 8767):
        if _port_free(port):
            return port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", 0))
        return int(s.getsockname()[1])
    finally:
        s.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        import traceback

        traceback.print_exc()
        try:
            _shutdown()
        except Exception:
            pass
        _message(f"NEXUS n'a pas pu démarrer.\n\n{type(exc).__name__}: {exc}\n\nConsultez logs\\nexus.log pour le détail.")
        raise SystemExit(1)
