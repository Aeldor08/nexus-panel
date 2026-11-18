# Personnalisation NEXUS — inventaire de référence

Version de référence : **NEXUS 1.6.0 personnalisé** (Phases 0 à 3 + portable).
Ce document sert à adapter une future version du dépôt d'origine sans perdre les
apports de la version native/portable.

Le fichier `docs/PATCH-PERSONNALISATION-1.6.0.patch` contient le diff complet
entre la 1.6.0 d'origine et cette version personnalisée. Il sert de **référence**
et peut être appliqué avec `git apply -p1 --ignore-whitespace` sur une copie de
la 1.6.0 d'origine.

La 1.6.0 d'origine apporte aussi le **Python privé** (`runtime\`,
`outils\installer_python.ps1`, `outils\python-prive.json`), le superviseur
d'arrière-plan (`nexus.pyw`, `superviseur.py`) et le profil « Averse de néons ».
Ce sont des fichiers **upstream à conserver** : ils ne font pas partie de la
personnalisation native/portable et ne doivent pas être supprimés lors d'une
fusion.

## Règle principale

Ne jamais copier tout le dossier personnalisé sur une nouvelle version : cela
écraserait les nouveautés de ton frère. Il faut :

1. copier les **nouveaux fichiers** de la personnalisation ;
2. **fusionner** les fichiers modifiés, en gardant les nouveautés upstream ;
3. lancer `outils/verifier_personnalisation.py` puis les tests.

## Nouveaux fichiers à copier

| Fichier | Rôle |
|---|---|
| `paths.py` | Sépare ressources en lecture seule et données inscriptibles (`%LOCALAPPDATA%\NEXUS` ou dossier portable). |
| `logs.py` | Journal fichier `logs\nexus.log` avec rotation. |
| `nexus_launcher.py` | Fenêtre native WebView2, tray, toasts, configuration, portable, instance unique. |
| `lancer_native.bat` | Lancement depuis les sources sans console. |
| `Creer-NEXUS-Portable.bat` | Double-clic : environnement de build, dépendances, ZIP portable. |
| `requirements-native.txt` | pywebview, pystray, winotify, PyInstaller. |
| `nexus.spec` | Build PyInstaller onedir, icône, version, données, helper PowerShell. |
| `installer.iss` | Installeur Inno Setup par utilisateur, WebView2, raccourcis, désinstallation. |
| `maj_natif.py` | Mise à jour de la version installée : SHA256, Authenticode, sauvegarde, helper, rollback. |
| `outils/build_native.py` | Build exe + installeur + archive portable + signatures + hashes. |
| `outils/sign_native.ps1` | Signature Authenticode (empreinte ou PFX). |
| `outils/appliquer_maj.ps1` | Helper caché qui ferme NEXUS, installe, relance et restaure en cas d'échec. |
| `outils/tests/test_paths.py` | Tests chemins/données/runtime. |
| `outils/tests/test_maj_natif.py` | Tests mise à jour native, signature, sauvegarde. |
| `outils/tests/test_portable.py` | Tests détection portable, mutex, archive ZIP. |
| `.github/workflows/ci.yml` | Lint + tests sur push/PR. |
| `.github/workflows/build-native.yml` | Build Windows sur tag `v*` (artefacts, sans publication). |
| `docs/GITHUB-FORK.md` | Procédure fork, clone, upstream, releases. |
| `docs/MODOP-PORTABLE.md` | Le présent mode opératoire. |
| `docs/PERSONNALISATION.md` | Cet inventaire. |
| `docs/PATCH-PERSONNALISATION-1.6.0.patch` | Diff de référence 1.6.0 d'origine → 1.6.0 personnalisée. |
| `outils/verifier_personnalisation.py` | Vérifie qu'une copie candidate contient les invariants. |

## Fichiers modifiés à fusionner

