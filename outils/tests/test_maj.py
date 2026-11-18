"""Test de bout en bout des mises à jour, dans un dossier SÉPARÉ (jamais le NEXUS en service, jamais le port 8000).

1. Installation propre depuis l'archive de release (comme une amie qui la télécharge) : aucun fichier personnel,
   assistant de première configuration (réponses envoyées au clavier), dépôt proposé depuis le fichier DEPOT.
2. Faux GitHub local (NEXUS_MAJ_API_TEST) : GitHub injoignable, jeton invalide, limite de requêtes, à jour.
3. Release 1.0.1 : détection, proposition, mot de passe exigé, archive CORROMPUE refusée, puis installation réussie
   (lancer.bat simulé : code 3 → maj_demarrage.py → redémarrage), données / config / profil perso intacts.
4. Retour à la version précédente.
5. Release 1.0.3 dont la migration ÉCHOUE au test de démarrage : restauration automatique (code, data, config).
6. Aucune erreur dans les journaux du serveur ; le jeton n'apparaît nulle part (réponses, config.json, journaux).
Usage : python outils/tests/test_maj.py [--garder]   (--garder : ne supprime pas le dossier de test)"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "outils"))
import release  # noqa: E402

DEPOT = "nexus-test/faux-depot"
MDP = "motdepasse-de-test"
JETON = "github_pat_" + "T3st" * 10          # faux jeton (format valide, ne donne accès à rien)
KEYRING_SERVICE = "NEXUS-panel-mises-a-jour"

passed = failed = 0


def ok(c, m):
    global passed, failed
    print(("OK    " if c else "ÉCHEC ") + m, flush=True)
    passed += bool(c)
    failed += not c
    return c


def port_libre() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# --------------------------------------------------------------------------- #
#  Faux GitHub
# --------------------------------------------------------------------------- #
class FauxGitHub:
    def __init__(self):
        self.mode = "ok"                 # ok | hors_ligne | jeton_invalide | limite
        self.release = None              # {"version", "zip": Path, "sha": bytes}
        self.vus = []                    # (chemin, en-tête Authorization)
        fg = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _envoyer(self, code, corps=b"", type_="application/json", entetes=None):
                self.send_response(code)
                self.send_header("Content-Type", type_)
                self.send_header("Content-Length", str(len(corps)))
                for k, v in (entetes or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(corps)

            def do_GET(self):
                fg.vus.append((self.path, self.headers.get("Authorization")))
                if fg.mode == "hors_ligne":
                    self.connection.close()      # connexion coupée sans réponse
                    return
                if self.path.startswith("/fichiers/"):
                    nom = self.path.split("/")[-1]
                    r = fg.release
                    if r and nom == r["zip"].name:
                        return self._envoyer(200, r["zip"].read_bytes(), "application/zip")
                    if r and nom == r["zip"].name + ".sha256":
                        return self._envoyer(200, r["sha"], "text/plain")
                    return self._envoyer(404, b"{}")
                if fg.mode == "jeton_invalide":
                    return self._envoyer(401, b'{"message":"Bad credentials"}')
                if fg.mode == "limite":
                    return self._envoyer(403, b'{"message":"API rate limit exceeded"}',
                                         entetes={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(time.time()) + 1800)})
                pre = f"/repos/{DEPOT}/releases/"
                r = fg.release
                if self.path == pre + "latest":
                    if not r:
                        return self._envoyer(404, b'{"message":"Not Found"}')
                    z = r["zip"]
                    data = {"tag_name": f"v{r['version']}", "name": f"NEXUS {r['version']}", "published_at": "2026-11-10T12:00:00Z",
                            "body": f"### Ajouté\n- nouveautés de la {r['version']}", "html_url": "https://github.com/" + DEPOT,
                            "assets": [{"id": 11, "name": z.name, "size": z.stat().st_size},
                                       {"id": 12, "name": z.name + ".sha256", "size": len(r["sha"])}]}
                    return self._envoyer(200, json.dumps(data).encode())
                if self.path.startswith(pre + "assets/") and r:
                    nom = r["zip"].name if self.path.endswith("/11") else r["zip"].name + ".sha256"
                    return self._envoyer(302, entetes={"Location": f"{fg.url}/fichiers/{nom}"})
                return self._envoyer(404, b'{"message":"Not Found"}')

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def publier(self, version: str, zip_: Path, corrompre: bool = False):
        h = hashlib.sha256(zip_.read_bytes()).hexdigest()
        if corrompre:
            h = ("0" if h[0] != "0" else "1") + h[1:]
        self.release = {"version": version, "zip": zip_, "sha": f"{h}  {zip_.name}\n".encode()}


# --------------------------------------------------------------------------- #
#  Copie de NEXUS installée + « lancer.bat » simulé
# --------------------------------------------------------------------------- #
class Panel:
    def __init__(self, dossier: Path, api: str):
        self.dir, self.api, self.port = dossier, api, port_libre()
        self.proc = None
        self.journal = dossier.parent / "journal-serveur.txt"
        self.env = dict(os.environ, NEXUS_PORT=str(self.port), NEXUS_LANCEUR="1", NEXUS_NO_BOT="1", NEXUS_OPEN_BROWSER="0",
                        NEXUS_DECK_DRYRUN="1", NEXUS_MAJ_API_TEST=api, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

    def demarrer(self):
        self.log = open(self.journal, "a", encoding="utf-8")
        self.proc = subprocess.Popen([sys.executable, "app.py"], cwd=self.dir, env=self.env, stdout=self.log,
                                     stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(240):
            if self.proc.poll() is not None:
                raise RuntimeError(f"le serveur de test s'est arrêté (code {self.proc.returncode})")
            try:
                return self.get("/api/version")
            except OSError:
                time.sleep(.5)
        raise RuntimeError("le serveur de test ne répond pas")

    def arreter(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(20)
        if self.proc:
            self.log.close()

    def get(self, chemin):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{chemin}", timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(self, chemin, corps=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{chemin}", data=json.dumps(corps or {}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")

    def cycle_lanceur(self, delai=60) -> str:
        """Comme lancer.bat : attend la sortie (code 3), lance maj_demarrage.py, puis redémarre app.py."""
        code = self.proc.wait(delai)
        self.log.close()
        if code != 3:
            raise RuntimeError(f"le serveur est sorti avec le code {code} au lieu de 3")
        r = subprocess.run([sys.executable, "maj_demarrage.py"], cwd=self.dir, env=self.env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=400)
        with open(self.journal, "a", encoding="utf-8") as f:
            f.write(r.stdout + r.stderr)
        self.demarrer()
        return r.stdout + r.stderr


def zip_de(source: Path, version: str, dest: Path, fichiers: list[str]) -> Path:
    (source / "VERSION").write_text(version + "\n", encoding="utf-8")
    archive, _ = release.construire_archive(version, DEPOT, fichiers, dest=dest, source=source)
    return archive


def user_version(db: Path) -> int:
    con = sqlite3.connect(db)
    try:
        return con.execute("PRAGMA user_version").fetchone()[0]
    finally:
        con.close()


def keyring_effacer():
    try:
        import keyring
        keyring.delete_password(KEYRING_SERVICE, DEPOT)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    garder = "--garder" in sys.argv
    racine = Path(tempfile.mkdtemp(prefix="nexus-test-maj-"))
    print(f"Dossier de test : {racine}")
    git = release.outil("git")
    fichiers = release.fichiers_suivis(git)
    fg = FauxGitHub()
    panel = None
    keyring_effacer()
    try:
        # ---- sources des releases : copies des fichiers suivis par Git ---------------------------------------
        src = racine / "source"
        for rel in fichiers:
            if (BASE / rel).is_file():
                (src / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(BASE / rel, src / rel)
        rels = racine / "releases"
        z100 = zip_de(src, "1.0.0", rels, fichiers)
        (src / "outils" / "temoin_101.py").write_text("# fichier apparu en 1.0.1\n", encoding="utf-8")
        z101 = zip_de(src, "1.0.1", rels, fichiers + ["outils/temoin_101.py"])
        (src / "outils" / "temoin_101.py").unlink()
        db_py, cfg_py = (src / "db.py").read_text(encoding="utf-8"), (src / "config.py").read_text(encoding="utf-8")
        (src / "db.py").write_text(db_py.replace("VERSION = MIGRATIONS[-1][0]",
            'MIGRATIONS.append((99, "_migration_test_echec"))\n\n\ndef _migration_test_echec(con):\n'
            '    con.execute("CREATE TABLE temoin_echec (x)")\n    raise RuntimeError("migration de test volontairement en échec")\n\n\n'
            "VERSION = MIGRATIONS[-1][0]"), encoding="utf-8")
        (src / "config.py").write_text(cfg_py.replace("MIGRATIONS = [(1, _migration_1)]",
            'MIGRATIONS = [(1, _migration_1), (2, lambda c: {**c, "temoin_migration": True})]'), encoding="utf-8")
        z103 = zip_de(src, "1.0.3", rels, fichiers)

        # ---- 1. installation propre depuis l'archive ---------------------------------------------------------
        with zipfile.ZipFile(z100) as z:
            noms = z.namelist()
            z.extractall(racine / "install")
        inst = racine / "install" / "NEXUS-1.0.0"
        ok(not any(n.split("/", 1)[1].split("/")[0] in ("data", "logs", "versions", "maj", "sauvegardes-maj") or
                   n.endswith(("/config.json", "/deck.json", "/jeux.json")) for n in noms),
           "archive : ni data/, ni config réelle, ni journaux ou sauvegardes")
        scan = subprocess.run([sys.executable, str(BASE / "outils" / "scan_perso.py"), str(z100)], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        ok(scan.returncode == 0, "archive : aucune donnée personnelle (scan_perso)")
        ok((inst / "DEPOT").read_text(encoding="utf-8").strip() == DEPOT, "archive : fichier DEPOT (dépôt d'origine)")
        reponses = f"{MDP}\n{MDP}\nn\n\n"          # mot de passe ×2, pas de bot Discord, dépôt proposé accepté
        r = subprocess.run([sys.executable, "configurer.py"], cwd=inst, input=reponses, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=60)
        cfg = json.loads((inst / "config.json").read_text(encoding="utf-8"))
        ok(r.returncode == 0 and cfg["deck"]["password_hash"].startswith("pbkdf2_sha256$") and not cfg["deck"]["password"],
           "assistant de première configuration : mot de passe enregistré en empreinte seulement")
        ok(cfg.get("mises_a_jour", {}).get("depot") == DEPOT, f"assistant : dépôt surveillé proposé et retenu ({cfg.get('mises_a_jour')})")
        ok((inst / "deck.json").is_file() and not (inst / "data" / "nexus.db").exists()
           and not (inst / "data" / "agenda.json").exists(),
           "assistant : deck.json d'exemple, data/ encore vide (aucune donnée)")

        # profil personnel + données témoins (ne doivent jamais être touchés)
        shutil.copytree(inst / "profils" / "_modele", inst / "profils" / "mon-perso")
        pj = inst / "profils" / "mon-perso" / "profil.json"
        pj.write_text(pj.read_text(encoding="utf-8").replace('"Mon profil"', '"Mon perso"'), encoding="utf-8")
        perso_avant = pj.read_bytes()

        panel = Panel(inst, fg.url)
        v = panel.demarrer()
        ok(v["version"] == "1.0.0", "installation propre : NEXUS 1.0.0 démarre avec des données vides")
        (inst / "data" / "temoin.txt").write_text("mes données", encoding="utf-8")
        cfg_avant = json.loads((inst / "config.json").read_text(encoding="utf-8"))
        uv_avant = user_version(inst / "data" / "nexus.db")
        m = panel.get("/api/maj")
        ok(m["reglages"]["depot"] == DEPOT and not m["jeton"]["enregistre"] and m["redemarrage_auto"], "état initial des mises à jour")

        # ---- 2. erreurs claires --------------------------------------------------------------------------------
        fg.mode = "hors_ligne"
        _, m = panel.post("/api/maj/verifier")
        ok(m["verification"]["resultat"] == "erreur" and "injoignable" in m["verification"]["erreur"],
           f"GitHub hors ligne : {m['verification']['erreur']}")
        fg.mode = "jeton_invalide"
        c, m = panel.post("/api/maj/jeton", {"jeton": JETON})
        ok(c == 200 and m["jeton"]["enregistre"] and "invalide" in (m["verification"]["erreur"] or ""),
           f"jeton invalide : {m['verification']['erreur']} (rangé : {m['jeton']['ou']})")
        ok(JETON not in json.dumps(m), "le jeton n'est jamais renvoyé par l'API du panel")
        ok(JETON not in (inst / "config.json").read_text(encoding="utf-8") or m["jeton"]["ou"] == "config",
           f"jeton rangé hors de config.json quand c'est possible (gestionnaire Windows : {m['jeton']['ou'] == 'windows'})")
        c, m2 = panel.post("/api/maj/jeton", {"jeton": "mot-de-passe-github"})
        ok(c == 400, "un texte qui n'est pas un jeton GitHub est refusé")
        fg.mode = "limite"
        _, m = panel.post("/api/maj/verifier")
        ok("limite de requêtes" in (m["verification"]["erreur"] or ""), f"limite de requêtes : {m['verification']['erreur']}")
        fg.mode = "ok"
        fg.publier("1.0.0", z100)
        _, m = panel.post("/api/maj/verifier")
        ok(m["verification"]["a_jour"] is True and not m["disponible"], "release identique : « à jour »")

        # ---- 3. release 1.0.1 : détection, refus si corrompue, installation -----------------------------------
        fg.publier("1.0.1", z101, corrompre=True)
        fg.vus.clear()
        _, m = panel.post("/api/maj/verifier")
        d = m["disponible"]
        ok(d and d["version"] == "1.0.1" and d["archive"]["taille"] > 1e6 and "1.0.1" in d["notes"],
           "détection de la 1.0.1 (notes et taille)")
        c, r = panel.post("/api/maj/installer", {"mot_de_passe": MDP})
        ok(c == 400 and "validation" in r.get("error", ""), f"installation refusée sans validation explicite ({c})")
        c, r = panel.post("/api/maj/installer", {"mot_de_passe": MDP, "validation": "1.0.0"})
        ok(c == 400, "installation refusée si la validation porte sur une autre version")
        c, r = panel.post("/api/maj/installer", {"mot_de_passe": "faux", "validation": "1.0.1"})
        ok(c == 403, "installation refusée sans le bon mot de passe")
        c, r = panel.post("/api/maj/installer", {"validation": "1.0.1"})
        ok(c == 403, "installation refusée sans mot de passe")
        c, r = panel.post("/api/maj/installer", {"mot_de_passe": MDP, "validation": panel.get("/api/maj")["disponible"]["version"]})
        for _ in range(60):
            t = panel.get("/api/maj")["travail"]
            if t["etape"] == "erreur":
                break
            time.sleep(.5)
        ok(t["etape"] == "erreur" and "SHA256" in (t["erreur"] or ""), f"archive corrompue refusée : {t['erreur']}")
        sauvs = list((inst / "sauvegardes-maj").glob("*")) if (inst / "sauvegardes-maj").exists() else []
        ok(panel.proc.poll() is None and panel.get("/api/version")["version"] == "1.0.0"
           and not (inst / "maj" / "en_cours.json").exists() and not sauvs and not (inst / "maj" / "1.0.1").exists(),
           "après le refus : rien n'a été touché (même version, archive supprimée, aucune sauvegarde ni travail en attente)")

        fg.publier("1.0.1", z101)
        panel.post("/api/maj/verifier")
        fg.vus.clear()
        c, r = panel.post("/api/maj/installer", {"mot_de_passe": MDP, "validation": panel.get("/api/maj")["disponible"]["version"]})
        ok(c == 200, "installation lancée (clic + mot de passe)")
        etapes = set()
        while panel.proc.poll() is None:
            try:
                etapes.add(panel.get("/api/maj")["travail"]["etape"])
            except OSError:
                break
            time.sleep(.2)
        sortie = panel.cycle_lanceur()
        v = panel.get("/api/version")
        m = panel.get("/api/maj")
        ok(v["version"] == "1.0.1", f"version 1.0.1 installée et démarrée (étapes vues : {sorted(e for e in etapes if e)})")
        ok("installée et testée" in sortie, "test de démarrage passé avant de rendre la main")
        ok(m["dernier_resultat"] and m["dernier_resultat"]["ok"], f"bandeau de résultat : {m['dernier_resultat'] and m['dernier_resultat']['message']}")
        ok((inst / "outils" / "temoin_101.py").is_file(), "fichiers de la release mis en place")
        ok((inst / "data" / "temoin.txt").read_text(encoding="utf-8") == "mes données", "data/ intact")
        ok(json.loads((inst / "config.json").read_text(encoding="utf-8")) == cfg_avant, "config.json intact")
        ok(pj.read_bytes() == perso_avant, "profil personnel intact")
        ok(len(m["sauvegardes"]) == 1 and m["retour_possible"], "sauvegarde horodatée faite avant l'installation")
        sauv = inst / "sauvegardes-maj" / m["sauvegardes"][0]["dossier"]
        ok((sauv / "data" / "temoin.txt").is_file() and (sauv / "config" / "config.json").is_file() and (sauv / "code" / "app.py").is_file(),
           "la sauvegarde contient le code, data/ et la configuration")
        api_vus = [a for p, a in fg.vus if p.startswith("/repos/")]
        fichiers_vus = [a for p, a in fg.vus if p.startswith("/fichiers/")]
        ok(api_vus and all(a == f"Bearer {JETON}" for a in api_vus), "jeton envoyé à l'API GitHub")
        ok(fichiers_vus and not any(fichiers_vus), "jeton JAMAIS envoyé à l'hébergeur des fichiers (redirection)")
        panel.post("/api/maj/resultat-vu")

        # ---- 4. retour à la version précédente --------------------------------------------------------------------
        c, r = panel.post("/api/maj/revenir", {"mot_de_passe": "faux", "validation": "1.0.0"})
        ok(c == 403, "retour refusé sans le bon mot de passe")
        c, r = panel.post("/api/maj/revenir", {"mot_de_passe": MDP, "validation": "1.0.0"})
        ok(c == 200 and r["vers"] == "1.0.0", "retour à la version précédente lancé")
        panel.cycle_lanceur()
        m = panel.get("/api/maj")
        ok(panel.get("/api/version")["version"] == "1.0.0", "retour : version 1.0.0 de nouveau")
        ok(not (inst / "outils" / "temoin_101.py").exists(), "retour : fichiers de la 1.0.1 retirés")
        ok((inst / "data" / "temoin.txt").is_file() and pj.read_bytes() == perso_avant, "retour : données et profil perso gardés")
        ok(m["dernier_resultat"]["ok"] and m["dernier_resultat"]["type"] == "retour", f"retour : {m['dernier_resultat']['message']}")
        panel.post("/api/maj/resultat-vu")

        # ---- 5. migration en échec : restauration automatique ------------------------------------------------------
        fg.publier("1.0.3", z103)
        panel.post("/api/maj/verifier")
        cfg_avant = json.loads((inst / "config.json").read_text(encoding="utf-8"))
        c, r = panel.post("/api/maj/installer", {"mot_de_passe": MDP, "validation": panel.get("/api/maj")["disponible"]["version"]})
        sortie = panel.cycle_lanceur(90)
        m = panel.get("/api/maj")
        res = m["dernier_resultat"] or {}
        ok(not res.get("ok") and "restaurée automatiquement" in (res.get("message") or ""), f"migration en échec : {res.get('message')}")
        ok(panel.get("/api/version")["version"] == "1.0.0", "après l'échec : la 1.0.0 tourne de nouveau")
        cfg_apres = json.loads((inst / "config.json").read_text(encoding="utf-8"))
        ok(cfg_apres == cfg_avant and "temoin_migration" not in cfg_apres, "config.json restauré (migration de config annulée)")
        ok(user_version(inst / "data" / "nexus.db") == uv_avant, f"base restaurée (schéma {uv_avant})")
        ok("migration de test volontairement en échec" in sortie, "la cause de l'échec est indiquée")
        ok(m["disponible"] and m["disponible"]["version"] == "1.0.3", "la 1.0.3 reste proposée (rien d'installé en douce)")
        _, m = panel.post("/api/maj/plus-tard", {})
        ok(m["rappel_repousse"], "« Plus tard » : rappel repoussé")

        # ---- 6. journaux propres ---------------------------------------------------------------------------------
        panel.arreter()
        journal = panel.journal.read_text(encoding="utf-8", errors="replace")
        lignes = [ligne for ligne in journal.splitlines() if "Traceback" in ligne or " 500 " in ligne or "ERROR" in ligne]
        ok(not lignes, f"aucune erreur dans les journaux du serveur ({lignes[:3]})")
        ok(JETON not in journal, "le jeton n'apparaît pas dans les journaux")
        ok(not list((inst / "maj").glob("1.0.*")), "fichiers téléchargés nettoyés")
    finally:
        if panel:
            panel.arreter()
        fg.srv.shutdown()
        keyring_effacer()
        if not garder:
            shutil.rmtree(racine, ignore_errors=True)
    print(f"\n{passed} OK, {failed} échec(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
