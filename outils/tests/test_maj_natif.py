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

    # PowerShell 7 (pwsh) lègue un PSModulePath que Windows PowerShell 5.1 ne sait pas charger
    psmodulepath = os.environ.get("PSModulePath")
    os.environ["PSModulePath"] = r"C:\Program Files\PowerShell\7\Modules"
    env_ps = maj_natif._env_powershell()
    ok(not any(k.upper() == "PSMODULEPATH" for k in env_ps), "PSModulePath hérité retiré pour Windows PowerShell")
    ok(env_ps.get("PATH") or env_ps.get("Path"), "le reste de l'environnement est conservé")
    if psmodulepath is None:
        os.environ.pop("PSModulePath", None)
    else:
        os.environ["PSModulePath"] = psmodulepath

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
            print(f"      (notepad.exe : {systeme['statut']}" + (f", {systeme['message']}" if systeme["statut"] != "valide" else "") + ")")
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
    ok(script.read_bytes().startswith(b"\xef\xbb\xbf"),
       "helper en UTF-8 avec BOM (PowerShell 5.1 : accents justes dans les messages)")
    ok("config.json" in job["proteger"] and "data" in job["proteger"] and "maj" in job["proteger"],
       "travail : données protégées transmises au helper")

    # --- version portable --------------------------------------------------
    import zipfile
    passets = [{"id": 7, "name": "NEXUS-Portable-1.9.0.zip"}, {"id": 8, "name": "NEXUS-Portable-1.9.0.zip.sha256"},
               {"id": 9, "name": "NEXUS-Portable-1.8.0.zip"}]
    pchoix = maj_natif.choisir_assets_portable(passets, "1.9.0")
    ok(pchoix["portable"]["id"] == 7 and pchoix["sha256_portable"]["id"] == 8, "portable : archive de la bonne version choisie")
    ok(maj_natif.choisir_assets_portable(passets, "2.0.0")["portable"] is None, "portable : autre version → rien")

    def zip_portable(nom, fichiers):
        z = root / nom
        with zipfile.ZipFile(z, "w") as f:
            for n, contenu in fichiers.items():
                f.writestr(n, contenu)
        return z

    bon = zip_portable("bon.zip", {"NEXUS-Portable-1.9.0/NEXUS.exe": "exe", "NEXUS-Portable-1.9.0/portable.flag": "p",
                                   "NEXUS-Portable-1.9.0/_internal/VERSION": "1.9.0\n",
                                   "NEXUS-Portable-1.9.0/_internal/app.py": "x"})
    nouveau = maj_natif.extraire_portable(bon, root / "extrait", "1.9.0")
    ok((nouveau / "NEXUS.exe").is_file() and (nouveau / "_internal" / "app.py").is_file(), "portable : archive extraite")

    def refuse(nom, fichiers, ver="1.9.0"):
        try:
            maj_natif.extraire_portable(zip_portable(nom, fichiers), root / ("x-" + nom), ver)
            return False
        except maj_natif.NatifError:
            return True

    base_ok = {"N/NEXUS.exe": "e", "N/_internal/VERSION": "1.9.0"}
    ok(refuse("v.zip", base_ok, "2.0.0"), "portable : version annoncée différente → refusée")
    ok(refuse("d.zip", {**base_ok, "N/config.json": "{}"}), "portable : config.json dans l'archive → refusée")
    ok(refuse("dd.zip", {**base_ok, "N/data/x.db": "x"}), "portable : data\\ dans l'archive → refusée")
    ok(refuse("p.zip", {**base_ok, "N/../evil.txt": "x"}), "portable : chemin avec .. → refusé")
    ok(refuse("r.zip", {**base_ok, "Autre/x.txt": "x"}), "portable : deux dossiers racine → refusé")
    ok(refuse("e.zip", {"N/_internal/VERSION": "1.9.0"}), "portable : NEXUS.exe absent → refusé")

    # sauvegarde du portable : programme copié, données jamais
    port = root / "portable"
    (port / "_internal").mkdir(parents=True)
    (port / "NEXUS.exe").write_bytes(b"exe")
    (port / "portable.flag").write_text("p", encoding="utf-8")
    (port / "_internal" / "app.py").write_text("x", encoding="utf-8")
    (port / "_internal" / "profils" / "pure").mkdir(parents=True)
    (port / "_internal" / "profils" / "pure" / "profil.json").write_text("{}", encoding="utf-8")
    for d in ("data", "profils", "maj", "LibreHardwareMonitor", "_mes-affaires"):
        (port / d).mkdir()
    (port / "config.json").write_text("{}", encoding="utf-8")
    paths.INSTALL_DIR = port
    paths.USER_ROOT = port
    ok(maj_natif.est_portable(), "portable détecté (données à côté de l'exe)")
    ok(maj_natif.dossier_inscriptible(port), "dossier du portable modifiable")
    sp = maj_natif.sauvegarder_installation()
    ok((sp / "NEXUS.exe").is_file() and (sp / "portable.flag").is_file() and (sp / "_internal" / "app.py").is_file(),
       "portable : NEXUS.exe, portable.flag et _internal sauvegardés")
    ok(not any((sp / n).exists() for n in ("config.json", "data", "profils", "maj")), "portable : données jamais sauvegardées")
    ok((sp / "_internal" / "profils" / "pure" / "profil.json").is_file(), "portable : profils fournis de _internal sauvegardés")
    ok(not (sp / "LibreHardwareMonitor").exists() and not (sp / "_mes-affaires").exists(),
       "portable : LibreHardwareMonitor et dossiers perso ni sauvegardés ni gérés")
    jp = maj_natif.construire_job_portable({"version": "1.9.0"}, nouveau, sp)
    ok(jp["action"] == "portable" and jp["source_dir"] == str(nouveau) and "config.json" in jp["proteger"],
       "travail portable cohérent")
    ok(set(jp["elements"]) == {"NEXUS.exe", "_internal", "Lancer NEXUS.bat", "LISEZMOI.txt", "portable.flag"}
       and "LibreHardwareMonitor" not in jp["elements"], "portable : le helper ne gère que les fichiers du programme")
    ok(set(maj_natif.construire_job_retour(sp, "1.8.0")["elements"]) == set(jp["elements"]),
       "portable : le retour en arrière ne gère aussi que les fichiers du programme")
    maj_natif._ecrire(maj_natif.JOB_FILE, {**jp, "expected_version": version_mod.current()})
    ok(maj_natif.marquer_demarrage_ok(), "le démarrage de la nouvelle version portable est confirmé au helper")
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
