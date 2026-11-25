"""Superviseur de NEXUS, sans fenêtre noire : une icône près de l'horloge (lancé par nexus.pyw).

Il fait ce que faisait la fenêtre noire de lancer.bat :
- première configuration (configurer.py, dans une fenêtre) si config.json n'existe pas encore ;
- dépendances : réinstallées seulement si requirements.txt a changé depuis la dernière installation ;
- LibreHardwareMonitor démarré en administrateur (températures CPU / disques) s'il est présent ;
- mise à jour préparée depuis le panel (maj\\en_cours.json) mise en place par maj_demarrage.py avant le serveur ;
- serveur app.py lancé sans fenêtre, ses messages dans logs\\nexus.log ; relancé tout de suite sur le code 3
  (mise à jour, accès téléphone), relancé après un plantage (5 plantages d'affilée au plus), arrêt sur le code 0 ;
- code 4 (port déjà utilisé) : notification, puis arrêt.
L'icône : Ouvrir NEXUS (clic), Redémarrer, Ouvrir le journal, Quitter. Une seule icône par dossier NEXUS.
La logique (classe Superviseur) ne dépend pas de l'icône : outils/tests/test_superviseur.py la teste sans pystray."""

from __future__ import annotations

import ctypes
import filecmp
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Callable

BASE = Path(__file__).resolve().parent
RESTART_CODE = 3  # app.py : « relance-moi » (mise à jour, accès téléphone)
PORT_PRIS = 4  # app.py : le port est déjà utilisé
MAX_PLANTAGES = 5  # plantages d'affilée avant d'abandonner (comme lancer.bat)
STABLE_S = 60  # un serveur qui a tenu une minute remet le compteur de plantages à zéro
JOURNAL_MAX = 1_000_000  # au-delà, logs\nexus.log devient logs\nexus.1.log au démarrage
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010


def port() -> int:
    return int(os.environ.get("NEXUS_PORT") or 8000)


def adresse() -> str:
    return f"http://127.0.0.1:{port()}"


def python_console(exe: str | Path | None = None) -> Path:
    """python.exe à côté de pythonw.exe (le serveur a besoin d'une sortie, même invisible)."""
    exe = Path(exe or sys.executable)
    c = exe.with_name("python.exe")
    return c if c.exists() else exe


