"""Migration vers la version installée : reprise des données d'une ancienne version source (dossier avec
lancer.bat), par « NEXUS.exe --importer <dossier> » ou automatiquement au premier lancement (raccourci du
Bureau). Copie seulement : l'ancien dossier n'est jamais modifié (il reste une sauvegarde complète).
Simule le mode gelé (exe) avec des dossiers temporaires ; ne touche ni au projet ni au vrai %LOCALAPPDATA%."""

import hashlib
import importlib
import os
import sys
import tempfile
from pathlib import Path

BASE = Path(sys.argv[1])
sys.path.insert(0, str(BASE))
TMP = Path(tempfile.mkdtemp(prefix="nexus-migration-"))

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


# --- une ancienne version source avec de vraies données de test
ancien = TMP / "NEXUS-source"
(ancien / "data" / "souvenirs").mkdir(parents=True)
(ancien / "profils" / "mon-profil").mkdir(parents=True)
(ancien / "actions").mkdir()
(ancien / "versions" / "NEXUS-1.0.0").mkdir(parents=True)
(ancien / "app.py").write_text("# code", encoding="utf-8")
(ancien / "nexus.pyw").write_text("# code", encoding="utf-8")
(ancien / "config.json").write_text('{"deck": {"password_hash": "pbkdf2_sha256$x"}}', encoding="utf-8")
(ancien / "jeux.json").write_text('{"processus": {}}', encoding="utf-8")
(ancien / "data" / "nexus.db").write_bytes(b"SQLite format 3\0" + b"x" * 100)
(ancien / "data" / "philibert.json").write_text('{"nom": "Philibert"}', encoding="utf-8")
(ancien / "data" / "souvenirs" / "photo.jpg").write_bytes(b"\xff\xd8photo")
(ancien / "profils" / "mon-profil" / "profil.json").write_text("{}", encoding="utf-8")
(ancien / "actions" / "ma-macro.bat").write_text("@echo off", encoding="utf-8")
avant = empreinte(ancien)


def charger_paths(donnees: Path):
    os.environ["NEXUS_DATA_DIR"] = str(donnees)
    os.environ["NEXUS_APP_DIR"] = str(BASE)
    sys.frozen = True  # version exe simulée
    import paths

    return importlib.reload(paths)


try:
    # 1. import demandé : NEXUS.exe --importer <dossier>
    donnees = TMP / "LocalAppData-NEXUS"
    os.environ["NEXUS_IMPORTER"] = str(ancien)
    paths = charger_paths(donnees)
    paths.prepare()
    ok((donnees / "config.json").read_text(encoding="utf-8").startswith('{"deck"'), "config.json repris")
    ok((donnees / "data" / "nexus.db").read_bytes().startswith(b"SQLite format 3"), "base de données reprise")
    ok((donnees / "data" / "souvenirs" / "photo.jpg").read_bytes() == b"\xff\xd8photo", "photos des souvenirs reprises")
    ok((donnees / "data" / "philibert.json").is_file(), "Philibert repris")
    ok((donnees / "profils" / "mon-profil" / "profil.json").is_file(), "profil personnel repris")
    ok((donnees / "actions" / "ma-macro.bat").is_file(), "actions du deck reprises")
    ok(not (donnees / "versions" / "NEXUS-1.0.0").exists(), "copies du code de la version source non reprises")
    ok((donnees / ".layout-v2").read_text(encoding="utf-8").startswith("Migration depuis " + str(ancien)), "marque de migration écrite")
    ok(empreinte(ancien) == avant, "ancien dossier intact (sauvegarde complète)")

    # 2. pas d'écrasement : une 2e importation ne remplace rien
    (donnees / "data" / "philibert.json").write_text('{"nom": "Modifié"}', encoding="utf-8")
    paths.prepare()
    ok((donnees / "data" / "philibert.json").read_text(encoding="utf-8") == '{"nom": "Modifié"}', "jamais d'écrasement des données déjà présentes")

    # 3. dossier qui n'est pas une version source : refusé, rien de copié
    os.environ["NEXUS_IMPORTER"] = str(TMP / "pas-nexus")
    (TMP / "pas-nexus").mkdir()
    donnees3 = TMP / "LocalAppData-3"
    paths = charger_paths(donnees3)
    paths.prepare()
    ok(not (donnees3 / "config.json").exists(), "dossier qui n'est pas NEXUS : rien n'est copié")
    del os.environ["NEXUS_IMPORTER"]

    # 4. premier lancement : ancienne version trouvée par le raccourci du Bureau
    donnees4 = TMP / "LocalAppData-4"
    paths = charger_paths(donnees4)
    paths._raccourci_bureau = lambda: ancien
    paths.prepare()
    ok((donnees4 / "data" / "nexus.db").is_file(), "premier lancement : ancienne version trouvée et reprise")

    # 5. lancements suivants : plus de détection (les données de l'utilisateur ne sont jamais complétées en douce)
    donnees5 = TMP / "LocalAppData-5"
    paths = charger_paths(donnees5)
    (donnees5).mkdir(parents=True, exist_ok=True)
    (donnees5 / "config.json").write_text("{}", encoding="utf-8")
    paths._raccourci_bureau = lambda: ancien
    paths.prepare()
    ok(not (donnees5 / "data" / "nexus.db").exists(), "pas un premier lancement : aucune reprise automatique")

    # 6. portable (données à côté de l'exe) : jamais de reprise automatique
    ok(paths.est_version_source(ancien) and not paths.est_version_source(TMP / "pas-nexus"), "détection d'un dossier de version source")
finally:
    try:
        del sys.frozen
    except AttributeError:
        pass

print(f"{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
