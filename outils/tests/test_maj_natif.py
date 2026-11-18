"""Tests du moteur de mise à jour native (installeur, SHA256, signature, sauvegarde).

Aucun installeur n'est lancé : on teste les fonctions pures et la copie de
l'installation dans un dossier temporaire. Le helper PowerShell est seulement
vérifié syntaxiquement par le build, pas exécuté ici.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
root = Path(tempfile.mkdtemp(prefix="nexus-maj-natif-"))
os.environ["NEXUS_DATA_DIR"] = str(root)
os.environ["NEXUS_APP_DIR"] = str(BASE)
sys.path.insert(0, str(BASE))

passed = failed = 0


def ok(condition, message):
    global passed, failed
    print(("OK    " if condition else "[ECHEC] ") + message)
    passed += bool(condition)
    failed += not condition


try:
    import maj_natif
    import paths
    import version as version_mod

    # --- choix des fichiers de la release ---------------------------------
    assets = [
        {"id": 1, "name": "NEXUS-1.4.1-Setup.exe", "size": 37_000_000},
        {"id": 2, "name": "NEXUS-1.4.1-Setup.exe.sha256", "size": 80},
        {"id": 3, "name": "NEXUS-1.4.1.zip", "size": 7_000_000},
        {"id": 4, "name": "NEXUS-1.4.1.zip.sha256", "size": 80},
        {"id": 5, "name": "autre-chose.zip", "size": 10},
    ]
    choix = maj_natif.choisir_assets(assets)
    ok(choix["installateur"]["id"] == 1, "installeur Windows choisi")
    ok(choix["sha256_installateur"]["id"] == 2, "SHA256 de l'installeur choisi")
    ok(choix["archive"]["id"] == 3 and choix["sha256"]["id"] == 4, "archive source toujours reconnue")
    ok(maj_natif.choisir_assets([])["installateur"] is None, "release sans installeur : aucun choix fabriqué")

    # --- SHA256 -----------------------------------------------------------
    fichier = root / "exemple.bin"
    fichier.write_bytes(b"NEXUS" * 1000)
    attendu = maj_natif.sha256_fichier(fichier)
    ok(len(attendu) == 64 and attendu == attendu.lower(), "SHA256 d'un fichier")
    ok(maj_natif.SHA256_RE.match(attendu) is not None, "format SHA256 accepté")
    ok(maj_natif.SHA256_RE.match("pas-un-hash") is None, "faux SHA256 refusé")

    # --- politique de signature ------------------------------------------
    non_signe = {"statut": "non_signe", "signataire": "", "empreinte": "", "message": "NotSigned"}
    valide = {"statut": "valide", "signataire": "CN=NEXUS", "empreinte": "AA BB CC", "message": "ok"}
    ok(maj_natif.evaluer_signature(non_signe, "auto", "")["ok"], "non signé accepté en mode auto (SHA256 seul)")
    ok(not maj_natif.evaluer_signature(non_signe, "requise", "")["ok"], "non signé refusé si signature requise")
    ok(maj_natif.evaluer_signature(non_signe, "ignoree", "")["ok"], "mode ignoré accepté")
    ok(maj_natif.evaluer_signature(valide, "requise", "")["ok"], "signature valide acceptée")
    ok(maj_natif.evaluer_signature(valide, "requise", "AABBCC")["ok"], "empreinte du signataire acceptée")
    ok(not maj_natif.evaluer_signature(valide, "requise", "DEADBEEF")["ok"], "signataire inattendu refusé")
    ok(not maj_natif.evaluer_signature({"statut": "invalide", "message": "HashMismatch"}, "auto", "")["ok"],
       "signature invalide refusée")

    if os.name == "nt":
        # Get-AuthenticodeSignature ne lit que les exécutables PE : on teste sur
        # l'exe du projet s'il a déjà été construit, sinon le cas « non signé »
        # reste couvert par evaluer_signature ci-dessus.
        exe_projet = BASE / "dist" / "NEXUS" / "NEXUS.exe"
        if exe_projet.is_file():
            signature = maj_natif.verifier_signature(exe_projet)
            ok(signature["statut"] in ("non_signe", "valide"),
               f"signature de l'exe local lue : {signature['statut']}")
        else:
            print("      (exe non construit : test « non signé » déjà couvert par evaluer_signature)")
        notepad = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "notepad.exe"
        if notepad.is_file():
            systeme = maj_natif.verifier_signature(notepad)
            print(f"      (notepad.exe : {systeme['statut']})")
            ok(systeme["statut"] == "valide", "fichier système signé reconnu par Get-AuthenticodeSignature")
    else:
        print("      (signature Authenticode ignorée : plateforme non Windows)")

    # --- sauvegarde de l'installation ------------------------------------
    source = root / "installation"
    (source / "_internal" / "profils" / "demo").mkdir(parents=True)
    (source / "NEXUS.exe").write_bytes(b"exe")
    (source / "unins000.exe").write_bytes(b"uninst")
    (source / "_internal" / "app.py").write_text("print('ok')", encoding="utf-8")
    (source / "_internal" / "profils" / "demo" / "style.css").write_text("body{}", encoding="utf-8")
    (source / "config.json").write_text("{}", encoding="utf-8")
    (source / "data").mkdir()
    (source / "data" / "secret.txt").write_text("personnel", encoding="utf-8")

    paths.FROZEN = True
    paths.INSTALL_DIR = source
    paths.USER_ROOT = root
    sauvegarde = maj_natif.sauvegarder_installation()
    ok((sauvegarde / "NEXUS.exe").is_file(), "sauvegarde : exe copié")
    ok((sauvegarde / "unins000.exe").is_file(), "sauvegarde : désinstalleur copié")
    ok((sauvegarde / "_internal" / "app.py").is_file(), "sauvegarde : _internal copié")
    ok((sauvegarde / "_internal" / "profils" / "demo" / "style.css").is_file(), "sauvegarde : profils fournis copiés")
    ok(not (sauvegarde / "config.json").exists(), "sauvegarde : config.json personnel exclu")
    ok(not (sauvegarde / "data").exists(), "sauvegarde : data/ personnel exclu")

    liste = maj_natif.sauvegardes_installation()
    ok(len(liste) == 1 and liste[0]["version"] == version_mod.current(), "sauvegarde listée avec sa version")

    # --- travail du helper ------------------------------------------------
    job = maj_natif.construire_job_installation({"version": "9.9.9"}, root / "NEXUS-9.9.9-Setup.exe", sauvegarde)
    ok(job["action"] == "install" and job["expected_version"] == "9.9.9", "travail d'installation cohérent")
    ok(job["parent_pid"] == os.getpid(), "PID du parent transmis au helper")
    ok(job["app_exe"].lower().endswith("python.exe"), "exe de relance renseigné")
    retour = maj_natif.construire_job_retour(sauvegarde, "1.4.1")
    ok(retour["action"] == "restore" and retour["expected_version"] == "1.4.1", "travail de retour cohérent")

    # --- helper présent dans les sources ---------------------------------
    script = BASE / "outils" / "appliquer_maj.ps1"
    ok(script.is_file() and "Start-Process" in script.read_text(encoding="utf-8"),
       "script helper présent et lisible")

    os.environ["NEXUS_MAJ_HELPER_DRY"] = "1"
    lancement = maj_natif.lancer_helper(job)
    copie = Path(lancement["commande"][-3])
    ok(copie.name.startswith("appliquer_maj-") and copie.parent == paths.MAJ_DIR,
       "helper copié hors du dossier d'installation")
    ok(maj_natif.JOB_FILE.is_file(), "travail JSON écrit pour le helper")
    os.environ.pop("NEXUS_MAJ_HELPER_DRY", None)
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
