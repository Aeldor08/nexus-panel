"""Mise en place d'une mise à jour AU DÉMARRAGE (lancé par lancer.bat juste avant app.py).

Bibliothèque standard uniquement : ce fichier doit fonctionner même si le reste du code est cassé.
Travail décrit par maj/en_cours.json (écrit par maj.py après téléchargement + vérification SHA256 + sauvegarde) :
- « a_appliquer » : copie le code et les profils FOURNIS par la release (jamais data/, la config, l'environnement
  ni les profils personnels), réinstalle les dépendances si requirements.txt a changé, puis « a_tester » ;
- « a_tester »    : démarre la nouvelle version dans un processus à part (app.py --test-demarrage : migrations,
  serveur sur un port libre, /api/version doit répondre la bonne version). Échec → RESTAURATION automatique
  de la sauvegarde (code + data/ + config), puis le panel redémarre dans l'ancienne version ;
- « a_restaurer » : bouton « Revenir à la version précédente » (code seulement, les données sont gardées).
Le résultat est écrit dans maj/resultat.json : le panel l'affiche (réussite, ou échec et restauration).
"""

from __future__ import annotations

import filecmp
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
MAJ_DIR = BASE / "maj"
EN_COURS = MAJ_DIR / "en_cours.json"
RESULTAT = MAJ_DIR / "resultat.json"
PROTEGES = {"data", "config.json", "deck.json", "jeux.json", "fan_names.json", ".env", ".venv", "venv", "logs",
            "versions", "partage", "maj", "sauvegardes-maj", "LibreHardwareMonitor", "actions", ".git",
            "dist", ".ruff_cache", ".pytest_cache", "sauvegardes", "backups", "reference", "references"}
TEST_TIMEOUT = 150


def _lire(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ecrire(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def _dire(msg: str) -> None:
    print(f"[Mise à jour] {msg}", flush=True)


def _fichiers(racine: Path) -> list[Path]:
    out = []
    for p in racine.rglob("*"):
        if p.is_file():
            rel = p.relative_to(racine)
            if rel.parts[0] in PROTEGES or "__pycache__" in rel.parts or p.suffix in (".pyc", ".lnk", ".log", ".tmp"):
                continue
            out.append(rel)
    return out


def copier_code(source: Path) -> int:
    n = 0
    for rel in _fichiers(source):
        cible = BASE / rel
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, cible)
        n += 1
    return n


def restaurer(sauvegarde: Path, code_seulement: bool) -> None:
    code = sauvegarde / "code"
    if not code.is_dir():
        raise RuntimeError(f"sauvegarde introuvable : {sauvegarde}")
    manifeste = _lire(sauvegarde / "manifeste.json") or {}
    anciens = set(manifeste.get("code") or [])
    # fichiers apparus avec la nouvelle version (code seulement) : retirés, l'ancienne version ne les connaît pas
    if anciens:
        for rel in _fichiers(BASE):
            if rel.as_posix() not in anciens and rel.suffix in (".py", ".js", ".css", ".html", ".bat") and rel.parts[0] != "profils":
                try:
                    (BASE / rel).unlink()
                except OSError:
                    pass
    copier_code(code)
    if not code_seulement:
        if (sauvegarde / "data").is_dir():
            if (BASE / "data").exists():
                shutil.rmtree(BASE / "data")
            shutil.copytree(sauvegarde / "data", BASE / "data")
        for f in (sauvegarde / "config").glob("*"):
            shutil.copy2(f, BASE / f.name)


def _pip_si_besoin(sauvegarde: Path) -> None:
    ancien, nouveau = sauvegarde / "code" / "requirements.txt", BASE / "requirements.txt"
    if nouveau.exists() and (not ancien.exists() or not filecmp.cmp(ancien, nouveau, shallow=False)):
        _dire("nouvelles dépendances : installation (Internet nécessaire)…")
        subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(nouveau)],
                       cwd=BASE, timeout=900, check=True)


