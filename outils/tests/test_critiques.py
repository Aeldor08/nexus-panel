"""Parties critiques de NEXUS, sans réseau ni navigateur (dossier de données temporaire) :
configuration, base de données et migrations, authentification (garde du serveur), import de profils,
calcul des statistiques personnelles.
Usage : python outils/tests/test_critiques.py <dossier de NEXUS>"""

import datetime as dt
import io
import json
import os
import sqlite3
import sys
import tempfile
import time
import zipfile
from pathlib import Path

BASE = Path(sys.argv[1])
os.chdir(BASE)
sys.path.insert(0, str(BASE))
TMP = Path(tempfile.mkdtemp(prefix="nexus-critiques-"))
os.environ.update(NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1", NEXUS_DATA_DIR=str(TMP), NEXUS_OPEN_BROWSER="0")

import config
import db
import paths
import profiles

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  [ECHEC]", m)


assert paths.USER_ROOT == TMP, paths.USER_ROOT  # jamais les vraies données

# =========================================================================== configuration
print("--- configuration")
if config.CONFIG_FILE.exists():
    config.CONFIG_FILE.unlink()
c = config.load(force=True)
ok(c["deck"]["rate_limit_per_minute"] == config.DEFAULTS["deck"]["rate_limit_per_minute"], "sans config.json : valeurs par défaut")
ok(any("absent" in w for w in config.warnings), "config.json absent : avertissement")

config.CONFIG_FILE.write_text("{ pas du json", encoding="utf-8")
c = config.load(force=True)
ok(any("illisible" in w for w in config.warnings) and c["deck"] == config.DEFAULTS["deck"], "config.json illisible : défauts + avertissement")

config.CONFIG_FILE.write_text(json.dumps({"deck": {"rate_limit_per_minute": 7}, "inconnu": 1, "alerts": {"cpu_temp_warn": 70}}), encoding="utf-8")
t = time.time() + 2
os.utime(config.CONFIG_FILE, (t, t))
c = config.load()
ok(c["deck"]["rate_limit_per_minute"] == 7, "valeur de l'utilisateur gardée")
ok("inconnu" not in c, "clé inconnue ignorée (pas de section inventée)")
ok(all(k in c["alerts"] for k in config.DEFAULTS["alerts"]), "section fusionnée : les autres clés gardent leur défaut")

# config.json enregistré avec un BOM (Bloc-notes « UTF-8 avec BOM », PowerShell) : lu normalement
config.CONFIG_FILE.write_bytes(b"\xef\xbb\xbf" + json.dumps({"deck": {"rate_limit_per_minute": 7}, "alerts": {"cpu_temp_warn": 70}}).encode())
c = config.load(force=True)
ok(c["deck"]["rate_limit_per_minute"] == 7 and not any("illisible" in w for w in config.warnings), "config.json avec BOM lu normalement")

# migration du schéma : sauvegarde puis section mises_a_jour explicite
(paths.APP_DIR / "DEPOT").exists() and print("  (DEPOT présent dans le dépôt : ignoré par ce test)")
version_cfg = config.migrer()
data = json.loads(config.CONFIG_FILE.read_text(encoding="utf-8"))
ok(version_cfg == config.CONFIG_VERSION and data.get("config_version") == config.CONFIG_VERSION, f"migration : schéma {version_cfg}")
ok(isinstance(data.get("mises_a_jour"), dict) and "intervalle_heures" in data["mises_a_jour"], "migration : section mises_a_jour créée")
ok(data["deck"]["rate_limit_per_minute"] == 7, "migration : valeurs de l'utilisateur intactes")
ok(any((paths.DATA_DIR / "backups").glob("config-*.json")) or any(paths.DATA_DIR.rglob("config*.json")), "migration : sauvegarde de config.json")

# --- jeton du bot Discord : rangé dans le gestionnaire d'identifiants (faux keyring en mémoire)
import identifiants

coffre = {}


class FauxKeyring:
    @staticmethod
    def get_password(s, k):
        return coffre.get((s, k))

    @staticmethod
    def set_password(s, k, v):
        coffre[(s, k)] = v

    @staticmethod
    def delete_password(s, k):
        coffre.pop((s, k), None)


identifiants._keyring = lambda: FauxKeyring
JETON = "MTIz.abc.def-jeton-de-test"
config.CONFIG_FILE.write_text(json.dumps({"discord": {"enabled": True, "token": JETON, "user_id": "1", "alert_channel_id": "2"}}), encoding="utf-8")
config.ranger_secrets()
brut = json.loads(config.CONFIG_FILE.read_text(encoding="utf-8"))
ok(brut["discord"]["token"] == "" and brut["discord"].get("token_windows") is True, "jeton Discord retiré de config.json")
ok(coffre.get((identifiants.SERVICE_DISCORD, identifiants.CLE_JETON_BOT)) == JETON, "jeton Discord rangé dans Windows")
ok(config.load(force=True)["discord"]["token"] == JETON, "jeton Discord relu depuis Windows par NEXUS")
config.CONFIG_FILE.write_text(json.dumps({"discord": {"enabled": False, "token": ""}}), encoding="utf-8")
config.ranger_secrets()
ok((identifiants.SERVICE_DISCORD, identifiants.CLE_JETON_BOT) not in coffre, "bot retiré : jeton effacé de Windows")
identifiants._keyring = lambda: None
config.CONFIG_FILE.write_text(json.dumps({"discord": {"token": JETON}}), encoding="utf-8")
config.ranger_secrets()
ok(json.loads(config.CONFIG_FILE.read_text(encoding="utf-8"))["discord"]["token"] == JETON, "sans gestionnaire : jeton gardé dans config.json (repli)")
config.CONFIG_FILE.unlink()
config.load(force=True)

# =========================================================================== base de données
print("--- base de données")
v = db.migrate()
con = sqlite3.connect(db.DB_FILE)
ok(con.execute("PRAGMA user_version").fetchone()[0] == db.VERSION == v, f"base neuve : schéma {db.VERSION}")
tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
ok({"reglages", "activite_heure", "temps_appli", "sessions"} <= tables, f"tables créées : {sorted(tables)[:6]}…")
con.close()
db.set_setting("essai", {"a": [1, 2]})
ok(db.get_setting("essai") == {"a": [1, 2]} and db.get_setting("absent", 5) == 5, "réglages : écriture / lecture / défaut")
ok(db.migrate() == db.VERSION, "migrate() une 2e fois : rien à faire")

# ancienne base (schéma 1) : sauvegardée avant migration, données gardées
vieux = TMP / "vieille"
vieux.mkdir()
ancien_fichier, ancien_dir = db.DB_FILE, db.store.DATA_DIR
db.DB_FILE = vieux / "nexus.db"
db.store.DATA_DIR = vieux
con = sqlite3.connect(db.DB_FILE)
for stmt in db._split(db.MIGRATIONS[0][1]):
    con.execute(stmt)
con.execute("PRAGMA user_version = 1")
con.execute("INSERT INTO reglages(cle, valeur) VALUES('garde', '42')")
con.commit()
con.close()
db._ready = False
db.migrate()
con = sqlite3.connect(db.DB_FILE)
ok(con.execute("PRAGMA user_version").fetchone()[0] == db.VERSION, "ancienne base migrée jusqu'au dernier schéma")
ok(con.execute("SELECT valeur FROM reglages WHERE cle='garde'").fetchone()[0] == "42", "ancienne base : données conservées")
con.close()
ok(any((vieux / "backups").glob("nexus-v1-*.db")), "ancienne base : copie de sauvegarde avant migration")

# migration qui échoue : annulée, schéma inchangé, connexion fermée
mig = list(db.MIGRATIONS)
db.MIGRATIONS.append((db.VERSION + 1, "CREATE TABLE ok_avant(x); INSERT INTO table_inexistante VALUES(1)"))
try:
    db._ready = False
    db.migrate()
    ok(False, "une migration en erreur doit lever une exception")
except sqlite3.Error:
    con = sqlite3.connect(db.DB_FILE)
    ok(con.execute("PRAGMA user_version").fetchone()[0] == db.VERSION, "migration en erreur : schéma inchangé")
    ok(con.execute("SELECT name FROM sqlite_master WHERE name='ok_avant'").fetchone() is None, "migration en erreur : annulée en entier")
    con.close()
finally:
    db.MIGRATIONS[:] = mig
    db.DB_FILE, db.store.DATA_DIR = ancien_fichier, ancien_dir
    db._ready = False
    db._local.con = None

# =========================================================================== authentification (garde du serveur)
print("--- authentification")
from fastapi.testclient import TestClient

import app

pc = TestClient(app.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8000")
tel = TestClient(app.app, client=("192.168.1.50", 5000), base_url="http://127.0.0.1:8000")
web = TestClient(app.app, client=("8.8.8.8", 5000), base_url="http://127.0.0.1:8000")

ok(pc.get("/api/version").status_code == 200, "PC (127.0.0.1), version source sans jeton : accès")
ok(pc.get("/api/version", headers={"host": "evil.example"}).status_code == 421, "en-tête Host étranger refusé (rebinding DNS)")
ok(pc.post("/api/maj/verifier", data="x", headers={"content-type": "text/plain"}).status_code == 415, "POST sans JSON refusé (autre site)")

app.TOKEN = "jeton-local-de-test"
try:
    ok(pc.get("/api/version").status_code == 403, "version exe : jeton local obligatoire")
    ok(pc.get("/api/version", headers={"x-nexus-token": "faux"}).status_code == 403, "version exe : mauvais jeton refusé")
    r = pc.get("/api/version?token=jeton-local-de-test")
    ok(r.status_code == 200 and app.LOCAL_COOKIE in r.cookies, "version exe : ?token= accepté et pose le cookie")
    ok(pc.get("/api/version", cookies={app.LOCAL_COOKIE: "jeton-local-de-test"}).status_code == 200, "version exe : cookie accepté")
finally:
    app.TOKEN = ""

avant = app.remote_svc.enabled
try:
    app.remote_svc.enabled = False
    ok(tel.get("/api/version").status_code == 403, "téléphone : refusé si l'accès téléphone est coupé")
    app.remote_svc.enabled = True
    ok(web.get("/api/version").status_code == 403, "adresse Internet : toujours refusée")
    ok(tel.get("/api/version").status_code == 401, "téléphone non appairé : 401 sur l'API")
    r = tel.get("/", follow_redirects=False)
    ok(r.status_code == 303 and r.headers.get("location") == "/pair", "téléphone non appairé : page → /pair")
    ok(tel.get("/pair").status_code == 200, "page d'appairage publique")
    ok(tel.get("/api/maj").status_code == 403 and tel.get("/api/remote").status_code == 403, "téléphone : mises à jour et appairage réservés au PC")
    p = app.remote_svc.pairing() or app.remote_svc.start_pairing()
    ok(tel.post("/api/pair/claim", json={"code": "000000" if p["code"] != "000000" else "111111"}).status_code == 403, "mauvais code refusé")
    p = app.remote_svc.start_pairing()
    r = tel.post("/api/pair/claim", json={"code": p["code"], "name": "Test"})
    ok(r.status_code == 200, "bon code accepté")
    jeton = r.cookies.get(app.remote_mod.COOKIE)
    ok(tel.get("/api/version", cookies={app.remote_mod.COOKIE: jeton}).status_code == 200, "téléphone appairé : accès")
    ok(tel.post("/api/pair/claim", json={"code": p["code"]}).status_code == 403, "code à usage unique")
    for d in list(app.remote_svc.devices):
        app.remote_svc.revoke(d["id"])
    ok(tel.get("/api/version", cookies={app.remote_mod.COOKIE: jeton}).status_code == 401, "appareil révoqué : plus d'accès")
finally:
    app.remote_svc.enabled = avant

ok(pc.get("/api/deck/buttons").status_code in (401, 404, 405), "deck : actions inaccessibles sans session")
ok(pc.post("/api/deck/run", json={"id": "x"}).status_code == 401, "deck : lancer une action exige une session")

# =========================================================================== import de profils
print("--- import de profils")
lib = profiles.ProfileLibrary(TMP / "profils-test")
META = {"format": 1, "nom": "Profil Essai", "auteur": "Test", "version": "1.0", "modes": ["terminal"], "description": "essai"}


def zip_de(fichiers: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for nom, contenu in fichiers.items():
            z.writestr(nom, contenu)
    return buf.getvalue()


def refuse(data: bytes, quoi: str) -> None:
    try:
        lib.import_zip(data)
        ok(False, f"{quoi} : devrait être refusé")
    except profiles.ProfileError:
        ok(True, quoi)


res = lib.import_zip(zip_de({"profil.json": json.dumps(META), "style.css": "body{color:#fff}"}))
ok(res.get("id") == "profil-essai" and (lib.root / "profil-essai" / "style.css").is_file(), f"profil valide importé : {res.get('id')}")
res = lib.import_zip(zip_de({"dossier/profil.json": json.dumps({**META, "nom": "Dans Dossier"}), "dossier/style.css": "a{}"}))
ok(res.get("id") == "dans-dossier", "profil dans un unique dossier du zip")
refuse(zip_de({"../evil/profil.json": json.dumps(META), "style.css": ""}), "chemin avec « .. » refusé")
refuse(zip_de({"C:/evil.txt": "x", "profil.json": json.dumps(META), "style.css": ""}), "chemin absolu refusé")
refuse(zip_de({f"assets/f{i}.png": b"x" for i in range(profiles.MAX_FILES + 1)} | {"profil.json": json.dumps(META)}), "trop de fichiers refusé")
refuse(b"ceci n'est pas un zip", "fichier qui n'est pas un zip refusé")
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:  # « bombe » : 6 Mo de zéros, quelques Ko compressés
    z.writestr("profil.json", json.dumps({**META, "nom": "Bombe"}))
    z.writestr("assets/gros.png", b"\0" * (profiles.MAX_TOTAL + 1024 * 1024))
refuse(buf.getvalue(), "archive trop lourde une fois décompressée refusée")
css, pb = profiles.analyze_css("@import url(http://x/y.css); a{background:url(https://evil/x.png)} b{x:expression(alert(1))}", set())
ok("@import" not in css and "evil" not in css and "expression" not in css and len(pb) >= 3, f"CSS nettoyé ({len(pb)} problèmes signalés)")
css, pb = profiles.analyze_css('a{background:url("assets/fond.png")}', {"assets/fond.png"})
ok(not pb and "assets/fond.png" in css, "url() vers un fichier du profil acceptée")
css, pb = profiles.analyze_css('a{background:url("assets/../../secret.png")}', {"assets/fond.png"})
ok(pb and "secret" not in css, "url() qui sort du profil refusée")

# =========================================================================== statistiques personnelles
print("--- statistiques")
import statistiques

statistiques.clear_all()
tr = statistiques.Tracker(gpu_load=lambda: 50.0)
jour = dt.date.today()
t0 = dt.datetime.combine(jour, dt.time(10, 0)).timestamp()
jeu = {"actif": True, "applis": [{"nom": "Mon Jeu", "categorie": "jeu"}]}
tr.tick(now=t0, sample=jeu)  # 1re mesure : compte un intervalle (10 s)
tr.tick(now=t0 + 10, sample=jeu)
tr.tick(now=t0 + 20, sample={"actif": False, "applis": []})
tr.tick(now=t0 + 10_000, sample=jeu)  # trou de 2 h : l'intervalle compté est plafonné
rep = statistiques.report("jour", jour)
ok(rep["actif_s"] == 10 + 10 + 30, f"temps actif : 10 + 10 + (trou plafonné à 30) = {rep['actif_s']}")
ok(rep["inactif_s"] == 10, f"temps inactif : {rep['inactif_s']}")
ok(rep["jeux"] and rep["jeux"][0]["nom"] == "Mon Jeu" and rep["jeux"][0]["secondes"] == 50, f"temps de jeu : {rep['jeux']}")
ok(len(rep["sessions"]) == 2, f"absence de plus de 15 min : nouvelle session ({len(rep['sessions'])})")
ok(rep["heures"][10]["gpu_moy"] == 50.0 and len(rep["heures"]) == 24, "moyenne GPU par heure")
db.set_setting("stats_pause", True)
tr.tick(now=t0 + 10_010, sample=jeu)
ok(statistiques.report("jour", jour)["actif_s"] == 50, "en pause : rien n'est compté")
db.set_setting("stats_pause", False)
r7 = statistiques.report("7j", jour)
ok(len(r7["jours"]) == 7 and r7["jours"][-1]["jour"] == jour.isoformat() and r7["actif_s"] == 50, "rapport 7 jours")
statistiques.clear_all()
ok(statistiques.report("jour", jour)["actif_s"] == 0, "effacement de toutes les statistiques")

print(f"{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
