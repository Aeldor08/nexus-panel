"""Mises à jour de NEXUS depuis les releases GitHub d'un dépôt configuré (config.json → mises_a_jour.depot).

- Vérification : au démarrage puis toutes les N heures (réglable, désactivable), en tâche de fond légère.
  Seule l'API des releases du dépôt configuré est interrogée (https://api.github.com/repos/<depot>/releases/latest).
- Dépôt privé : jeton en LECTURE SEULE (fine-grained, ce dépôt uniquement), rangé dans le gestionnaire
  d'identifiants de Windows (keyring), ou à défaut dans config.json (hors Git). Il n'est jamais renvoyé par l'API
  du panel, jamais écrit dans les journaux, et n'est envoyé qu'à api.github.com (pas même à l'hébergeur des
  fichiers vers lequel GitHub redirige le téléchargement).
- Installation (clic + mot de passe du panel, jamais déclenchée par le bot Discord) : téléchargement de l'archive
  de la release, vérification du SHA256 AVANT toute extraction, sauvegarde horodatée (code, data/, config),
  préparation des fichiers, puis redémarrage : maj_demarrage.py les met en place, teste le démarrage et
  restaure tout seul la sauvegarde en cas d'échec.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import shutil
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import config
import identifiants
import maj_natif
import paths
import version as version_mod

BASE = paths.APP_DIR
MAJ_DIR = paths.MAJ_DIR  # téléchargements et fichiers préparés (hors Git, hors release)
SAUV_DIR = paths.SAUVEGARDES_DIR  # sauvegardes horodatées avant chaque mise à jour (hors Git)
ETAT_FILE = MAJ_DIR / "etat.json"  # dernière vérification, « plus tard », notification Discord
EN_COURS = MAJ_DIR / "en_cours.json"  # travail pour maj_demarrage.py (au prochain démarrage)
API = "https://api.github.com"
# Tests uniquement : faux GitHub local (jamais utilisé en temps normal)
API_TEST = os.environ.get("NEXUS_MAJ_API_TEST", "").rstrip("/")
DEPOT_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")
JETON_RE = re.compile(r"^(github_pat_[A-Za-z0-9_]{20,255}|gh[pousr]_[A-Za-z0-9]{20,255})$")
KEYRING_SERVICE = identifiants.SERVICE_MAJ
# Hôtes où GitHub redirige le téléchargement des fichiers de release (aucun jeton ne leur est envoyé)
HOTES_FICHIERS = {"objects.githubusercontent.com", "github-releases.githubusercontent.com", "release-assets.githubusercontent.com", "codeload.github.com"}
MAX_ARCHIVE = 300 * 1024 * 1024
# Jamais remplacés par une mise à jour (données, configuration, environnement, sauvegardes)
PROTEGES = {
    "data",
    "config.json",
    "deck.json",
    "jeux.json",
    "fan_names.json",
    "runtime.json",
    ".env",
    ".venv",
    ".venv-build",
    "venv",
    "runtime",
    "runtime.neuf",
    "runtime.tmp",
    "logs",
    "versions",
    "partage",
    "maj",
    "sauvegardes-maj",
    "LibreHardwareMonitor",
    "actions",
    ".git",
    "dist",
    ".ruff_cache",
    ".pytest_cache",
    "sauvegardes",
    "backups",
    "reference",
    "references",
}
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


class MajError(Exception):
    pass


# --------------------------------------------------------------------------- #
#  Outils
# --------------------------------------------------------------------------- #
def vtuple(v: str) -> tuple[int, int, int]:
    m = SEMVER.match(str(v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def plus_recente(a: str, b: str) -> bool:
    """a est-elle strictement plus récente que b ?"""
    return vtuple(a) > vtuple(b)


def reglages() -> dict:
    r = dict(config.get("mises_a_jour"))
    r["depot"] = str(r.get("depot") or "").strip()
    if r["depot"] and not DEPOT_RE.match(r["depot"]):
        r["depot"] = ""  # jamais d'adresse fabriquée avec un nom invalide
    try:
        r["intervalle_heures"] = max(1.0, min(168.0, float(r.get("intervalle_heures") or 6)))
    except (TypeError, ValueError):
        r["intervalle_heures"] = 6.0
    r["actif"] = bool(r.get("actif", True))
    r["discord"] = bool(r.get("discord", False))
    sig = str(r.get("signature") or "auto").strip().lower()
    r["signature"] = sig if sig in ("auto", "requise", "ignoree") else "auto"
    r["certificat"] = str(r.get("certificat") or "").strip()
    return r


def _lire(path: Path, defaut):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))  # le helper PowerShell écrit sans BOM
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


# --------------------------------------------------------------------------- #
#  Jeton (lecture seule) : gestionnaire d'identifiants de Windows, sinon config.json
# --------------------------------------------------------------------------- #
def jeton(depot: str) -> tuple[str, str]:
    """(jeton, où il est rangé : 'windows' | 'config' | 'environnement' | '')."""
    t = os.environ.get("NEXUS_MAJ_JETON", "").strip()  # tests / CI : lu en mémoire, jamais enregistré
    if t:
        return t, "environnement"
    t = identifiants.lire(KEYRING_SERVICE, depot)
    if t:
        return t, "windows"
    t = str(config.get("mises_a_jour").get("jeton") or "").strip()
    return (t, "config") if t else ("", "")


def enregistrer_jeton(depot: str, valeur: str) -> str:
    valeur = (valeur or "").strip()
    if not DEPOT_RE.match(depot or ""):
        raise MajError("indique d'abord le dépôt à surveiller (propriétaire/nom)")
    if valeur and not JETON_RE.match(valeur):
        raise MajError("ce n'est pas un jeton GitHub (il commence par github_pat_ ou ghp_)")
    if not valeur:
        identifiants.supprimer(KEYRING_SERVICE, depot)
        _config_set({"jeton": ""})
        return ""
    if identifiants.ecrire(KEYRING_SERVICE, depot, valeur):
        _config_set({"jeton": ""})  # jamais en double dans config.json
        return "windows"
    _config_set({"jeton": valeur})  # repli : config.json, exclu de Git
    return "config" if valeur else ""


def _config_set(changes: dict) -> None:
    """Modifie la section mises_a_jour de config.json (le reste du fichier n'est pas touché)."""
    path = config.CONFIG_FILE
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise MajError("config.json illisible : corrige-le ou relance configurer.bat")
    sec = dict(data.get("mises_a_jour") or {})
    sec.update(changes)
    if not sec.get("jeton"):
        sec.pop("jeton", None)
    data["mises_a_jour"] = sec
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    config.load(force=True)


def modifier_reglages(changes: dict) -> dict:
    ok = {}
    if "depot" in changes:
        d = str(changes["depot"] or "").strip().removeprefix("https://github.com/").strip("/")
        if d and not DEPOT_RE.match(d):
            raise MajError("dépôt invalide : écris-le sous la forme propriétaire/nom (ex. mon-pseudo/nexus-panel)")
        ok["depot"] = d
    if "actif" in changes:
        ok["actif"] = bool(changes["actif"])
    if "discord" in changes:
        ok["discord"] = bool(changes["discord"])
    if "intervalle_heures" in changes:
        try:
            ok["intervalle_heures"] = max(1, min(168, int(float(changes["intervalle_heures"]))))
        except (TypeError, ValueError):
            raise MajError("intervalle invalide")
    if ok:
        _config_set(ok)
    return reglages()


# --------------------------------------------------------------------------- #
#  Accès à GitHub (API des releases du dépôt configuré, uniquement)
# --------------------------------------------------------------------------- #
class _SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # on suit les redirections à la main (sans le jeton)
        return None


_OPENER = urllib.request.build_opener(_SansRedirection, urllib.request.HTTPSHandler(context=ssl.create_default_context()))


def _base_api() -> str:
    return API_TEST or API


def _requete(url: str, tok: str = "", accept: str = "application/vnd.github+json", timeout: float = 15):
    """GET vers l'API GitHub. Renvoie la réponse (http.client) ; lève MajError avec un message clair."""
    u = urllib.parse.urlparse(url)
    base = urllib.parse.urlparse(_base_api())
    if (u.scheme, u.netloc) != (base.scheme, base.netloc):
        raise MajError("adresse refusée (seule l'API GitHub du dépôt configuré est autorisée)")
    headers = {"Accept": accept, "User-Agent": f"NEXUS-panel/{version_mod.current()}", "X-GitHub-Api-Version": "2022-11-28"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    try:
        return _OPENER.open(urllib.request.Request(url, headers=headers), timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e  # redirection : traitée par l'appelant
        raise _erreur_http(e) from None
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        raise MajError("GitHub injoignable (pas de connexion Internet ?) — réessaie plus tard") from e


def _erreur_http(e: urllib.error.HTTPError) -> MajError:
    reste = e.headers.get("X-RateLimit-Remaining") if e.headers else None
    if e.code == 401:
        return MajError("jeton GitHub invalide ou expiré : crée-en un nouveau (Réglages → Mises à jour)")
    if e.code in (403, 429) and reste == "0":
        reset = e.headers.get("X-RateLimit-Reset")
        quand = time.strftime("%H:%M", time.localtime(int(reset))) if reset and reset.isdigit() else "plus tard"
        return MajError(f"limite de requêtes GitHub atteinte : nouvel essai possible vers {quand}")
    if e.code == 403:
        return MajError("accès refusé par GitHub : le jeton n'a pas le droit de lire ce dépôt")
    if e.code == 404:
        return MajError("dépôt ou release introuvable (dépôt privé ? il faut alors un jeton en lecture seule)")
    return MajError(f"GitHub a répondu une erreur {e.code}")


def _json(url: str, tok: str):
    r = _requete(url, tok)
    try:
        return json.loads(r.read().decode("utf-8"))
    except ValueError:
        raise MajError("réponse de GitHub illisible")


def _asset_public(asset: dict | None) -> dict | None:
    if not asset:
        return None
    return {"id": asset["id"], "nom": asset["name"], "taille": asset.get("size")}


def derniere_release(depot: str, tok: str) -> dict:
    data = _json(f"{_base_api()}/repos/{depot}/releases/latest", tok)
    tag = str(data.get("tag_name") or "")
    ver = tag.removeprefix("v")
    if not SEMVER.match(ver):
        raise MajError(f"la dernière release a un numéro illisible ({tag!r})")
    assets = maj_natif.choisir_assets(list(data.get("assets") or []))
    return {
        "version": ver,
        "tag": tag,
        "nom": data.get("name") or tag,
        "notes": str(data.get("body") or "")[:20000],
        "date": data.get("published_at"),
        "page": data.get("html_url"),
        "archive": _asset_public(assets["archive"]),
        "sha256": _asset_public(assets["sha256"]),
        "installateur": _asset_public(assets["installateur"]),
        "sha256_installateur": _asset_public(assets["sha256_installateur"]),
    }


def release_portable(depot: str, tok: str, ver: str) -> dict:
    """Archive de la version portable : pré-release « portable-X.Y.Z » à part (jamais vue par /releases/latest).
    Pas encore publiée (404) → archive absente : le portable attend, ou se met à jour à la main."""
    try:
        data = _json(f"{_base_api()}/repos/{depot}/releases/tags/portable-{ver}", tok)
    except MajError:
        return {"portable": None, "sha256_portable": None}
    assets = maj_natif.choisir_assets_portable(list(data.get("assets") or []), ver)
    return {"portable": _asset_public(assets["portable"]), "sha256_portable": _asset_public(assets["sha256_portable"])}


def _telecharger_asset(depot: str, asset_id: int, tok: str, dest: Path, limite: int = MAX_ARCHIVE, progres=None) -> None:
    """Fichier d'une release du dépôt configuré : demande à l'API (avec le jeton), puis suit la redirection
    vers l'hébergeur des fichiers de GitHub SANS le jeton."""
    r = _requete(f"{_base_api()}/repos/{depot}/releases/assets/{int(asset_id)}", tok, accept="application/octet-stream", timeout=60)
    if isinstance(r, urllib.error.HTTPError):  # redirection
        loc = r.headers.get("Location") or ""
        u = urllib.parse.urlparse(loc)
        if API_TEST and loc.startswith(API_TEST):
            pass  # faux GitHub des tests
        elif u.scheme != "https" or u.hostname not in HOTES_FICHIERS:
            raise MajError("redirection de téléchargement refusée (hôte inattendu)")
        try:
            r = _OPENER.open(urllib.request.Request(loc, headers={"User-Agent": f"NEXUS-panel/{version_mod.current()}"}), timeout=60)
        except (urllib.error.URLError, OSError) as e:
            raise MajError("téléchargement interrompu (connexion ?)") from e
    total = int(r.headers.get("Content-Length") or 0)
    if total > limite:
        raise MajError("archive trop grande")
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(dest, "wb") as f:
        while True:
            bloc = r.read(1 << 16)
            if not bloc:
                break
            n += len(bloc)
            if n > limite:
                raise MajError("archive trop grande")
            f.write(bloc)
            if progres and total:
                progres(n / total)


# --------------------------------------------------------------------------- #
#  Le service (une instance dans app.py)
# --------------------------------------------------------------------------- #
class Updater:
    def __init__(self, notifier=None) -> None:
        self.notifier = notifier  # bot Discord : simple message, jamais d'installation
        self._lock = threading.Lock()
        self.etat = _lire(ETAT_FILE, {})
        self.travail = {"etape": None, "progres": 0, "erreur": None, "vers": None}
        self._stop = threading.Event()

    # -- état pour la page -----------------------------------------------------
    def retours(self) -> list[dict]:
        """Versions vers lesquelles un retour est encore possible (jamais la version courante)."""
        if paths.FROZEN:
            return [s for s in maj_natif.sauvegardes_installation() if s["version"] != version_mod.current()]
        return self.sauvegardes()

    def public(self) -> dict:
        r = reglages()
        _, ou = jeton(r["depot"])
        dispo = self.etat.get("disponible")
        report = self.etat.get("plus_tard") or {}
        cache = bool(dispo and report.get("version") == dispo.get("version") and time.time() < float(report.get("jusqu_a") or 0))
        dispo = dispo if dispo and plus_recente(dispo.get("version"), version_mod.current()) else None
        if dispo:
            dispo = dict(dispo)
            if paths.FROZEN and maj_natif.est_portable():
                # « portable » : remplacement automatique ; « manuel » : archive portable pas (encore) publiée
                # ou dossier en lecture seule (clé verrouillée, Program Files…)
                auto = bool(dispo.get("portable") and dispo.get("sha256_portable") and maj_natif.dossier_inscriptible(paths.INSTALL_DIR))
                dispo["mode"] = "portable" if auto else "manuel"
                dispo["taille"] = (dispo.get("portable") or {}).get("taille")
            elif paths.FROZEN:
                dispo["mode"] = "installateur"
                dispo["taille"] = (dispo.get("installateur") or {}).get("taille")
            else:
                dispo["mode"] = "archive"
                dispo["taille"] = (dispo.get("archive") or {}).get("taille")
        sauv = self.retours()
        return {
            "version": version_mod.current(),
            "date": version_mod.date_version(),
            "natif": paths.FROZEN,
            "portable": maj_natif.est_portable(),
            "reglages": {k: r[k] for k in ("depot", "actif", "intervalle_heures", "discord", "signature")},
            "jeton": {"enregistre": bool(ou), "ou": ou},
            "verification": {k: self.etat.get(k) for k in ("derniere", "resultat", "erreur", "a_jour")},
            "disponible": dispo,
            "rappel_repousse": cache,
            "travail": dict(self.travail),
            "dernier_resultat": _lire(MAJ_DIR / "resultat.json", None),
            "retour_possible": bool(sauv),
            "sauvegardes": sauv[:5],
            "redemarrage_auto": os.environ.get("NEXUS_LANCEUR") == "1",
        }

    def sauvegardes(self) -> list[dict]:
        out = []
        for d in sorted(SAUV_DIR.glob("*/manifeste.json"), reverse=True):
            m = _lire(d, {})
            if m.get("version"):
                out.append({"dossier": d.parent.name, "version": m["version"], "date": m.get("date")})
        return out

    # -- vérification -----------------------------------------------------------
    def verifier(self) -> dict:
        r = reglages()
        with self._lock:
            if not r["depot"]:
                self.etat.update(resultat="non_configure", erreur="aucun dépôt configuré (Réglages → Mises à jour)", a_jour=None)
            else:
                tok, _ = jeton(r["depot"])
                try:
                    rel = derniere_release(r["depot"], tok)
                    nouvelle = plus_recente(rel["version"], version_mod.current())
                    if nouvelle and maj_natif.est_portable():
                        rel.update(release_portable(r["depot"], tok, rel["version"]))
                    self.etat.update(resultat="ok", erreur=None, a_jour=not nouvelle, disponible=rel if nouvelle else None)
                    if nouvelle and r["discord"] and self.notifier and self.etat.get("discord_notifie") != rel["version"]:
                        self.etat["discord_notifie"] = rel["version"]
                        try:
                            self.notifier(
                                f"🆕 NEXUS : la version {rel['version']} est disponible (installée : "
                                f"{version_mod.current()}). Installe-la depuis le panel, sur le PC."
                            )
                        except Exception:
                            pass
                except MajError as e:
                    self.etat.update(resultat="erreur", erreur=str(e))
            self.etat["derniere"] = time.time()  # une fois la réponse reçue (jamais « vérifié » à moitié)
            _ecrire(ETAT_FILE, self.etat)
        return self.public()

    def plus_tard(self, heures: float = 24) -> dict:
        dispo = self.etat.get("disponible") or {}
        with self._lock:
            self.etat["plus_tard"] = {"version": dispo.get("version"), "jusqu_a": time.time() + heures * 3600}
            _ecrire(ETAT_FILE, self.etat)
        return self.public()

    def demarrer(self, delai: float = 20) -> None:
        self._stop.clear()
        threading.Thread(target=self._boucle, args=(delai,), daemon=True, name="maj").start()

    def arreter(self) -> None:
        self._stop.set()

    def _boucle(self, delai: float) -> None:
        if self._stop.wait(delai):
            return
        while not self._stop.is_set():
            r = reglages()
            prochaine = float(self.etat.get("derniere") or 0) + r["intervalle_heures"] * 3600
            if r["actif"] and r["depot"] and time.time() >= prochaine - 60:
                try:
                    self.verifier()
                except Exception as e:  # jamais d'arrêt du panel à cause d'une vérification
                    self.etat.update(resultat="erreur", erreur=f"{type(e).__name__}")
            self._stop.wait(300)  # regarde toutes les 5 min si l'heure est venue

    # -- installation -------------------------------------------------------------
    def installer(self, on_restart) -> None:
        """Lancé dans un fil : prépare tout puis demande le redémarrage. Erreur → self.travail['erreur']."""
        if self.travail["etape"] not in (None, "erreur"):
            raise MajError("une mise à jour est déjà en cours")
        dispo = self.public().get("disponible")
        if not dispo:
            raise MajError("aucune version plus récente à installer (vérifie d'abord)")
        if paths.FROZEN:
            if maj_natif.est_portable():
                if not maj_natif.dossier_inscriptible(paths.INSTALL_DIR):
                    raise MajError(
                        "le dossier du portable est en lecture seule : NEXUS ne peut pas s'y mettre à jour "
                        "(copie-le dans un dossier modifiable, ou remplace NEXUS.exe et _internal à la main)"
                    )
                if not dispo.get("portable") or not dispo.get("sha256_portable"):
                    r = reglages()  # publiée depuis la dernière vérification ?
                    dispo.update(release_portable(r["depot"], jeton(r["depot"])[0], dispo["version"]))
                    if self.etat.get("disponible"):
                        self.etat["disponible"].update({k: dispo[k] for k in ("portable", "sha256_portable")})
                if not dispo.get("portable") or not dispo.get("sha256_portable"):
                    raise MajError(
                        f"la version portable {dispo['version']} n'est pas encore publiée "
                        f"(NEXUS-Portable-{dispo['version']}.zip et son .sha256) : réessaie un peu plus tard"
                    )
                self.travail = {"etape": "telechargement", "progres": 0, "erreur": None, "vers": dispo["version"]}
                threading.Thread(target=self._installer_portable, args=(dispo, on_restart), daemon=True, name="maj-installation").start()
                return
            if not dispo.get("installateur") or not dispo.get("sha256_installateur"):
                raise MajError("cette release n'a pas d'installeur NEXUS-x.y.z-Setup.exe et de fichier .sha256 : installation refusée")
            self.travail = {"etape": "telechargement", "progres": 0, "erreur": None, "vers": dispo["version"]}
            threading.Thread(target=self._installer_natif, args=(dispo, on_restart), daemon=True, name="maj-installation").start()
            return
        if not dispo.get("archive") or not dispo.get("sha256"):
            raise MajError("cette release n'a pas d'archive .zip et de fichier .sha256 : installation refusée")
        self.travail = {"etape": "telechargement", "progres": 0, "erreur": None, "vers": dispo["version"]}
        threading.Thread(target=self._installer, args=(dispo, on_restart), daemon=True, name="maj-installation").start()

    def _installer(self, dispo: dict, on_restart) -> None:
        try:
            prep = self.preparer(dispo, progres=lambda p: self.travail.update(progres=round(p * 100)))
            self.travail.update(etape="redemarrage", progres=100)
            _ecrire(EN_COURS, prep)
            time.sleep(0.8)  # la page reçoit l'étape « redémarrage »
            on_restart()
        except Exception as e:
            self.travail.update(etape="erreur", erreur=str(e) if isinstance(e, MajError) else f"{type(e).__name__}: {e}")

    def _installer_natif(self, dispo: dict, on_restart) -> None:
        """Télécharge l'installeur, vérifie SHA256 + signature, sauvegarde, puis laisse le helper agir."""
        dossier = maj_natif.NATIF_DIR / dispo["version"]
        try:
            r = reglages()
            tok, _ = jeton(r["depot"])
            if dossier.exists():
                shutil.rmtree(dossier, ignore_errors=True)
            dossier.mkdir(parents=True, exist_ok=True)
            nom_installeur = Path(str(dispo["installateur"]["nom"])).name
            nom_somme = Path(str(dispo["sha256_installateur"]["nom"])).name
            installeur = dossier / nom_installeur
            somme = dossier / nom_somme

            self.travail.update(etape="telechargement", progres=0)
            _telecharger_asset(r["depot"], dispo["sha256_installateur"]["id"], tok, somme, limite=4096)
            _telecharger_asset(r["depot"], dispo["installateur"]["id"], tok, installeur, progres=lambda p: self.travail.update(progres=round(p * 100)))

            self.travail.update(etape="verification", progres=100)
            attendu = somme.read_text(encoding="utf-8", errors="replace").strip().split()[0].lower() if somme.stat().st_size else ""
            if not maj_natif.SHA256_RE.match(attendu):
                raise MajError("fichier SHA256 de l'installeur illisible : installation refusée")
            if maj_natif.sha256_fichier(installeur) != attendu:
                raise MajError("SHA256 différent pour l'installeur : fichier corrompu ou modifié — installation refusée, rien n'a été touché")

            self.travail.update(etape="signature")
            signature = maj_natif.verifier_signature(installeur)
            evaluation = maj_natif.evaluer_signature(signature, r["signature"], r["certificat"])
            if not evaluation["ok"]:
                raise MajError(evaluation["message"])
            print(f"[MAJ] {evaluation['message']}", flush=True)

            self.travail.update(etape="sauvegarde")
            backup = maj_natif.sauvegarder_installation()
            job = maj_natif.construire_job_installation(dispo, installeur, backup)
            job["signature_note"] = "" if evaluation["niveau"] == "ok" else evaluation["message"]
            maj_natif.lancer_helper(job)
            self.travail.update(etape="redemarrage", progres=100)
            time.sleep(0.8)
            on_restart()
        except Exception as e:
            try:
                shutil.rmtree(dossier, ignore_errors=True)
            except OSError:
                pass
            message = str(e) if isinstance(e, (MajError, maj_natif.NatifError)) else f"{type(e).__name__}: {e}"
            self.travail.update(etape="erreur", erreur=message)
            try:
                maj_natif.resultat_erreur("installation", version_mod.current(), str(dispo.get("version") or ""), f"Mise à jour impossible : {message}")
            except OSError:
                pass

    def _installer_portable(self, dispo: dict, on_restart) -> None:
        """Portable : télécharge l'archive portable, vérifie SHA256 et contenu, sauvegarde le programme actuel,
        puis le helper remplace NEXUS.exe et _internal (jamais les données posées à côté) et relance NEXUS."""
        dossier = maj_natif.NATIF_DIR / dispo["version"]
        try:
            r = reglages()
            tok, _ = jeton(r["depot"])
            if dossier.exists():
                shutil.rmtree(dossier, ignore_errors=True)
            dossier.mkdir(parents=True, exist_ok=True)
            archive = dossier / Path(str(dispo["portable"]["nom"])).name
            somme = dossier / Path(str(dispo["sha256_portable"]["nom"])).name

            self.travail.update(etape="telechargement", progres=0)
            _telecharger_asset(r["depot"], dispo["sha256_portable"]["id"], tok, somme, limite=4096)
            _telecharger_asset(r["depot"], dispo["portable"]["id"], tok, archive, progres=lambda p: self.travail.update(progres=round(p * 100)))

            self.travail.update(etape="verification", progres=100)
            attendu = somme.read_text(encoding="utf-8", errors="replace").strip().split()[0].lower() if somme.stat().st_size else ""
            if not maj_natif.SHA256_RE.match(attendu):
                raise MajError("fichier SHA256 de l'archive portable illisible : installation refusée")
            if maj_natif.sha256_fichier(archive) != attendu:
                raise MajError("SHA256 différent pour l'archive portable : fichier corrompu ou modifié — installation refusée, rien n'a été touché")
            nouveau = maj_natif.extraire_portable(archive, dossier / "fichiers", dispo["version"])
            archive.unlink(missing_ok=True)  # place disque : seul le dossier extrait sert

            self.travail.update(etape="sauvegarde")
            backup = maj_natif.sauvegarder_installation()
            maj_natif.lancer_helper(maj_natif.construire_job_portable(dispo, nouveau, backup))
            self.travail.update(etape="redemarrage", progres=100)
            time.sleep(0.8)
            on_restart()
        except Exception as e:
            shutil.rmtree(dossier, ignore_errors=True)
            message = str(e) if isinstance(e, (MajError, maj_natif.NatifError)) else f"{type(e).__name__}: {e}"
            self.travail.update(etape="erreur", erreur=message)
            try:
                maj_natif.resultat_erreur("installation", version_mod.current(), str(dispo.get("version") or ""), f"Mise à jour impossible : {message}")
            except OSError:
                pass

    def preparer(self, dispo: dict, progres=None) -> dict:
        """Télécharge, vérifie le SHA256, sauvegarde, extrait. Renvoie le travail pour maj_demarrage.py."""
        r = reglages()
        tok, _ = jeton(r["depot"])
        ver = dispo["version"]
        dossier = MAJ_DIR / ver
        if dossier.exists():
            shutil.rmtree(dossier, ignore_errors=True)
        archive = dossier / dispo["archive"]["nom"]
        somme = dossier / dispo["sha256"]["nom"]
        _telecharger_asset(r["depot"], dispo["sha256"]["id"], tok, somme, limite=4096)
        _telecharger_asset(r["depot"], dispo["archive"]["id"], tok, archive, progres=progres)
        self.travail.update(etape="verification")
        attendu = somme.read_text(encoding="utf-8", errors="replace").strip().split()[0].lower() if somme.stat().st_size else ""
        if not re.fullmatch(r"[0-9a-f]{64}", attendu):
            raise MajError("fichier SHA256 illisible : installation refusée")
        obtenu = sha256_fichier(archive)
        if obtenu != attendu:
            shutil.rmtree(dossier, ignore_errors=True)
            raise MajError("SHA256 différent : archive corrompue ou modifiée — installation refusée, rien n'a été touché")
        fichiers = dossier / "fichiers"
        racine = extraire_sur(archive, fichiers)
        if vtuple((racine / "VERSION").read_text(encoding="utf-8").strip()) != vtuple(ver):
            raise MajError("l'archive ne contient pas la version annoncée : installation refusée")
        self.travail.update(etape="sauvegarde")
        sauv = sauvegarder(f"avant-v{ver}")
        nettoyer_sauvegardes()  # au plus 3 sauvegardes de mise à jour (chacune ~ code + data)
        return {
            "etat": "a_appliquer",
            "de": version_mod.current(),
            "vers": ver,
            "fichiers": str(racine),
            "sauvegarde": str(sauv),
            "date": time.time(),
            "essais": 0,
        }

    def revenir(self, on_restart) -> str:
        sauv = self.retours()
        if not sauv:
            raise MajError("aucune sauvegarde de version précédente")
        if paths.FROZEN:
            try:
                job = maj_natif.construire_job_retour(Path(sauv[0]["chemin"]), sauv[0]["version"])
                maj_natif.lancer_helper(job)
            except maj_natif.NatifError as exc:
                raise MajError(str(exc)) from exc
            self.travail = {"etape": "redemarrage", "progres": 100, "erreur": None, "vers": sauv[0]["version"]}
            threading.Timer(0.8, on_restart).start()
            return sauv[0]["version"]
        dossier = SAUV_DIR / sauv[0]["dossier"]
        _ecrire(
            EN_COURS,
            {
                "etat": "a_restaurer",
                "de": version_mod.current(),
                "vers": sauv[0]["version"],
                "sauvegarde": str(dossier),
                "date": time.time(),
                "code_seulement": True,
            },
        )
        self.travail = {"etape": "redemarrage", "progres": 100, "erreur": None, "vers": sauv[0]["version"]}
        threading.Timer(0.8, on_restart).start()
        return sauv[0]["version"]


# --------------------------------------------------------------------------- #
#  Archive, sauvegarde (aussi utilisés par maj_demarrage.py et les tests)
# --------------------------------------------------------------------------- #
def extraire_sur(archive: Path, dest: Path) -> Path:
    """Extrait l'archive en refusant tout chemin dangereux ; renvoie le dossier racine (avec VERSION et app.py)."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    try:
        z = zipfile.ZipFile(archive)
    except zipfile.BadZipFile:
        raise MajError("archive illisible") from None
    with z:
        total = 0
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or re.match(r"^[A-Za-z]:", name) or ".." in name.split("/"):
                raise MajError(f"chemin dangereux dans l'archive ({name}) : installation refusée")
            total += info.file_size
            if total > MAX_ARCHIVE * 3:
                raise MajError("archive trop volumineuse une fois extraite")
        z.extractall(dest)
    racine = dest
    enfants = list(dest.iterdir())
    if len(enfants) == 1 and enfants[0].is_dir():
        racine = enfants[0]  # archive avec un dossier NEXUS-x.y.z/ à la racine
    if not (racine / "VERSION").is_file() or not (racine / "app.py").is_file():
        raise MajError("ce n'est pas une archive de NEXUS (VERSION ou app.py manquant)")
    return racine


def fichiers_code(racine: Path = BASE) -> list[Path]:
    """Fichiers du code et des profils FOURNIS (jamais données, config, environnement, sauvegardes)."""
    out = []
    for p in racine.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(racine)
        if rel.parts[0] in PROTEGES or "__pycache__" in rel.parts or p.suffix in (".pyc", ".lnk", ".log", ".tmp"):
            continue
        out.append(rel)
    return out


SAUVEGARDES_A_GARDER = 3


def nettoyer_sauvegardes(garder: int = SAUVEGARDES_A_GARDER) -> list[str]:
    """Garde les « garder » sauvegardes de mise à jour les plus récentes (dossiers horodatés du dossier sauvegardes-maj)."""
    dossiers = sorted((d for d in SAUV_DIR.glob("*") if (d / "manifeste.json").is_file()), key=lambda d: d.name, reverse=True)
    retires = []
    for d in dossiers[max(1, garder) :]:
        shutil.rmtree(d, ignore_errors=True)
        retires.append(d.name)
    return retires


def sauvegarder(etiquette: str) -> Path:
    """Sauvegarde horodatée : code actuel + data/ + configuration personnelle."""
    dossier = SAUV_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-v{version_mod.current()}-{etiquette}"
    code = dossier / "code"
    for rel in fichiers_code(BASE):
        cible = code / rel
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE / rel, cible)
    if paths.DATA_DIR.is_dir():
        shutil.copytree(paths.DATA_DIR, dossier / "data", ignore=shutil.ignore_patterns("*.tmp"))
    perso = dossier / "config"
    perso.mkdir(parents=True, exist_ok=True)
    for src in (paths.CONFIG_FILE, paths.DECK_FILE, paths.JEUX_FILE, paths.FAN_NAMES_FILE, paths.USER_ROOT / ".env"):
        if src.is_file():
            shutil.copy2(src, perso / src.name)
    _ecrire(dossier / "manifeste.json", {"version": version_mod.current(), "date": time.time(), "code": [r.as_posix() for r in fichiers_code(BASE)]})
    return dossier