def tester_demarrage(attendue: str) -> tuple[bool, str]:
    """Démarre la version installée dans un processus séparé et vérifie qu'elle répond la bonne version."""
    try:
        p = subprocess.run([sys.executable, str(BASE / "app.py"), "--test-demarrage", attendue], cwd=BASE,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TEST_TIMEOUT,
                           env={**os.environ, "NEXUS_OPEN_BROWSER": "0", "NEXUS_NO_BOT": "1"})
    except subprocess.TimeoutExpired:
        return False, "le test de démarrage n'a pas répondu à temps"
    if p.returncode == 0:
        return True, ""
    lignes = [l for l in (p.stdout + "\n" + p.stderr).splitlines() if l.strip()]
    return False, (lignes[-1] if lignes else f"code de sortie {p.returncode}")[:300]


def main() -> int:
    travail = _lire(EN_COURS)
    if not travail:
        return 0
    etat = travail.get("etat")
    sauv = Path(travail.get("sauvegarde") or "")
    de, vers = travail.get("de"), travail.get("vers")
    try:
        if etat == "a_restaurer":
            _dire(f"retour à la version {vers}…")
            restaurer(sauv, code_seulement=bool(travail.get("code_seulement", True)))
            _ecrire(RESULTAT, {"ok": True, "type": "retour", "de": de, "vers": vers, "date": time.time(),
                               "message": f"Retour à la version {vers} effectué (tes données sont conservées)."})
            EN_COURS.unlink(missing_ok=True)
            return 0
        if etat == "a_appliquer":
            travail["essais"] = int(travail.get("essais") or 0) + 1
            if travail["essais"] > 2:
                raise RuntimeError("la mise en place a déjà échoué plusieurs fois")
            _ecrire(EN_COURS, travail)
            _dire(f"installation de la version {vers}…")
            n = copier_code(Path(travail["fichiers"]))
            _dire(f"{n} fichiers mis en place")
            _pip_si_besoin(sauv)
            travail["etat"] = etat = "a_tester"
            _ecrire(EN_COURS, travail)
        if etat == "a_tester":
            _dire("test de démarrage de la nouvelle version (migrations comprises)…")
            ok, err = tester_demarrage(vers)
            if not ok:
                raise RuntimeError(f"test de démarrage échoué : {err}")
            _ecrire(RESULTAT, {"ok": True, "type": "installation", "de": de, "vers": vers, "date": time.time(),
                               "message": f"Mise à jour vers la version {vers} réussie."})
            EN_COURS.unlink(missing_ok=True)
            shutil.rmtree(MAJ_DIR / str(vers), ignore_errors=True)
            _dire(f"version {vers} installée et testée ✔")
            return 0
    except Exception as e:
        _dire(f"ÉCHEC : {e}")
        try:
            if sauv.is_dir():
                _dire("restauration automatique de la sauvegarde (code, données, configuration)…")
                restaurer(sauv, code_seulement=False)
                msg = f"La mise à jour vers {vers} a échoué ({e}). La version {de} a été restaurée automatiquement, avec tes données."
            else:
                msg = f"La mise à jour vers {vers} a échoué ({e}) et la sauvegarde est introuvable : vois sauvegardes-maj\\."
        except Exception as e2:
            msg = f"La mise à jour vers {vers} a échoué ({e}) ET la restauration aussi ({e2}) : copie à la main sauvegardes-maj\\…\\code."
        _ecrire(RESULTAT, {"ok": False, "type": "installation", "de": de, "vers": vers, "date": time.time(), "message": msg})
        EN_COURS.unlink(missing_ok=True)
        if vers:
            shutil.rmtree(MAJ_DIR / str(vers), ignore_errors=True)   # archive téléchargée : inutile désormais
        _dire(msg)
    return 0


if __name__ == "__main__":
    code = main()
    if "--puis-lancer" in sys.argv:                       # redémarrage sans lancer.bat (repli)
        os.execv(sys.executable, [sys.executable, str(BASE / "app.py")])
    sys.exit(code)
