"""Mises à jour de la version gelée (.exe) : installeur Inno Setup, ou archive portable.

En mode source, NEXUS met à jour son code depuis l'archive ZIP de la release.
En mode gelé, ce n'est pas possible : l'exécutable et son dossier ``_internal``
sont remplacés par un installeur. Ce module prépare cette mise à jour :

- téléchargement de ``NEXUS-x.y.z-Setup.exe`` et de son fichier ``.sha256`` ;
- vérification du SHA256, puis de la signature Authenticode (si présente) ;
- sauvegarde complète de l'installation actuelle (exe + ``_internal``) ;
- écriture d'un travail JSON et lancement d'un helper PowerShell caché.

Le helper ferme NEXUS, lance l'installeur en mode silencieux, relance NEXUS
et attend le marqueur ``maj/demarrage_ok.json``. Si la nouvelle version ne
démarre pas, il remet la sauvegarde en place et relance l'ancienne version.

Version portable : même chemin, sans installeur. On télécharge
``NEXUS-Portable-x.y.z.zip`` (pré-release ``portable-x.y.z``), on vérifie son SHA256
et son contenu, on l'extrait dans ``maj/natif/x.y.z``, puis le helper remplace
seulement les fichiers du programme (``NEXUS.exe``, ``_internal``…) dans le dossier
du portable. Les données posées à côté (``config.json``, ``data``, ``profils``…)
ne sont jamais touchées, ni par la mise à jour ni par un retour en arrière.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import config
import paths
import version as version_mod

INSTALLATEUR_RE = re.compile(r"^NEXUS-(\d+\.\d+\.\d+)-Setup\.exe$", re.I)
MAX_FICHIERS_PORTABLE = 20000
# Fichiers du programme portable (racine de NEXUS-Portable-x.y.z.zip) : les seuls que la mise à jour du
# portable sauvegarde, remplace ou remet en place. Tout le reste du dossier (données, LibreHardwareMonitor,
# dossiers perso…) n'est jamais touché.
PROGRAMME_PORTABLE = ("NEXUS.exe", "_internal", "Lancer NEXUS.bat", "LISEZMOI.txt", "portable.flag")
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

NATIF_DIR = paths.MAJ_DIR / "natif"
ROLLBACK_DIR = paths.MAJ_DIR / "rollback"
JOB_FILE = paths.MAJ_DIR / "natif.json"
MARKER_FILE = paths.MAJ_DIR / "demarrage_ok.json"
LOG_FILE = paths.MAJ_DIR / "natif.log"
RESULT_FILE = paths.MAJ_DIR / "resultat.json"
HELPER_NAME = "appliquer_maj.ps1"

# Jamais copiés dans la sauvegarde d'installation : ce sont des données
# personnelles, pas des fichiers du programme. Les noms ne s'appliquent qu'à
# la racine de l'installation, pour ne pas exclure ``_internal/profils``.
PROTEGES_RACINE = {
    "data", "logs", "maj", "sauvegardes-maj", "versions", "profils", "actions",
    "config.json", "deck.json", "jeux.json", "fan_names.json", "runtime.json", ".env",
    ".venv", "venv", "backups", "sauvegardes", "partage", "reference", "references",
    "dist", "build", ".git", ".ruff_cache", ".pytest_cache",
}


class NatifError(Exception):
    pass


# --------------------------------------------------------------------------- #
#  Outils
# --------------------------------------------------------------------------- #
def _lire(path: Path, defaut=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return defaut


def _ecrire(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def sha256_fichier(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def vtuple(v: str) -> tuple[int, int, int]:
    m = SEMVER_RE.match(str(v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def est_portable() -> bool:
    """Version gelée dont les données sont à côté de l'exe (pas d'installeur)."""
    try:
        return paths.FROZEN and paths.INSTALL_DIR.resolve() == paths.USER_ROOT.resolve()
    except OSError:
        return False


def peut_utiliser_installeur() -> bool:
    return paths.FROZEN and not est_portable()


# --------------------------------------------------------------------------- #
#  Choix des fichiers de la release
# --------------------------------------------------------------------------- #
def choisir_assets(assets: list[dict]) -> dict:
    """Sélectionne l'installeur Windows et son .sha256, sinon l'archive source."""
    installateur = sha_installateur = archive = sha_archive = None
    for asset in assets:
        nom = str(asset.get("name") or "")
        if INSTALLATEUR_RE.match(nom):
            if installateur is None or vtuple(INSTALLATEUR_RE.match(nom).group(1)) > vtuple(
                    INSTALLATEUR_RE.match(installateur["name"]).group(1)):
                installateur = asset
        elif nom.lower().endswith(".exe.sha256") and INSTALLATEUR_RE.match(nom[:-7]):
            if sha_installateur is None or vtuple(INSTALLATEUR_RE.match(nom[:-7]).group(1)) > vtuple(
                    INSTALLATEUR_RE.match(sha_installateur["name"][:-7]).group(1)):
                sha_installateur = asset
        elif nom.lower().endswith(".zip.sha256"):
            sha_archive = sha_archive or asset
        elif nom.lower().endswith(".zip"):
            archive = archive or asset
    return {"installateur": installateur, "sha256_installateur": sha_installateur,
            "archive": archive, "sha256": sha_archive}


def choisir_assets_portable(assets: list[dict], version: str) -> dict:
    """Archive portable ``NEXUS-Portable-<version>.zip`` et son .sha256 (pré-release ``portable-<version>``)."""
    archive = somme = None
    for asset in assets:
        nom = str(asset.get("name") or "")
        if nom.lower() == f"nexus-portable-{version}.zip".lower():
            archive = asset
        elif nom.lower() == f"nexus-portable-{version}.zip.sha256".lower():
            somme = asset
    return {"portable": archive, "sha256_portable": somme}


def dossier_inscriptible(dossier: Path) -> bool:
    """Le portable ne peut se remplacer que dans un dossier où il peut écrire (pas une clé verrouillée)."""
    essai = Path(dossier) / f".nexus-ecriture-{os.getpid()}.tmp"
    try:
        essai.write_bytes(b"ok")
        essai.unlink()
        return True
    except OSError:
        return False


def extraire_portable(archive: Path, dest: Path, version: str) -> Path:
    """Extrait l'archive portable en la contrôlant ; renvoie le dossier qui contient NEXUS.exe.

    Refusé : chemins absolus ou avec « .. », plusieurs dossiers racine, fichier de données à la
    racine (config.json, data…, qui écraseraient celles de l'utilisateur), NEXUS.exe ou _internal
    absents, version annoncée différente de celle de l'archive."""
    import zipfile
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    try:
        z = zipfile.ZipFile(archive)
    except (OSError, zipfile.BadZipFile) as exc:
        raise NatifError("archive portable illisible") from exc
    with z:
        noms = z.namelist()
        if not noms or len(noms) > MAX_FICHIERS_PORTABLE:
            raise NatifError("archive portable vide ou anormale")
        racines = set()
        for nom in noms:
            n = nom.replace("\\", "/")
            morceaux = [m for m in n.split("/") if m]
            if n.startswith("/") or ":" in n or any(m == ".." for m in morceaux) or not morceaux:
                raise NatifError(f"chemin dangereux dans l'archive portable : {nom!r}")
            racines.add(morceaux[0])
            if len(morceaux) >= 2 and morceaux[1].lower() in {p.lower() for p in PROTEGES_RACINE}:
                raise NatifError(f"l'archive portable contient des données ({morceaux[1]}) : refusée")
        if len(racines) != 1:
            raise NatifError("l'archive portable doit contenir un seul dossier")
        z.extractall(dest)
    racine = dest / racines.pop()
    if not (racine / "NEXUS.exe").is_file() or not (racine / "_internal").is_dir():
        raise NatifError("l'archive portable ne contient pas NEXUS.exe et _internal")
    lue = ""
    try:
        lue = (racine / "_internal" / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    if vtuple(lue) != vtuple(version):
        raise NatifError("l'archive portable ne contient pas la version annoncée : installation refusée")
    return racine


def politique_signature() -> tuple[str, str]:
    """(politique, empreinte attendue). NEXUS_MAJ_SIGNATURE / NEXUS_MAJ_CERTIFICAT pour les tests."""
    reg = dict(config.get("mises_a_jour"))
    politique = str(os.environ.get("NEXUS_MAJ_SIGNATURE") or reg.get("signature") or "auto").strip().lower()
    if politique not in ("auto", "requise", "ignoree"):
        politique = "auto"
    certificat = str(os.environ.get("NEXUS_MAJ_CERTIFICAT") or reg.get("certificat") or "").strip()
    return politique, certificat


def _normaliser_empreinte(valeur: str) -> str:
    return re.sub(r"[^0-9A-F]", "", str(valeur or "").upper())


# --------------------------------------------------------------------------- #
#  Signature Authenticode (Windows)
# --------------------------------------------------------------------------- #
def _powershell() -> str | None:
    if os.name != "nt":
        return None
    trouve = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")
    if trouve:
        return trouve
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    for candidat in (windows / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
                     windows / "System32" / "WindowsPowerShell" / "v1.0" / "pwsh.exe"):
        if candidat.is_file():
            return str(candidat)
    return None


def _ps_litteral(valeur: str) -> str:
    return "'" + str(valeur).replace("'", "''") + "'"


def verifier_signature(path: Path, timeout: float = 45.0) -> dict:
    """Lit la signature Authenticode avec Get-AuthenticodeSignature.

    Renvoie un statut normalisé : ``valide``, ``non_signe``, ``invalide`` ou
    ``inconnu``, avec le signataire et son empreinte SHA1 quand ils existent.
    """
    path = Path(path)
    if not path.is_file():
        return {"statut": "inconnu", "signataire": "", "empreinte": "", "message": "fichier introuvable"}
    exe = _powershell()
    if not exe:
        return {"statut": "inconnu", "signataire": "", "empreinte": "", "message": "PowerShell introuvable"}
    script = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
        f"$s=Get-AuthenticodeSignature -LiteralPath {_ps_litteral(str(path))};"
        "if($s.SignerCertificate){$sujet=$s.SignerCertificate.Subject;$emp=$s.SignerCertificate.Thumbprint}"
        "else{$sujet='';$emp=''};"
        "[pscustomobject]@{Status=$s.Status.ToString();Message=$s.StatusMessage;"
        "Subject=$sujet;Thumbprint=$emp}|ConvertTo-Json -Compress"
    )
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        p = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                           creationflags=flags)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"statut": "inconnu", "signataire": "", "empreinte": "",
                "message": f"vérification impossible ({type(exc).__name__})"}
    sortie = (p.stdout or "").strip()
    ligne = next((l for l in reversed(sortie.splitlines()) if l.strip().startswith("{")), "")
    if p.returncode != 0 or not ligne:
        detail = ((p.stderr or "").strip() or sortie or "réponse vide")[:300]
        return {"statut": "inconnu", "signataire": "", "empreinte": "", "message": detail}
    try:
        data = json.loads(ligne)
    except ValueError:
        return {"statut": "inconnu", "signataire": "", "empreinte": "", "message": "réponse illisible"}
    statut = str(data.get("Status") or "").strip()
    if statut == "Valid":
        normalise = "valide"
    elif statut in ("NotSigned", "NotSupported"):
        normalise = "non_signe"
    else:
        normalise = "invalide"
    return {"statut": normalise, "signataire": str(data.get("Subject") or ""),
            "empreinte": _normaliser_empreinte(str(data.get("Thumbprint") or "")),
            "message": str(data.get("Message") or statut)}


