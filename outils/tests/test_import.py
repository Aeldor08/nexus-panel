"""Reprise des données d'un autre NEXUS du PC (importer.py, « NEXUS.exe --importer ») : reconnaissance des
dossiers NEXUS, recherche, copie cohérente de la base (WAL compris), remplacement avec sauvegarde, original jamais
modifié, remise en place si la copie échoue, détection et fermeture des NEXUS ouverts, option de la ligne de
commande. Tout se passe dans un dossier temporaire : ni le projet ni le vrai %LOCALAPPDATA% ne sont touchés."""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(sys.argv[1])
sys.path.insert(0, str(BASE))
TMP = Path(tempfile.mkdtemp(prefix="nexus-import-test-")).resolve()  # nom long (TEMP en 8.3 sur la CI)
DEST = TMP / "LocalAppData" / "NEXUS"
os.environ["NEXUS_DATA_DIR"] = str(DEST)
os.environ.pop("NEXUS_PORTABLE", None)

import importer
import paths

# (mode source : le dossier d'installation serait le projet, où tournent les tests eux-mêmes)
paths.INSTALL_DIR = TMP / "Programs" / "NEXUS"

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  [ECHEC]", m)


def empreinte(dossier: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(dossier.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(dossier)).encode() + p.read_bytes())
    return h.hexdigest()