def env_prive(**extra: str) -> dict:
    """Environnement des processus de NEXUS : rien d'extérieur au Python de NEXUS (PYTHONPATH, paquets utilisateur)."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    env.update(PYTHONNOUSERSITE="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONUNBUFFERED="1")
    env.update(extra)
    return env


def version_nexus(base: Path = BASE) -> str:
    try:
        return (base / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "?"


def python_prive_a_jour(base: Path = BASE) -> bool:
    """runtime\\ existe et a la version voulue (outils\\python-prive.json)."""
    try:
        voulu = json.loads((base / "outils" / "python-prive.json").read_text(encoding="utf-8"))["version"]
        a = (base / "runtime" / "VERSION-PYTHON").read_text(encoding="ascii").strip()
    except (OSError, ValueError, KeyError):
        return False
    return a == voulu and (base / "runtime" / "python.exe").exists()


class Superviseur:
    def __init__(
        self,
        base: Path = BASE,
        python: str | Path | None = None,
        *,
        notifier: Callable[[str, str], None] | None = None,
        etat: Callable[[str], None] | None = None,
        ouvrir_navigateur: bool = True,
        delai_plantage: float = 3.0,
        lhm: bool = True,
        configurer: bool = True,
        prefixe: Path | None = None,
    ):
        self.base = Path(base)
        self.python = python_console(python)
        self.prefixe = prefixe  # dossier du Python (marque des dépendances) ; tests : un dossier à part
        self.notifier = notifier or (lambda titre, texte: None)
        self._etat_cb = etat or (lambda texte: None)
        self.ouvrir_navigateur = ouvrir_navigateur
        self.delai_plantage = delai_plantage
        self.lhm, self.configurer = lhm, configurer
        self.etat = "démarrage…"
        self.proc: subprocess.Popen | None = None
        self.quitter = threading.Event()
        self._relance = threading.Event()  # Redémarrer (menu) : relance au lieu de s'arrêter
        self._reprise = threading.Event()  # après 5 plantages : on attend Redémarrer ou Quitter
        self.journal = self.base / "logs" / "nexus.log"
        self.lancements = 0

    # ---- journal et état --------------------------------------------------
    def _etat(self, texte: str) -> None:
        self.etat = texte
        self._etat_cb(texte)

    def noter(self, texte: str) -> None:
        try:
            self.journal.parent.mkdir(exist_ok=True)
            with self.journal.open("a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Icône] {texte}\n")
        except OSError:
            pass

    def tourner_journal(self) -> None:
        try:
            if self.journal.exists() and self.journal.stat().st_size > JOURNAL_MAX:
                self.journal.replace(self.journal.with_name("nexus.1.log"))
        except OSError:
            pass

    def _lancer(self, args: list[str], **kw) -> subprocess.Popen:
        self.journal.parent.mkdir(exist_ok=True)
        sortie = self.journal.open("a", encoding="utf-8")
        try:
            return subprocess.Popen(
                [str(self.python), *args],
                cwd=self.base,
                stdout=sortie,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
                **kw,
            )
        finally:
            sortie.close()  # le processus enfant garde sa propre copie

    # ---- avant le serveur ---------------------------------------------------
    def preparer(self) -> bool:
        """Configuration, dépendances, LibreHardwareMonitor. False = impossible de démarrer."""
        if self.configurer and not (self.base / "config.json").exists():
            self._etat("première configuration…")
            self.noter("config.json absent : assistant de configuration")
            subprocess.run([str(self.python), "configurer.py"], cwd=self.base, env=env_prive(), creationflags=CREATE_NEW_CONSOLE)
        if not self.dependances():
            return False
        if self.lhm:
            threading.Thread(target=self.demarrer_lhm, daemon=True).start()
        return True

    def dependances(self) -> bool:
        """pip seulement si requirements.txt a changé depuis la dernière installation (marque dans le Python)."""
        req = self.base / "requirements.txt"
        prefixe = self.prefixe or Path(
            subprocess.run(
                [str(self.python), "-c", "import sys; print(sys.prefix)"], capture_output=True, text=True, env=env_prive(), creationflags=CREATE_NO_WINDOW
            ).stdout.strip()
            or self.python.parent
        )
        marque = prefixe / "requirements.installe"
        if not req.exists() or (marque.exists() and filecmp.cmp(req, marque, shallow=False)):
            return True
        self._etat("installation des dépendances…")
        self.noter("requirements.txt a changé : installation des dépendances")
        p = self._lancer(["-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", "-q", "-r", str(req)], env=env_prive())
        if p.wait() != 0:
            self.notifier("NEXUS ne peut pas démarrer", "L'installation des dépendances a échoué (connexion Internet ?). Détails : Ouvrir le journal.")
            self._etat("dépendances manquantes")
            return False
        try:
            shutil.copyfile(req, marque)
        except OSError:
            pass
        return True

    def demarrer_lhm(self) -> None:
        exe = self.base / "LibreHardwareMonitor" / "LibreHardwareMonitor.exe"
        if not exe.exists():
            return
        cfg = exe.with_name("LibreHardwareMonitor.config")
        modele = self.base / "outils" / "LibreHardwareMonitor.config"
        if not cfg.exists() and modele.exists():
            shutil.copyfile(modele, cfg)
        try:
            import psutil

            if any((p.info.get("name") or "").lower() == "librehardwaremonitor.exe" for p in psutil.process_iter(["name"])):
                return
        except Exception:
            pass
        self.noter("démarrage de LibreHardwareMonitor (fenêtre administrateur de Windows)")
        r = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(exe), None, str(exe.parent), 7)  # 7 : réduit
        if r <= 32:
            self.noter("LibreHardwareMonitor non démarré : températures CPU indisponibles")

    def appliquer_maj(self) -> None:
        if not (self.base / "maj" / "en_cours.json").exists():
            return
        self._etat("mise à jour en cours…")
        self.noter("mise à jour préparée : maj_demarrage.py")
        self._lancer(["maj_demarrage.py"], env=env_prive()).wait()

    # ---- le serveur -----------------------------------------------------------
    def lancer_serveur(self) -> subprocess.Popen:
        premiere = self.lancements == 0
        self.lancements += 1
        self.noter(f"démarrage du serveur (NEXUS {version_nexus(self.base)}, {self.python})")
        return self._lancer(["app.py"], env=env_prive(NEXUS_LANCEUR="1", NEXUS_OPEN_BROWSER="1" if premiere and self.ouvrir_navigateur else "0"))

    def boucle(self) -> int:
        """Tourne jusqu'à Quitter, un arrêt normal (code 0) ou un port déjà pris. Renvoie le dernier code."""
        self.tourner_journal()
        if not self.preparer():
            self._reprise.wait()  # dépendances manquantes : Redémarrer (réessaie) ou Quitter
            if self.quitter.is_set():
                return 1
            self._reprise.clear()
            return self.boucle()
        plantages, rc = 0, 0
        while not self.quitter.is_set():
            self.appliquer_maj()
            t0 = time.monotonic()
            self.proc = self.lancer_serveur()
            self._etat("en marche")
            rc = self.proc.wait()
            self.proc = None
            if self.quitter.is_set():
                break
            if self._relance.is_set():  # Redémarrer (menu)
                self._relance.clear()
                plantages = 0
                continue
            if rc == 0:
                self.noter("serveur arrêté normalement")
                break
            if rc == RESTART_CODE:
                self.noter("redémarrage demandé par NEXUS")
                plantages = 0
                continue
            if rc == PORT_PRIS:
                self.noter(f"port {port()} déjà utilisé")
                self.notifier("NEXUS ne peut pas démarrer", f"Le port {port()} est déjà utilisé : NEXUS est peut-être déjà ouvert ailleurs.")
                break
            plantages = 1 if time.monotonic() - t0 > STABLE_S else plantages + 1
            self.noter(f"le serveur s'est arrêté de façon inattendue (code {rc}, {plantages}/{MAX_PLANTAGES})")
            if plantages >= MAX_PLANTAGES:
                self._etat(f"arrêté ({MAX_PLANTAGES} plantages d'affilée)")
                self.notifier(
                    "NEXUS s'est arrêté", f"Le serveur s'est arrêté {MAX_PLANTAGES} fois de suite. Clic droit sur l'icône : Ouvrir le journal, ou Redémarrer."
                )
                self._reprise.wait()
                if self.quitter.is_set():
                    break
                self._reprise.clear()
                plantages = 0
                continue
            self._etat("redémarrage après un plantage…")
            self.quitter.wait(self.delai_plantage)
        return rc

    def _arreter_serveur(self) -> None:
        p = self.proc
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()

    def redemarrer(self) -> None:
        self.noter("Redémarrer (menu de l'icône)")
        if self.proc and self.proc.poll() is None:
            self._relance.set()
            self._arreter_serveur()
        else:
            self._reprise.set()

    def arreter(self) -> None:
        self.noter("Quitter NEXUS (menu de l'icône)")
        self.quitter.set()
        self._reprise.set()
        self._arreter_serveur()