def evaluer_signature(info: dict, politique: str = "auto", certificat: str = "") -> dict:
    """Applique la politique de signature. ``ok=False`` bloque l'installation."""
    attendu = _normaliser_empreinte(certificat)
    statut = str(info.get("statut") or "inconnu")
    if politique == "ignoree":
        return {"ok": True, "niveau": "attention", "message": "signature Authenticode ignorée (configuration)"}
    if statut == "valide":
        if attendu and _normaliser_empreinte(info.get("empreinte")) != attendu:
            return {"ok": False, "niveau": "erreur",
                    "message": "signature valide, mais signataire inattendu : installation refusée"}
        signataire = str(info.get("signataire") or "").strip()
        return {"ok": True, "niveau": "ok",
                "message": "signature Authenticode valide" + (f" ({signataire[:160]})" if signataire else "")}
    if statut == "non_signe":
        if politique == "requise":
            return {"ok": False, "niveau": "erreur",
                    "message": "l'installeur n'est pas signé : installation refusée (signature requise)"}
        return {"ok": True, "niveau": "attention",
                "message": "Installeur non signé : vérification SHA-256 seulement."}
    return {"ok": False, "niveau": "erreur",
            "message": f"signature Authenticode invalide ou illisible : {info.get('message') or statut}"}