| Fichier | Ce qu'il faut conserver | Risque si écrasé |
|---|---|---|
| `app.py` | Imports `paths`/`maj_natif`, routes `/api/maj`, `start_services`/`stop_services`, notifier natif, boucle d'alertes, `RESTART_CODE`, `_single_instance_guard`, marqueur de démarrage. | Mise à jour native, tray, redémarrage et instance unique cassés. |
| `config.py`, `config.example.json` | `mises_a_jour.signature`, `mises_a_jour.certificat`, valeurs par défaut et migration. | Politique de signature perdue. |
| `maj.py` | Branche `paths.FROZEN` : assets installateur, `maj_natif`, SHA256, signature, sauvegarde, `revenir`. | Mise à jour native impossible ou non vérifiée. |
| `maj_demarrage.py` | Garde `paths.FROZEN`, sauvegarde/restauration source. | Mélange source/gelé. |
| `audio.py` | `comtypes.client.gen_dir` dans `%LOCALAPPDATA%\NEXUS`. | Audio cassé dans l'exe (dossier read-only). |
| `deck.py` | `paths.DECK_FILE`, `paths.DECK_EXAMPLE`, `paths.ACTIONS_DIR`, `paths.DATA_DIR`, exécution `.py` en gelé. | Deck et scripts cassés. |
| `profiles.py` | `PROFILES_DIR = paths.PROFILES_DIR`, `mkdir(parents=True)`. | Profils écrits dans le programme. |
| `store.py` | `DATA_DIR = paths.DATA_DIR`. | Données dans le dossier d'installation. |
| `stats.py` | `paths.FAN_NAMES_FILE`, `paths.LEGACY_DIR`, `paths.INSTALL_DIR` pour LHM. | Ventilateurs/LHM introuvables. |
| `statistiques.py` | `paths.JEUX_FILE`, `paths.JEUX_EXAMPLE`, `stop()`. | Stats et arrêt propre cassés. |
| `reminders.py` | `stop()` + `mkdir(parents=True)`. | Thread de rappels non arrêtable. |
| `bot.py` | `stop()` et boucle arrêtable. | Bot non arrêté proprement. |
| `configurer.py` | `paths.prepare()`, chemins de config, révocation des sessions deck. | Configuration au mauvais endroit. |
| `version.py` | Nouveaux globs (`*.spec`, `*.iss`, outils), garde `paths.FROZEN`. | Snapshots/restauration incohérents. |
| `lancer.bat` | Vérification des dépendances par empreinte, `NEXUS_SINGLE_INSTANCE=1`. | Réinstallation inutile / double instance. |
| `installer.bat` | Écriture de `.venv/.requirements.sha256`. | Dépendances réinstallées à chaque lancement. |
| `static/js/version.js` | `maj.natif`, `maj.portable`, `d.taille`, étapes téléchargement/signature/sauvegarde. | UI de mise à jour incohérente. |
| `static/js/rappels.js`, `static/js/philibert.js` | Désactiver les notifications navigateur si `window.NEXUS_NATIVE`. | Doublons de notifications. |
| `README.md`, `CHANGELOG.md`, `LICENSE`, `THIRD_PARTY.md`, `NE_PAS_PARTAGER.md`, `.gitignore` | Documentation et exclusions. | Documentation fausse ou secrets exposés. |
| `outils/tests/run_all.py` | Ajout de `test_maj_natif.py` et `test_portable.py`. | Tests non exécutés. |
| `outils/tests/test_maj.py` | Compatibilité avec la version gelée et les nouveaux champs. | Tests de mise à jour cassés. |
| `outils/release.py`, `outils/preparer_partage.py` | Nouveaux fichiers (`*.spec`, `*.iss`, `nexus_launcher.py`, docs, etc.). | Archive de release incomplète. |

## Fichiers à ne jamais copier

`config.json`, `deck.json`, `jeux.json`, `fan_names.json`, `runtime.json`,
`data/`, `logs/`, `maj/`, `sauvegardes-maj/`, `versions/`, `profils/` personnels,
`actions/` personnelles, `.venv/`, `dist/`, `build/`, `__pycache__/`, `.ruff_cache/`,
`partage/`, secrets `.pfx`, `.env`, jetons.

## Invariants à vérifier

- les données vont dans `%LOCALAPPDATA%\NEXUS` en installé, et dans le dossier de
  l'exe en portable ;
- `portable.flag` est détecté **avant** l'import de `paths` ;
- le mode portable désactive le démarrage automatique et la mise à jour par
  installeur ;
- l'installeur contient `NEXUS.exe` + `_internal/`, et supprime l'ancien
  `_internal` avant copie ;
- `nexus.spec` embarque `outils/appliquer_maj.ps1` et `panel.ico` ;
- `maj.py` refuse une mise à jour sans SHA256 ou sans signature conforme à la
  politique ;
- l'arrêt de l'application est propre (bot, rappels, statistiques, serveur) ;
- `run_all.py` passe, et `test_maj.py` passe dans un dépôt Git.