# ---- une seule icône par dossier NEXUS ------------------------------------------
_verrou = None


def deja_ouvert(base: Path = BASE) -> bool:
    global _verrou
    nom = "Local\\NEXUS-icone-" + hashlib.sha1(str(base).lower().encode()).hexdigest()[:16]
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = ctypes.c_void_p
    _verrou = k32.CreateMutexW(None, False, nom)
    return k32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def main() -> int:
    if deja_ouvert():
        webbrowser.open(adresse())  # NEXUS tourne déjà : on ouvre juste le panel
        return 0
    # Python privé absent ou pas à la bonne version : lancer.bat l'installe (dans une fenêtre, une seule fois),
    # puis relance l'icône (NEXUS_DEPUIS_LANCEUR=1 : pas de boucle si l'installation a échoué)
    if os.environ.get("NEXUS_DEPUIS_LANCEUR") != "1" and not python_prive_a_jour():
        subprocess.Popen(["cmd.exe", "/c", str(BASE / "lancer.bat")], cwd=BASE, creationflags=CREATE_NEW_CONSOLE, env={**os.environ, "NEXUS_ATTENDRE": "1"})
        return 0

    import pystray
    from PIL import Image

    icone: pystray.Icon | None = None

    def maj_titre(texte: str) -> None:
        if icone is not None:
            icone.title = f"NEXUS {version_nexus()} : {texte}"[:127]
            icone.update_menu()

    def notifier(titre: str, texte: str) -> None:
        if icone is not None:
            try:
                icone.notify(texte, titre)
            except Exception:
                pass

    # NEXUS_OPEN_BROWSER=0 : ne pas ouvrir le navigateur au démarrage (copies de test, démarrage discret)
    sup = Superviseur(notifier=notifier, etat=maj_titre, ouvrir_navigateur=os.environ.get("NEXUS_OPEN_BROWSER") != "0")

    def ouvrir(_i=None, _m=None):
        webbrowser.open(adresse())

    def journal(_i=None, _m=None):
        sup.journal.parent.mkdir(exist_ok=True)
        sup.journal.touch()
        os.startfile(sup.journal)

    def quitter(i, _m=None):
        sup.arreter()
        i.stop()

    menu = pystray.Menu(
        pystray.MenuItem(lambda _m: f"NEXUS {version_nexus()} : {sup.etat}", None, enabled=False),
        pystray.MenuItem("Ouvrir NEXUS", ouvrir, default=True),
        pystray.MenuItem("Redémarrer NEXUS", lambda _i, _m: sup.redemarrer()),
        pystray.MenuItem("Ouvrir le journal", journal),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quitter NEXUS", quitter),
    )
    try:
        image = Image.open(BASE / "panel.ico")
    except OSError:
        image = Image.new("RGBA", (64, 64), (0, 200, 255, 255))
    icone = pystray.Icon("NEXUS", image, f"NEXUS {version_nexus()}", menu)

    def travail(i: pystray.Icon) -> None:
        i.visible = True
        sup.boucle()
        if not sup.quitter.is_set():  # arrêt normal ou port pris : l'icône s'en va aussi
            time.sleep(4)  # le temps de lire la notification
            i.stop()

    icone.run(setup=travail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