# --------------------------------------------------------------------------- #
#  Sauvegarde de l'installation actuelle
# --------------------------------------------------------------------------- #
def _ignorer_racine(source: Path):
    def ignorer(dossier: str, noms: list[str]) -> list[str]:
        ici = Path(dossier)
        if ici == source:
            return [n for n in noms if n in PROTEGES_RACINE]
        return [n for n in noms if n in ("__pycache__", ".ruff_cache", ".pytest_cache")
                or n.endswith((".pyc", ".log", ".tmp", ".lnk"))]
    return ignorer


def sauvegarder_installation() -> Path:
    """Copie l'exe et ses fichiers dans ``maj/rollback/vX.Y.Z``."""
    if not paths.FROZEN:
        raise NatifError("la sauvegarde d'installation n'existe qu'en version gelée")
    source = Path(paths.INSTALL_DIR)
    if not source.is_dir() or not (source / "NEXUS.exe").is_file():
        raise NatifError("dossier d'installation introuvable")
    version = version_mod.current()
    ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)
    cible = ROLLBACK_DIR / f"v{version}"
    temporaire = ROLLBACK_DIR / f".copie-{version}-{int(time.time())}"
    try:
        if est_portable():                            # portable : seulement les fichiers du programme
            temporaire.mkdir(parents=True)
            for nom in PROGRAMME_PORTABLE:
                el = source / nom
                if el.is_dir():
                    shutil.copytree(el, temporaire / nom)   # tout _internal, profils fournis compris
                elif el.is_file():
                    shutil.copy2(el, temporaire / nom)
        else:
            shutil.copytree(source, temporaire, ignore=_ignorer_racine(source))
    except OSError as exc:
        shutil.rmtree(temporaire, ignore_errors=True)
        raise NatifError(f"sauvegarde de l'installation impossible ({exc})") from exc
    for vieux in list(ROLLBACK_DIR.iterdir()):
        if vieux == temporaire:
            continue
        if vieux.is_dir():
            shutil.rmtree(vieux, ignore_errors=True)
        else:
            vieux.unlink(missing_ok=True)
    try:
        temporaire.replace(cible)
    except OSError as exc:
        shutil.rmtree(temporaire, ignore_errors=True)
        raise NatifError(f"sauvegarde de l'installation impossible ({exc})") from exc
    _ecrire(ROLLBACK_DIR / f"v{version}.json",
            {"version": version, "date": time.time(), "dossier": str(cible)})
    return cible