def base_wal(dossier: Path, journal: list[str], sessions: int) -> sqlite3.Connection:
    """Base au format de NEXUS dont les dernières écritures sont encore dans le WAL (connexion laissée ouverte,
    comme un NEXUS qui tourne) : nexus.db et nexus.db-wal sont copiés dans `dossier`."""
    travail = Path(tempfile.mkdtemp(dir=TMP))
    con = sqlite3.connect(travail / "nexus.db")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA wal_autocheckpoint=0")
    con.execute("CREATE TABLE journal (id INTEGER PRIMARY KEY, texte TEXT)")
    con.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY, debut REAL, fin REAL)")
    con.execute("CREATE TABLE photos (id INTEGER PRIMARY KEY)")
    con.commit()
    con.executemany("INSERT INTO journal (texte) VALUES (?)", [(t,) for t in journal])
    con.executemany("INSERT INTO sessions (debut, fin) VALUES (?, ?)", [(i, i + 1) for i in range(sessions)])
    con.commit()
    (dossier / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy2(travail / "nexus.db", dossier / "data" / "nexus.db")
    shutil.copy2(travail / "nexus.db-wal", dossier / "data" / "nexus.db-wal")
    return con


def lire_journal(db: Path) -> list[str]:
    con = sqlite3.connect(db)
    try:
        return [r[0] for r in con.execute("SELECT texte FROM journal ORDER BY id")]
    finally:
        con.close()


ouvertes = []
try:
    # --- 1. Reconnaître un NEXUS
    disque = TMP / "Disque"
    portable = disque / "Jeux" / "NEXUS-Portable-1.7.0"
    portable.mkdir(parents=True)
    (portable / "NEXUS.exe").write_bytes(b"MZ")
    (portable / "portable.flag").write_text("", encoding="utf-8")
    (portable / "config.json").write_text(json.dumps({"deck": {"password_hash": "ancien$hash"}, "journal": {"x": 1}}), encoding="utf-8")
    (portable / "deck.json").write_text('{"boutons": ["ancien"]}', encoding="utf-8")
    ouvertes.append(base_wal(portable, ["lundi", "mardi", "mercredi"], 5))
    (portable / "data" / "philibert.json").write_text('{"stade": "adulte"}', encoding="utf-8")
    (portable / "data" / "agenda.json").write_text('{"evenements": ["anniversaire"]}', encoding="utf-8")
    (portable / "data" / "souvenirs").mkdir()
    (portable / "data" / "souvenirs" / "photo.jpg").write_bytes(b"\xff\xd8photo")
    (portable / "data" / "webview").mkdir()
    (portable / "data" / "webview" / "cache.bin").write_bytes(b"cache")
    (portable / "profils" / "mon-profil").mkdir(parents=True)
    (portable / "profils" / "mon-profil" / "profil.json").write_text('{"nom": "perso"}', encoding="utf-8")
    (portable / "profils" / "sakura").mkdir(parents=True)
    (portable / "profils" / "sakura" / "profil.json").write_text('{"version": "ancienne"}', encoding="utf-8")
    (portable / "actions").mkdir()
    (portable / "actions" / "macro.bat").write_text("@echo off", encoding="utf-8")
    (portable / "_internal").mkdir()
    (portable / "_ancienne-version" / "data").mkdir(parents=True)  # sauvegarde interne : pas un 2e NEXUS
    (portable / "_ancienne-version" / "config.json").write_text("{}", encoding="utf-8")
    (portable / "_ancienne-version" / "NEXUS.exe").write_bytes(b"MZ")

    source_zip = disque / "Users" / "amie" / "Downloads" / "NEXUS-1.8.0"
    source_zip.mkdir(parents=True)
    for f in ("app.py", "nexus.pyw", "lancer.bat"):
        (source_zip / f).write_text("# code", encoding="utf-8")
    (source_zip / "VERSION").write_text("1.8.0\n", encoding="utf-8")
    (source_zip / "config.json").write_text("{}", encoding="utf-8")

    installe = disque / "Programmes" / "NEXUS"  # application installée : exe sans données à côté
    installe.mkdir(parents=True)
    (installe / "NEXUS.exe").write_bytes(b"MZ")
    cache = disque / "AppData" / "NEXUS-copie"  # AppData n'est jamais parcouru
    cache.mkdir(parents=True)
    (cache / "app.py").write_text("", encoding="utf-8")
    (cache / "nexus.pyw").write_text("", encoding="utf-8")
    (cache / "config.json").write_text("{}", encoding="utf-8")

    ok(importer.genre(portable) == "portable", "portable reconnu")
    ok(importer.genre(source_zip) == "source", "version ZIP (source) reconnue")
    ok(importer.genre(installe) is None, "dossier d'une application installée sans données : ignoré")
    ok(importer.genre(TMP / "rien") is None and importer.genre(disque) is None, "dossier quelconque : ignoré")
    vieil_exe = TMP / "vieil-exe"
    (vieil_exe / "data").mkdir(parents=True)
    (vieil_exe / "NEXUS.exe").write_bytes(b"MZ")
    (vieil_exe / "data" / "nexus.db").write_bytes(b"")
    ok(importer.genre(vieil_exe) == "exe", "ancien exe avec ses données à côté reconnu")
    # data/ et actions/ déplacés seuls dans un dossier (sans config.json ni programme)
    deplaces = TMP / "Bureau" / "Sauvegarde NEXUS"
    ouvertes.append(base_wal(deplaces, ["note gardée"], 2))
    (deplaces / "data" / "philibert.json").write_text('{"stade": "ado"}', encoding="utf-8")
    (deplaces / "actions").mkdir()
    (deplaces / "actions" / "ma-macro.bat").write_text("@echo off", encoding="utf-8")
    ok(importer.genre(deplaces) == "dossiers", "data et actions déplacés seuls : reconnus")
    ok(importer.dossier_source(deplaces / "data") == deplaces, "dossier data choisi lui-même : son dossier parent")
    ok(importer.dossier_source(deplaces / "actions") == deplaces, "dossier actions choisi lui-même : son dossier parent")
    ok(importer.dossier_source(portable) == portable, "dossier NEXUS choisi : inchangé")
    seul_philibert = TMP / "vieux-data"
    (seul_philibert / "data").mkdir(parents=True)
    (seul_philibert / "data" / "philibert.json").write_text("{}", encoding="utf-8")
    ok(importer.genre(seul_philibert) == "dossiers", "data sans base mais avec Philibert : reconnu")
    (TMP / "autre" / "data").mkdir(parents=True)
    (TMP / "autre" / "data" / "photo.jpg").write_bytes(b"x")
    ok(importer.genre(TMP / "autre") is None, "dossier data quelconque : ignoré")
    d = importer.decrire(deplaces)
    ok("actions (1)" in d["contenu"] and any("sans configuration" in x for x in d["contenu"]), f"description : actions, sans configuration ({d['contenu']})")

    # --- 2. Recherche
    DEST.mkdir(parents=True)
    (DEST / "config.json").write_text(json.dumps({"deck": {"password_hash": "neuf$hash"}}), encoding="utf-8")
    os.utime(source_zip / "config.json", (time.time() - 86400 * 30,) * 2)  # utilisé il y a un mois
    trouves = importer.chercher([disque, DEST.parent])
    chemins = [Path(c["chemin"]) for c in trouves]
    ok(chemins == [portable, source_zip], f"recherche : portable puis version ZIP, le plus récent d'abord ({chemins})")
    ok(not any(importer._meme(c, DEST) for c in chemins), "ce NEXUS-ci n'est jamais proposé")
    d = trouves[0]
    ok(d["libelle"] == "NEXUS portable" and "journal (3 entrées)" in d["contenu"], f"description : journal lu dans le WAL ({d['contenu']})")
    ok(
        "statistiques (5 sessions)" in d["contenu"] and "Philibert" in d["contenu"] and "souvenirs (1 photos)" in d["contenu"],
        "description : stats, Philibert, souvenirs",
    )
    ok(trouves[1]["version"] == "1.8.0", "version lue dans VERSION")
    ok([Path(c["chemin"]) for c in importer.chercher([TMP / "Bureau"])] == [deplaces], "recherche : data et actions déplacés seuls trouvés")
    # application installée : data/ posé à la main à côté de NEXUS.exe (elle lit %LOCALAPPDATA%\NEXUS) → proposé
    (paths.INSTALL_DIR / "data").mkdir(parents=True)
    (paths.INSTALL_DIR / "NEXUS.exe").write_bytes(b"MZ")
    (paths.INSTALL_DIR / "data" / "philibert.json").write_text("{}", encoding="utf-8")
    ok(importer.chercher([paths.INSTALL_DIR.parent]) == [], "version source : son propre dossier jamais proposé")
    paths.FROZEN = True
    try:
        ok(
            [Path(c["chemin"]) for c in importer.chercher([paths.INSTALL_DIR.parent])] == [paths.INSTALL_DIR],
            "appli installée : data posé à côté de l'exe proposé",
        )
    finally:
        paths.FROZEN = False
    shutil.rmtree(paths.INSTALL_DIR)

    # --- 3. Import dans un NEXUS déjà utilisé
    (DEST / "data").mkdir()
    con = sqlite3.connect(DEST / "data" / "nexus.db")
    con.execute("CREATE TABLE journal (id INTEGER PRIMARY KEY, texte TEXT)")
    con.execute("INSERT INTO journal (texte) VALUES ('note de l''appli neuve')")
    con.commit()
    con.close()
    (DEST / "data" / "nexus.db-wal").write_bytes(b"WAL perime")  # un vieux WAL ne doit jamais rester
    (DEST / "data" / "devices.json").write_text('{"seul": "ici"}', encoding="utf-8")
    (DEST / "data" / "philibert.json").write_text('{"stade": "oeuf"}', encoding="utf-8")
    (DEST / "profils" / "sakura").mkdir(parents=True)
    (DEST / "profils" / "sakura" / "profil.json").write_text('{"version": "fournie, plus récente"}', encoding="utf-8")
    avant = empreinte(portable)

    r = importer.importer(portable, verifier_ouverts=False)
    ok(empreinte(portable) == avant, "l'autre NEXUS n'est pas modifié")
    ok(json.loads((DEST / "config.json").read_text(encoding="utf-8"))["deck"]["password_hash"] == "ancien$hash", "configuration reprise (mot de passe du Deck)")
    ok(lire_journal(DEST / "data" / "nexus.db") == ["lundi", "mardi", "mercredi"], "base reprise avec les écritures du WAL")
    ok(not (DEST / "data" / "nexus.db-wal").exists(), "ancien WAL de ce NEXUS supprimé")
    ok(json.loads((DEST / "data" / "philibert.json").read_text(encoding="utf-8"))["stade"] == "adulte", "Philibert repris")
    ok((DEST / "data" / "agenda.json").is_file() and (DEST / "data" / "souvenirs" / "photo.jpg").is_file(), "agenda et souvenirs repris")
    ok(not (DEST / "data" / "webview").exists(), "cache WebView2 non copié")
    ok((DEST / "data" / "devices.json").is_file(), "fichier présent seulement ici : gardé")
    ok((DEST / "profils" / "mon-profil" / "profil.json").is_file(), "profil ajouté repris")
    ok("plus récente" in (DEST / "profils" / "sakura" / "profil.json").read_text(encoding="utf-8"), "profil fourni de ce NEXUS gardé")
    ok((DEST / "actions" / "macro.bat").is_file() and (DEST / "deck.json").is_file(), "actions et Deck repris")
    ok((DEST / ".layout-v2").is_file(), "marqueur posé (pas de reprise automatique ensuite)")
    sauvegarde = Path(r["sauvegarde"])
    ok(sauvegarde.parent == DEST / importer.SAUVEGARDES, "sauvegarde dans sauvegardes-import")
    ok(json.loads((sauvegarde / "config.json").read_text(encoding="utf-8"))["deck"]["password_hash"] == "neuf$hash", "sauvegarde : ancienne configuration")
    ok(lire_journal(sauvegarde / "data" / "nexus.db") == ["note de l'appli neuve"], "sauvegarde : ancienne base")
    ok(json.loads((sauvegarde / "IMPORT.txt").read_text(encoding="utf-8"))["source"] == str(portable), "IMPORT.txt décrit l'import")
    ok(importer.chercher([DEST.parent]) == [], "les sauvegardes d'import ne sont pas proposées")

    # --- 4. Refus
    for dossier, attendu in ((TMP / "rien", "pas un dossier NEXUS"), (DEST, "ce NEXUS-ci")):
        try:
            importer.importer(dossier, verifier_ouverts=False)
            ok(False, f"refus attendu : {attendu}")
        except importer.ImportImpossible:
            ok(True, "")

    # --- 5. Copie interrompue : tout est remis comme avant
    avant_dest = {p: p.read_bytes() for p in (DEST / "config.json", DEST / "data" / "philibert.json")}
    shutil.rmtree(DEST / "data" / "souvenirs")
    vrai_remplacer = importer._remplacer

    def remplacer_en_panne(src, dst):
        if src.name == "souvenirs":
            (dst / "a-moitie.jpg").parent.mkdir(parents=True, exist_ok=True)
            (dst / "a-moitie.jpg").write_bytes(b"x")
            raise OSError("disque plein")
        vrai_remplacer(src, dst)

    importer._remplacer = remplacer_en_panne
    (portable / "config.json").write_text(json.dumps({"deck": {"password_hash": "autre$hash"}}), encoding="utf-8")
    try:
        importer.importer(portable, verifier_ouverts=False)
        ok(False, "échec attendu")
    except importer.ImportImpossible as exc:
        ok("rien n'a changé" in str(exc), f"message clair ({exc})")
    finally:
        importer._remplacer = vrai_remplacer
    ok(all(p.read_bytes() == b for p, b in avant_dest.items()), "copie interrompue : configuration et Philibert remis")
    ok(not (DEST / "data" / "souvenirs").exists(), "copie interrompue : dossier à moitié copié retiré")
    ok(lire_journal(DEST / "data" / "nexus.db") == ["lundi", "mardi", "mercredi"], "copie interrompue : base remise")

    # --- 5 bis. Import de data et actions déplacés seuls (dossier data choisi lui-même) : configuration gardée
    (DEST / "config.json").write_text(json.dumps({"deck": {"password_hash": "neuf$hash"}}), encoding="utf-8")
    r = importer.importer(deplaces / "data", verifier_ouverts=False)
    ok(lire_journal(DEST / "data" / "nexus.db") == ["note gardée"], "dossiers déplacés : base reprise")
    ok(json.loads((DEST / "data" / "philibert.json").read_text(encoding="utf-8"))["stade"] == "ado", "dossiers déplacés : Philibert repris")
    ok((DEST / "actions" / "ma-macro.bat").is_file(), "dossiers déplacés : actions reprises")
    ok(
        json.loads((DEST / "config.json").read_text(encoding="utf-8"))["deck"]["password_hash"] == "neuf$hash",
        "dossiers déplacés : mot de passe de ce NEXUS gardé",
    )
    ok(json.loads((Path(r["sauvegarde"]) / "IMPORT.txt").read_text(encoding="utf-8"))["source"] == str(deplaces), "IMPORT.txt : le dossier qui contient data")

    # --- 6. NEXUS ouvert : détecté (version source lancée depuis son dossier), puis fermé
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], cwd=str(source_zip))
    try:
        time.sleep(0.5)
        trouves = importer.ouverts_pour(source_zip, DEST)
        ok(any(x["pid"] == p.pid for x in trouves), f"NEXUS ouvert détecté ({trouves})")
        try:
            importer.importer(source_zip)
            ok(False, "import refusé tant que NEXUS est ouvert")
        except importer.ImportImpossible as exc:
            ok("Ferme" in str(exc), "import refusé tant que NEXUS est ouvert")
        ok(importer.fermer([p.pid]) == [] and p.wait(10) is not None, "NEXUS fermé")
    finally:
        if p.poll() is None:
            p.kill()
    (DEST / "runtime.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    ok(importer.ouverts_pour(source_zip, DEST) == [], "ce processus-ci (la fenêtre d'import) n'est jamais compté")

    # --- 7. Ligne de commande
    import nexus_launcher

    ok(nexus_launcher._parser().parse_args(["--importer"]).importer == "*", "--importer seul : fenêtre d'import")
    ok(nexus_launcher._parser().parse_args(["--importer", "C:\\X"]).importer == "C:\\X", "--importer DOSSIER : inchangé")
    ok(nexus_launcher._parser().parse_args([]).importer == "", "sans option : rien")
    ok(paths.USER_ROOT == DEST, "tests isolés du vrai dossier de données")
finally:
    for con in ouvertes:
        try:
            con.close()
        except Exception:
            pass
    shutil.rmtree(TMP, ignore_errors=True)

print(f"{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
