"""Démarrage de Windows et LibreHardwareMonitor sans fenêtre d'autorisation (⚙ Réglages → Démarrage de Windows).

1) Lancer NEXUS au démarrage : valeur « NEXUS » de HKCU\\...\\Run (la même que la case de l'installeur), sans droits
   administrateur. Version exe (installée ou portable) : « NEXUS.exe --minimized » (icône près de l'horloge) ;
   version source : « pythonw.exe nexus.pyw --demarrage » (icône, sans ouvrir le navigateur).

2) LibreHardwareMonitor (températures du processeur) a besoin des droits administrateur : sans rien, Windows affiche
   sa fenêtre d'autorisation à chaque lancement de NEXUS. Sur demande, et après UNE autorisation :
   - LibreHardwareMonitor est copié dans %ProgramFiles%\\NEXUS\\LibreHardwareMonitor, dossier que seul un
     administrateur peut modifier (un programme ordinaire ne peut donc pas remplacer l'exe pour obtenir les droits) ;
   - une tâche planifiée « \\NEXUS\\LibreHardwareMonitor » (ton compte, « exécuter avec les autorisations
     maximales », sans déclencheur) le lance ; NEXUS la démarre (schtasks /run) : plus de fenêtre.
   Désactiver supprime la tâche et la copie (une autorisation aussi). Sans tâche : comportement d'origine (fenêtre).
"""

from __future__ import annotations

import base64
import ctypes
import os
import subprocess
import sys
from pathlib import Path

NOM_RUN = os.environ.get("NEXUS_TEST_RUN_NOM") or "NEXUS"  # tests : autre nom, jamais le vrai
CLE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
TACHE = r"\NEXUS\LibreHardwareMonitor"
SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class DemarrageErreur(Exception):
    pass


def _windows() -> bool:
    return os.name == "nt"


# --------------------------------------------------------------------------- #
#  Lancer NEXUS au démarrage de Windows
# --------------------------------------------------------------------------- #
def commande_autostart() -> str:
    """Commande de CETTE copie de NEXUS pour la clé Run."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --minimized'
    import paths

    py = Path(sys.executable).resolve()
    pyw = py.with_name("pythonw.exe")  # sans console (runtime\ ou .venv\Scripts\)
    return f'"{pyw if pyw.is_file() else py}" "{paths.INSTALL_DIR / "nexus.pyw"}" --demarrage'


def _lire_run() -> str | None:
    if not _windows():
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLE_RUN) as k:
            return str(winreg.QueryValueEx(k, NOM_RUN)[0])
    except OSError:
        return None


def regler_autostart(actif: bool) -> None:
    if not _windows():
        raise DemarrageErreur("réservé à Windows")
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLE_RUN, 0, winreg.KEY_SET_VALUE) as k:
            if actif:
                winreg.SetValueEx(k, NOM_RUN, 0, winreg.REG_SZ, commande_autostart())
            else:
                try:
                    winreg.DeleteValue(k, NOM_RUN)
                except FileNotFoundError:
                    pass
    except OSError as exc:
        raise DemarrageErreur(f"registre de Windows inaccessible ({exc})") from exc


# --------------------------------------------------------------------------- #
#  LibreHardwareMonitor
# --------------------------------------------------------------------------- #
def dossier_lhm() -> Path:
    import paths

    return paths.INSTALL_DIR / "LibreHardwareMonitor"


def dossier_protege() -> Path:
    return Path(os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles") or r"C:\Program Files") / "NEXUS" / "LibreHardwareMonitor"


def _schtasks(*args: str, timeout: float = 15) -> subprocess.CompletedProcess:
    exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "schtasks.exe"
    return subprocess.run([str(exe), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=SANS_FENETRE)


def tache_existe() -> bool:
    if not _windows():
        return False
    try:
        return _schtasks("/query", "/tn", TACHE).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def lhm_en_marche() -> bool:
    try:
        import psutil

        return any((p.info.get("name") or "").lower() == "librehardwaremonitor.exe" for p in psutil.process_iter(["name"]))
    except Exception:
        return False


def demarrer_lhm(dossier: Path, modele: Path | None = None, noter=print) -> None:
    """Démarre LibreHardwareMonitor s'il est livré avec NEXUS et ne tourne pas déjà : par la tâche planifiée si elle
    existe (sans fenêtre), sinon avec la fenêtre d'autorisation de Windows (comportement d'origine)."""
    if not _windows():
        return
    exe = Path(dossier) / "LibreHardwareMonitor.exe"
    if not exe.is_file() and not tache_existe():
        return
    if lhm_en_marche():
        return
    if tache_existe() and (dossier_protege() / "LibreHardwareMonitor.exe").is_file():
        try:
            if _schtasks("/run", "/tn", TACHE).returncode == 0:
                noter("démarrage de LibreHardwareMonitor (tâche planifiée, sans fenêtre d'autorisation)")
                return
        except (OSError, subprocess.TimeoutExpired):
            pass
        noter("tâche planifiée de LibreHardwareMonitor indisponible : demande d'autorisation classique")
    if not exe.is_file():
        return
    cfg = exe.with_name("LibreHardwareMonitor.config")
    if not cfg.exists() and modele and Path(modele).is_file():
        import shutil

        shutil.copyfile(modele, cfg)
    noter("démarrage de LibreHardwareMonitor (fenêtre administrateur de Windows)")
    r = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(exe), None, str(exe.parent), 7)  # 7 : réduit
    if r <= 32:
        noter("LibreHardwareMonitor non démarré (autorisation refusée ?) : températures CPU indisponibles")


def _ps(texte: str) -> str:
    return "'" + str(texte).replace("'", "''") + "'"


def _script_activer(source: Path, modele: Path | None, utilisateur: str) -> str:
    dst = dossier_protege()
    return f"""