def sauvegardes_installation() -> list[dict]:
    out = []
    if not ROLLBACK_DIR.is_dir():
        return out
    for meta in sorted(ROLLBACK_DIR.glob("v*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = _lire(meta, {}) or {}
        dossier = Path(str(data.get("dossier") or ""))
        if data.get("version") and dossier.is_dir():
            out.append({"dossier": dossier.name, "version": str(data["version"]), "date": data.get("date"),
                        "natif": True, "chemin": str(dossier)})
    return out


# --------------------------------------------------------------------------- #
#  Travail pour le helper PowerShell
# --------------------------------------------------------------------------- #
def _job(action: str, backup: Path, expected: str, timeout: int) -> dict:
    return {
        "action": action,
        "parent_pid": os.getpid(),
        "app_dir": str(Path(paths.INSTALL_DIR)),
        "app_exe": str(Path(sys.executable).resolve()),
        "backup_dir": str(backup),
        "data_dir": str(Path(paths.USER_ROOT)),
        "from_version": version_mod.current(),
        "expected_version": expected,
        "marker": str(MARKER_FILE),
        "result": str(RESULT_FILE),
        "log": str(LOG_FILE),
        "started": time.time(),
        "timeout": int(timeout),
        "restart_args": [],
        # jamais supprimés ni remplacés à la racine du dossier du programme (données du portable)
        "proteger": sorted(PROTEGES_RACINE),
        # portable : seuls éléments du dossier que le helper peut supprimer ou remplacer ; vide = tout le dossier
        # du programme (version installée, où les données sont ailleurs)
        "elements": list(PROGRAMME_PORTABLE) if est_portable() else [],
    }


def construire_job_installation(dispo: dict, installeur: Path, backup: Path) -> dict:
    job = _job("install", backup, str(dispo["version"]), 300)
    job.update({
        "installer": str(Path(installeur)),
        "installer_log": str(NATIF_DIR / f"installateur-{dispo['version']}.log"),
    })
    return job


def construire_job_portable(dispo: dict, nouveau: Path, backup: Path) -> dict:
    """Portable : le helper remplace les fichiers du programme par ceux de ``nouveau``."""
    job = _job("portable", backup, str(dispo["version"]), 180)
    nouveaux = [e.name for e in Path(nouveau).iterdir() if e.name.lower() not in {p.lower() for p in PROTEGES_RACINE}]
    job.update({"source_dir": str(Path(nouveau)), "installer": "", "installer_log": "",
                "elements": sorted(set(PROGRAMME_PORTABLE) | set(nouveaux))})
    return job


def construire_job_retour(backup: Path, version: str) -> dict:
    job = _job("restore", backup, str(version), 180)
    job.update({"installer": "", "installer_log": ""})
    return job


def lancer_helper(job: dict) -> dict:
    """Écrit le travail et démarre le script PowerShell détaché."""
    if os.name != "nt":
        raise NatifError("la mise à jour par installeur nécessite Windows")
    exe = _powershell()
    if not exe:
        raise NatifError("PowerShell est introuvable : impossible de lancer l'installeur")
    script = Path(os.environ.get("NEXUS_MAJ_HELPER") or (paths.APP_DIR / "outils" / HELPER_NAME))
    if not script.is_file():
        raise NatifError(f"script de mise à jour introuvable : {script}")
    # Copie hors du dossier d'installation : l'installeur supprime _internal, et
    # PowerShell ne doit pas dépendre d'un fichier en cours de remplacement.
    paths.MAJ_DIR.mkdir(parents=True, exist_ok=True)
    for vieux in paths.MAJ_DIR.glob("appliquer_maj-*.ps1"):
        try:
            vieux.unlink()
        except OSError:
            pass
    copie = paths.MAJ_DIR / f"appliquer_maj-{int(time.time())}.ps1"
    try:
        shutil.copy2(script, copie)
    except OSError as exc:
        raise NatifError(f"copie du script de mise à jour impossible ({exc})") from exc
    _ecrire(JOB_FILE, job)
    cmd = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
           "-WindowStyle", "Hidden", "-File", str(copie), "-Job", str(JOB_FILE)]
    if os.environ.get("NEXUS_MAJ_HELPER_DRY") == "1":       # tests : ne lance rien
        return {"commande": cmd, "travail": job}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(cmd, cwd=str(paths.MAJ_DIR), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)
    except OSError as exc:
        try:
            JOB_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        raise NatifError(f"lancement du helper impossible ({exc})") from exc
    return {"commande": cmd, "travail": job}


# --------------------------------------------------------------------------- #
#  Marqueur de démarrage réussi (écrit par la nouvelle version)
# --------------------------------------------------------------------------- #
def job_en_cours() -> dict | None:
    return _lire(JOB_FILE, None)


def marquer_demarrage_ok() -> bool:
    """Appelé quand le serveur est prêt : le helper considère l'installation réussie."""
    job = job_en_cours()
    if not isinstance(job, dict) or job.get("action") not in ("install", "restore", "portable"):
        return False
    if str(job.get("expected_version") or "") != version_mod.current():
        return False
    _ecrire(MARKER_FILE, {"version": version_mod.current(), "date": time.time(), "pid": os.getpid()})
    return True


def resultat_erreur(type_: str, from_version: str, vers: str, message: str) -> None:
    _ecrire(RESULT_FILE, {"ok": False, "type": type_, "de": from_version, "vers": vers,
                          "date": time.time(), "message": message, "journalise": False})
