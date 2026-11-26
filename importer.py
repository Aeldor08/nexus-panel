"""Reprise des données personnelles d'un autre NEXUS de ce PC (« NEXUS.exe --importer »).

Repère les autres copies de NEXUS (portable, version source avec lancer.bat, ancien exe avec ses données à côté,
dossier de données d'une application installée) sur les disques et clés USB, puis copie leurs données dans ce
NEXUS-ci :
- configuration (mot de passe du Deck, réglages, Discord), Deck, jeux, actions ;
- data/ : base (statistiques, journal, notes des souvenirs), Philibert, agenda, rappels, photos des souvenirs,
  appareils appairés, activité, sauvegardes ;
- profils visuels ajoutés (ceux qui manquent ici ; les profils fournis, plus récents, sont gardés).

Ce qui n'est pas repris : journaux, caches (WebView2, icônes système), copies du code (versions/, maj/,
sauvegardes-maj/), LibreHardwareMonitor.

L'autre NEXUS n'est jamais modifié : il reste une sauvegarde complète (et un portable continue de marcher).
Avant d'écrire, les données actuelles de ce NEXUS sont copiées dans sauvegardes-import/<date>/ et remises en
place si la copie échoue. Les deux NEXUS doivent être fermés (une base SQLite ouverte n'est pas copiable sans
risque) : processus_ouverts() les trouve, fermer() les arrête.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import paths

# Fichiers à la racine du dossier de données
FICHIERS = ("config.json", "deck.json", "jeux.json", "fan_names.json", ".env")
# Dans data/ : caches et fichiers de la base gérés à part
DATA_IGNORES = {"webview", "comtypes", "nexus.db", "nexus.db-wal", "nexus.db-shm", "nexus.db-journal"}
SAUVEGARDES = "sauvegardes-import"

# Recherche : jamais dans ces dossiers (système, programmes, caches, contenu d'un NEXUS…)
_NE_PAS_PARCOURIR = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "$recycle.bin",
    "system volume information",
    "recovery",
    "perflogs",
    "msocache",
    "$windows.~bt",
    "$windows.~ws",
    "$sysreset",
    "windowsapps",
    "appdata",
    "node_modules",
    ".git",
    "__pycache__",
    "_internal",
    "runtime",
    ".venv",
    ".venv-build",
    "venv",
    "site-packages",
    "steamapps",
    "librehardwaremonitor",
    SAUVEGARDES,
}
_GENRES = {
    "portable": "NEXUS portable",
    "source": "NEXUS version source (lancer.bat)",
    "exe": "Ancien NEXUS (exe, données à côté)",
    "donnees": "Données d'une application NEXUS installée",
}


class ImportImpossible(Exception):
    pass


# --------------------------------------------------------------------------- #
#  Reconnaître un NEXUS
# --------------------------------------------------------------------------- #
def a_des_donnees(dossier: Path) -> bool:
    return (dossier / "config.json").is_file() or (dossier / "data" / "nexus.db").is_file()


def genre(dossier: Path) -> str | None:
    """portable / source / exe / donnees, ou None si le dossier n'est pas un NEXUS avec des données."""
    try:
        if not dossier.is_dir() or not a_des_donnees(dossier):
            return None
        if (dossier / "NEXUS.exe").is_file():
            return "portable" if (dossier / "portable.flag").is_file() else "exe"
        if (dossier / "app.py").is_file() and (dossier / "nexus.pyw").is_file():
            return "source"
        if (dossier / "data" / "nexus.db").is_file() and (dossier / "config.json").is_file():
            return "donnees"
    except OSError:
        pass
    return None


def _meme(a: Path, b: Path) -> bool:
    try:
        return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))
    except OSError:
        return False


def derniere_activite(dossier: Path) -> float:
    """Date de la dernière écriture de données (base, Philibert, activité, configuration…)."""
    data = dossier / "data"
    noms = [
        data / "nexus.db",
        data / "nexus.db-wal",
        data / "philibert.json",
        data / "activite.jsonl",
        data / "agenda.json",
        data / "rappels.json",
        dossier / "config.json",
    ]
    dates = []
    for f in noms:
        with contextlib.suppress(OSError):
            dates.append(f.stat().st_mtime)
    return max(dates, default=0.0)