$ErrorActionPreference = 'Stop'
$src = {_ps(source)}; $dst = {_ps(dst)}; $modele = {_ps(modele or "")}
Get-Process LibreHardwareMonitor -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -and $_.Path.StartsWith($dst, [StringComparison]::OrdinalIgnoreCase) }} | Stop-Process -Force
Start-Sleep -Milliseconds 500
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force
$cfg = Join-Path $dst 'LibreHardwareMonitor.config'
if (-not (Test-Path -LiteralPath $cfg) -and $modele -and (Test-Path -LiteralPath $modele)) {{ Copy-Item -LiteralPath $modele -Destination $cfg }}
$a = New-ScheduledTaskAction -Execute (Join-Path $dst 'LibreHardwareMonitor.exe') -WorkingDirectory $dst
$p = New-ScheduledTaskPrincipal -UserId {_ps(utilisateur)} -LogonType Interactive -RunLevel Highest
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'LibreHardwareMonitor' -TaskPath '\\NEXUS\\' -Action $a -Principal $p -Settings $s -Description 'Lancé par NEXUS sans fenêtre d''autorisation (températures du processeur). Copie protégée dans Program Files.' -Force | Out-Null
exit 0
"""


def _script_desactiver() -> str:
    dst = dossier_protege()
    return f"""
$ErrorActionPreference = 'SilentlyContinue'
$dst = {_ps(dst)}
Unregister-ScheduledTask -TaskName 'LibreHardwareMonitor' -TaskPath '\\NEXUS\\' -Confirm:$false
Get-Process LibreHardwareMonitor | Where-Object {{ $_.Path -and $_.Path.StartsWith($dst, [StringComparison]::OrdinalIgnoreCase) }} | Stop-Process -Force
Start-Sleep -Milliseconds 800
Remove-Item -LiteralPath $dst -Recurse -Force
$parent = Split-Path -Parent $dst
if ((Test-Path -LiteralPath $parent) -and -not (Get-ChildItem -LiteralPath $parent -Force)) {{ Remove-Item -LiteralPath $parent -Force }}
if (Get-ScheduledTask -TaskName 'LibreHardwareMonitor' -TaskPath '\\NEXUS\\') {{ exit 1 }}
exit 0
"""


def _executer_admin(script: str, timeout: float = 180) -> None:
    """Exécute le script PowerShell avec les droits administrateur : Windows affiche UNE fenêtre d'autorisation."""
    code = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    lanceur = (
        f"try {{ $p = Start-Process -FilePath {_ps(ps)} -Verb RunAs -WindowStyle Hidden -Wait -PassThru "
        f"-ArgumentList '-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand','{code}'; "
        "exit $p.ExitCode } catch { exit 1223 }"
    )
    try:
        r = subprocess.run(
            [str(ps), "-NoProfile", "-NonInteractive", "-Command", lanceur],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=SANS_FENETRE,
        )
    except subprocess.TimeoutExpired as exc:
        raise DemarrageErreur("pas de réponse à la fenêtre d'autorisation de Windows") from exc
    if r.returncode == 1223:
        raise DemarrageErreur("autorisation refusée dans la fenêtre de Windows : rien n'a été changé")
    if r.returncode != 0:
        raise DemarrageErreur(f"l'opération a échoué (code {r.returncode})")


def _utilisateur() -> str:
    dom, nom = os.environ.get("USERDOMAIN", ""), os.environ.get("USERNAME", "")
    if not nom:
        raise DemarrageErreur("compte Windows introuvable")
    return f"{dom}\\{nom}" if dom else nom


def regler_lhm_sans_fenetre(actif: bool) -> None:
    if not _windows():
        raise DemarrageErreur("réservé à Windows")
    if actif:
        source = dossier_lhm()
        if not (source / "LibreHardwareMonitor.exe").is_file():
            raise DemarrageErreur("LibreHardwareMonitor n'est pas installé avec NEXUS (dossier LibreHardwareMonitor)")
        import paths

        modele = paths.APP_DIR / "outils" / "LibreHardwareMonitor.config"
        _executer_admin(_script_activer(source, modele if modele.is_file() else None, _utilisateur()))
        if not tache_existe():
            raise DemarrageErreur("la tâche planifiée n'a pas été créée")
        if not lhm_en_marche():
            _schtasks("/run", "/tn", TACHE)
    else:
        if tache_existe() or dossier_protege().exists():
            _executer_admin(_script_desactiver())


# --------------------------------------------------------------------------- #
#  État pour ⚙ Réglages
# --------------------------------------------------------------------------- #
def etat() -> dict:
    run = _lire_run()
    ici = commande_autostart()
    return {
        "windows": _windows(),
        "autostart": bool(run) and run.strip().lower() == ici.strip().lower(),
        "autostart_ailleurs": bool(run) and run.strip().lower() != ici.strip().lower(),
        "lhm_present": (dossier_lhm() / "LibreHardwareMonitor.exe").is_file(),
        "lhm_sans_fenetre": tache_existe(),
        "lhm_en_marche": lhm_en_marche(),
    }