def _version(dossier: Path) -> str:
    for f in (dossier / "VERSION", dossier / "_internal" / "VERSION"):
        with contextlib.suppress(OSError):
            texte = f.read_text(encoding="utf-8-sig").strip()
            if texte and len(texte) < 20:
                return texte
    return ""


def _compter_base(base: Path) -> dict:
    """Entrées du journal et sessions de statistiques (lecture seule, sur une copie : l'original n'est pas touché)."""
    res: dict = {}
    if not base.is_file():
        return res
    with tempfile.TemporaryDirectory(prefix="nexus-import-") as tmp:
        copie = Path(tmp) / "nexus.db"
        try:
            shutil.copy2(base, copie)
            wal = base.with_name(base.name + "-wal")
            if wal.is_file():
                shutil.copy2(wal, copie.with_name("nexus.db-wal"))
            con = sqlite3.connect(copie)
            try:
                for table, cle in (("journal", "journal"), ("sessions", "sessions"), ("photos", "photos")):
                    with contextlib.suppress(sqlite3.Error):
                        res[cle] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            finally:
                con.close()
        except (OSError, sqlite3.Error):
            pass
    return res


def decrire(dossier: Path) -> dict:
    """Résumé lisible d'un NEXUS (pour la fenêtre d'import)."""
    g = genre(dossier) or ""
    data = dossier / "data"
    contenu = []
    if (dossier / "config.json").is_file():
        contenu.append("configuration et mot de passe du Deck")
    base = _compter_base(data / "nexus.db")
    if base:
        contenu.append(f"journal ({base.get('journal', 0)} entrées)")
        contenu.append(f"statistiques ({base.get('sessions', 0)} sessions)")
    if (data / "philibert.json").is_file():
        contenu.append("Philibert")
    if (data / "agenda.json").is_file():
        contenu.append("agenda")
    souvenirs = data / "souvenirs"
    if souvenirs.is_dir():
        with contextlib.suppress(OSError):
            n = sum(1 for f in souvenirs.rglob("*") if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
            if n:
                contenu.append(f"souvenirs ({n} photos)")
    if (data / "remote.json").is_file():
        contenu.append("téléphones appairés")
    activite = derniere_activite(dossier)
    return {
        "chemin": str(dossier),
        "genre": g,
        "libelle": _GENRES.get(g, "NEXUS"),
        "version": _version(dossier),
        "activite": activite,
        "activite_texte": time.strftime("%d/%m/%Y à %H:%M", time.localtime(activite)) if activite else "inconnue",
        "contenu": contenu,
    }


# --------------------------------------------------------------------------- #
#  Chercher les autres NEXUS du PC
# --------------------------------------------------------------------------- #
def _lecteurs() -> list[Path]:
    """Disques fixes et amovibles (clé USB avec un portable), pas les lecteurs réseau ni les CD."""
    if os.name != "nt":
        return []
    import ctypes

    lecteurs = []
    masque = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if masque & (1 << i):
            racine = f"{chr(65 + i)}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(racine) in (2, 3):  # DRIVE_REMOVABLE, DRIVE_FIXED
                lecteurs.append(Path(racine))
    return lecteurs


def _est_lien(entree: os.DirEntry) -> bool:
    try:
        if entree.is_symlink():
            return True
        attributs = getattr(entree.stat(follow_symlinks=False), "st_file_attributes", 0)
        return bool(attributs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT (jonctions « Application Data »…)
    except OSError:
        return True


def _parcourir(racine: Path, profondeur: int, trouves: dict, fin: float) -> None:
    pile = [(racine, 0)]
    while pile and time.monotonic() < fin:
        dossier, niveau = pile.pop()
        if genre(dossier):
            with contextlib.suppress(OSError):
                trouves.setdefault(os.path.normcase(str(dossier.resolve())), dossier)
            continue  # (ses sous-dossiers sont des sauvegardes de ce même NEXUS)
        if niveau >= profondeur:
            continue
        try:
            with os.scandir(dossier) as it:
                for e in it:
                    if e.name.lower() in _NE_PAS_PARCOURIR or e.name.startswith((".", "$")):
                        continue
                    with contextlib.suppress(OSError):
                        if e.is_dir(follow_symlinks=False) and not _est_lien(e):
                            pile.append((Path(e.path), niveau + 1))
        except OSError:
            continue


def _indices() -> list[Path]:
    """Emplacements connus : processus NEXUS ouverts, raccourci du Bureau, dossier noté par l'installeur,
    dossier de données de l'application installée."""
    res: list[Path] = []
    with contextlib.suppress(Exception):
        import psutil

        for p in psutil.process_iter(["name", "exe", "cwd"]):
            info = p.info
            if (info.get("name") or "").lower() == "nexus.exe" and info.get("exe"):
                res.append(Path(info["exe"]).parent)
            elif (info.get("name") or "").lower().startswith("python") and info.get("cwd"):
                res.append(Path(info["cwd"]))
    with contextlib.suppress(Exception):
        r = paths._raccourci_bureau()
        if r:
            res.append(r)
    with contextlib.suppress(Exception):
        r = paths._ancienne_version_notee()
        if r:
            res.append(r)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        res.append(Path(local) / paths.APP_NAME)
    return res


def chercher(racines: list[Path] | None = None, *, destination: Path | None = None, duree_max: float = 20.0) -> list[dict]:
    """Les autres NEXUS avec des données, le plus récemment utilisé d'abord (jamais celui-ci)."""
    destination = destination or paths.USER_ROOT
    fin = time.monotonic() + duree_max
    trouves: dict[str, Path] = {}
    if racines is None:
        for d in _indices():
            _parcourir(d, 0, trouves, fin)
        _parcourir(Path.home(), 5, trouves, fin)
        for lecteur in _lecteurs():
            _parcourir(lecteur, 4, trouves, fin)  # (ex. D:\Jeux\Outils\NEXUS-1.8.0\NEXUS-1.8.0 : 2 s ici)
    else:
        for r in racines:
            _parcourir(r, 4, trouves, fin)
    exclus = [destination, paths.INSTALL_DIR]
    liste = [decrire(d) for d in trouves.values() if not any(_meme(d, x) for x in exclus)]
    return sorted(liste, key=lambda c: c["activite"], reverse=True)


# --------------------------------------------------------------------------- #
#  NEXUS ouverts
# --------------------------------------------------------------------------- #
def _moi() -> set[int]:
    """Ce processus, et son lanceur s'il exécute le même programme (python.exe d'un environnement virtuel)."""
    moi = {os.getpid()}
    with contextlib.suppress(Exception):
        import psutil

        for parent in psutil.Process().parents():
            if os.path.normcase(parent.exe()) == os.path.normcase(sys.executable):
                moi.add(parent.pid)
    return moi


def processus_ouverts(dossiers: list[Path]) -> list[dict]:
    """Processus NEXUS lancés depuis ces dossiers (exe, ou Python de la version source). Jamais celui-ci."""
    try:
        import psutil
    except ImportError:
        return []
    cibles = [os.path.normcase(str(d.resolve())) for d in dossiers]
    moi = _moi()
    res = []
    for p in psutil.process_iter(["pid", "name", "exe", "cwd", "cmdline"]):
        info = p.info
        if info["pid"] in moi:
            continue
        nom = (info.get("name") or "").lower()
        exe = info.get("exe") or ""
        lien = ""
        if nom == "nexus.exe" and exe:
            lien = os.path.normcase(str(Path(exe).parent))
        elif nom.startswith("python"):
            lien = os.path.normcase(info.get("cwd") or "")
            if lien not in cibles:
                ligne = os.path.normcase(" ".join(info.get("cmdline") or []))
                lien = next((c for c in cibles if c and c in ligne), lien)
        if lien and lien in cibles:
            res.append({"pid": info["pid"], "nom": info.get("name") or "", "chemin": exe})
    return res


def fermer(pids: list[int], delai: float = 8.0) -> list[int]:
    """Arrête ces processus (et leurs enfants). Renvoie ceux qui tournent encore."""
    import psutil

    procs = []
    for pid in pids:
        with contextlib.suppress(psutil.Error):
            p = psutil.Process(pid)
            procs.extend(p.children(recursive=True))
            procs.append(p)
    for p in procs:
        with contextlib.suppress(psutil.Error):
            p.terminate()
    _, restants = psutil.wait_procs(procs, timeout=delai)
    return [p.pid for p in restants]


def _dossiers_lances(dossier: Path) -> list[Path]:
    """Dossiers dont un processus ouvert utiliserait ces données (dossier lui-même, et l'exe de l'application
    installée pour son dossier de données)."""
    res = [dossier]
    if _meme(dossier, paths.USER_ROOT) and not _meme(paths.INSTALL_DIR, paths.USER_ROOT):
        res.append(paths.INSTALL_DIR)
    return res


def _selon_runtime(dossier: Path) -> list[dict]:
    """NEXUS qui utilise ce dossier de données d'après son runtime.json (pid écrit au démarrage du serveur),
    même si son exe est ailleurs (application installée dans un autre dossier)."""
    try:
        import psutil

        pid = int(json.loads((dossier / "runtime.json").read_text(encoding="utf-8")).get("pid") or 0)
        if not pid or pid in _moi():
            return []
        p = psutil.Process(pid)
        nom = p.name()
        if nom.lower() == "nexus.exe" or nom.lower().startswith("python"):
            return [{"pid": pid, "nom": nom, "chemin": p.exe()}]
    except Exception:
        pass
    return []


def ouverts_pour(source: Path, destination: Path | None = None) -> list[dict]:
    destination = destination or paths.USER_ROOT
    res = processus_ouverts(_dossiers_lances(source) + _dossiers_lances(destination))
    for d in (source, destination):
        res += [p for p in _selon_runtime(d) if all(p["pid"] != q["pid"] for q in res)]
    return res


# --------------------------------------------------------------------------- #
#  Copie
# --------------------------------------------------------------------------- #
def _copier_base(src: Path, dst: Path) -> None:
    """Copie cohérente de la base SQLite (avec son journal WAL) sans ouvrir l'original : copie brute dans un
    dossier temporaire, ouverture de la copie (le WAL y est appliqué), vérification, puis sauvegarde SQLite."""
    with tempfile.TemporaryDirectory(prefix="nexus-import-") as tmp:
        copie = Path(tmp) / "nexus.db"
        shutil.copy2(src, copie)
        wal = src.with_name(src.name + "-wal")
        if wal.is_file():
            shutil.copy2(wal, copie.with_name("nexus.db-wal"))
        lu = sqlite3.connect(copie)
        try:
            verif = lu.execute("PRAGMA quick_check").fetchone()[0]
            if verif != "ok":
                raise ImportImpossible(f"la base de l'autre NEXUS est abîmée ({verif})")
            neuf = dst.with_name("nexus.db.import")
            neuf.unlink(missing_ok=True)
            ecrit = sqlite3.connect(neuf)
            try:
                lu.backup(ecrit)
            finally:
                ecrit.close()
        finally:
            lu.close()
    for suffixe in ("", "-wal", "-shm", "-journal"):  # un ancien WAL serait rejoué sur la nouvelle base
        dst.with_name(dst.name + suffixe).unlink(missing_ok=True)
    neuf.replace(dst)


def _remplacer(src: Path, dst: Path) -> None:
    if dst.is_dir() and not dst.is_symlink():
        shutil.rmtree(dst)
    elif dst.exists():
        dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def _sauvegarder(destination: Path) -> Path:
    """Copie des données actuelles de ce NEXUS (tout ce que l'import peut remplacer)."""
    racine = destination / SAUVEGARDES / time.strftime("%Y-%m-%d_%H-%M-%S")
    dossier, n = racine, 1
    while dossier.exists():  # (deux imports dans la même seconde)
        n += 1
        dossier = racine.with_name(f"{racine.name}_{n}")
    dossier.mkdir(parents=True)
    for nom in FICHIERS:
        if (destination / nom).is_file():
            shutil.copy2(destination / nom, dossier / nom)
    data = destination / "data"
    if data.is_dir():
        (dossier / "data").mkdir()
        for e in data.iterdir():
            if e.name in DATA_IGNORES or e.name.endswith(".import"):
                continue
            if e.is_dir():
                shutil.copytree(e, dossier / "data" / e.name)
            else:
                shutil.copy2(e, dossier / "data" / e.name)
        if (data / "nexus.db").is_file():
            _copier_base(data / "nexus.db", dossier / "data" / "nexus.db")
    if (destination / "actions").is_dir():
        shutil.copytree(destination / "actions", dossier / "actions")
    return dossier


def _restaurer(sauvegarde: Path, destination: Path, touches: list[str]) -> None:
    """Remet les données d'avant l'import et retire ce que l'import avait ajouté."""
    for rel in touches:
        rel = rel.rstrip("/")
        if rel != "actions" and not (sauvegarde / rel).exists():
            cible = destination / rel
            if cible.is_dir():
                shutil.rmtree(cible, ignore_errors=True)
            else:
                cible.unlink(missing_ok=True)
    for e in sauvegarde.iterdir():
        if e.name == "data":
            for f in e.iterdir():
                if f.name == "nexus.db":
                    _copier_base(f, destination / "data" / "nexus.db")
                else:
                    _remplacer(f, destination / "data" / f.name)
        elif e.name != "IMPORT.txt":
            _remplacer(e, destination / e.name)


def importer(source: Path, destination: Path | None = None, *, verifier_ouverts: bool = True) -> dict:
    """Copie les données de `source` dans `destination` (ce NEXUS par défaut), en remplaçant les siennes.
    Renvoie {"copies": [...], "sauvegarde": chemin}. Lève ImportImpossible avec un message lisible."""
    source = Path(source)
    destination = Path(destination or paths.USER_ROOT)
    g = genre(source)
    if not g:
        raise ImportImpossible(f"{source} n'est pas un dossier NEXUS avec des données (config.json ou data\\nexus.db).")
    if _meme(source, destination):
        raise ImportImpossible("C'est le dossier de données de ce NEXUS-ci.")
    if verifier_ouverts and ouverts_pour(source, destination):
        raise ImportImpossible("Ferme d'abord les NEXUS ouverts (l'autre et celui-ci).")

    destination.mkdir(parents=True, exist_ok=True)
    sauvegarde = _sauvegarder(destination)
    copies: list[str] = []
    try:
        for nom in FICHIERS:
            if (source / nom).is_file():
                copies.append(nom)
                _remplacer(source / nom, destination / nom)
        data_src, data_dst = source / "data", destination / "data"
        data_dst.mkdir(parents=True, exist_ok=True)
        if (data_src / "nexus.db").is_file():
            copies.append("data/nexus.db")
            _copier_base(data_src / "nexus.db", data_dst / "nexus.db")
        if data_src.is_dir():
            for e in sorted(data_src.iterdir()):
                if e.name in DATA_IGNORES or e.name.endswith(".import"):
                    continue
                copies.append(f"data/{e.name}" + ("/" if e.is_dir() else ""))
                _remplacer(e, data_dst / e.name)
        if (source / "actions").is_dir():
            copies.append("actions/")
            shutil.copytree(source / "actions", destination / "actions", dirs_exist_ok=True)
        profils = source / "profils"
        if profils.is_dir():
            for p in sorted(profils.iterdir()):
                if p.is_dir() and not p.name.startswith(("_", ".")) and not (destination / "profils" / p.name).exists():
                    copies.append(f"profils/{p.name}/")
                    shutil.copytree(p, destination / "profils" / p.name)
    except Exception as exc:
        try:
            _restaurer(sauvegarde, destination, copies)
        except Exception as exc2:
            raise ImportImpossible(
                f"Copie interrompue ({type(exc).__name__}: {exc}) et remise en place incomplète ({exc2}). Tes anciennes données sont dans {sauvegarde}."
            ) from exc
        raise ImportImpossible(f"Copie interrompue, rien n'a changé ici ({type(exc).__name__}: {exc}).") from exc

    marqueur = destination / ".layout-v2"  # (évite la reprise automatique du premier lancement : paths.py)
    if not marqueur.exists():
        marqueur.write_text(f"Import depuis {source} le {time.strftime('%Y-%m-%d %H:%M:%S')}\n", encoding="utf-8")
    (sauvegarde / "IMPORT.txt").write_text(
        json.dumps(
            {"source": str(source), "genre": g, "date": time.strftime("%Y-%m-%d %H:%M:%S"), "copies": copies},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if _meme(destination, paths.USER_ROOT):
        with contextlib.suppress(Exception):
            import config

            config.ranger_secrets()  # jeton du bot en clair dans l'ancienne configuration → gestionnaire Windows
    return {"copies": copies, "sauvegarde": str(sauvegarde)}
