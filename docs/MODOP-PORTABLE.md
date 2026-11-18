# Mode opératoire — adapter une nouvelle version de NEXUS en version portable

Ce document est écrit pour être exécuté par un développeur **ou par une IA**
(Claude, ChatGPT, etc.). Il part d'une nouvelle version du NEXUS d'origine
(par exemple une release de ton frère) et produit la version Windows
personnalisée : exe autonome, installeur et archive portable.

## 0. Entrées et sorties

**Entrées**

- une nouvelle version source de NEXUS (dossier, ZIP ou tag Git), par exemple
  `NEXUS-1.5.0` ;
- la version personnalisée de référence (ce dossier, 1.6.0) ;
- `docs/PERSONNALISATION.md` et `docs/PATCH-PERSONNALISATION-1.6.0.patch` ;
- Windows 10/11 64 bits, Python 3.11, Inno Setup 6.

**Sorties attendues dans `dist\`**

- `NEXUS\NEXUS.exe` + `NEXUS\_internal\` (onedir) ;
- `NEXUS-<version>-Setup.exe` ;
- `NEXUS-Portable-<version>.zip` ;
- `NEXUS.exe.sha256`, `NEXUS-<version>-Setup.exe.sha256`,
  `NEXUS-Portable-<version>.zip.sha256` et `SHA256SUMS.txt`.

Le résultat doit préserver **toutes** les fonctionnalités de la nouvelle version
d'origine, plus les apports natifs/portables décrits dans
`docs/PERSONNALISATION.md`.

## 0 bis. Prompt prêt à donner à une IA

> Tu vas adapter une nouvelle version de NEXUS en version Windows native et
> portable. Lis entièrement `docs/MODOP-PORTABLE.md` et
> `docs/PERSONNALISATION.md`. Utilise `docs/PATCH-PERSONNALISATION-1.6.0.patch`
> comme référence, mais ne copie jamais `config.json`, `data/`, `logs/`,
> `dist/`, `build/` ni les profils/actions personnels. Préserve les
> fonctionnalités de la nouvelle version upstream et réapplique les
> personnalisations décrites. Ensuite, exécute dans l'ordre :
> `python outils/verifier_personnalisation.py`, `python -m ruff check .`,
> `python outils/tests/run_all.py`, puis
> `python outils/build_native.py --installer --portable`. Corrige les erreurs
> jusqu'à ce que le vérificateur, le lint, les tests et le build passent.
> Termine par un test d'extraction du ZIP portable et vérifie que les données
> restent dans le dossier portable et que l'autostart est refusé.

## 1. Règles absolues

1. **Ne jamais copier les données** : `config.json`, `deck.json`, `jeux.json`,
   `data/`, `logs/`, `maj/`, `sauvegardes-maj/`, `versions/`, `.venv/`, `dist/`,
   `build/`, profils personnels, actions personnelles.
2. **Ne pas écraser un fichier modifié** par la version 1.6.0 sans fusion : cela
   supprimerait les nouveautés de la nouvelle version.
3. Les nouveaux fichiers listés dans `docs/PERSONNALISATION.md` peuvent être
   copiés tels quels, puis adaptés si l'upstream a changé une API.
4. Le mode portable ne doit **jamais** écrire dans `%LOCALAPPDATA%\NEXUS`,
   ni créer de raccourci ou d'entrée `Run` dans le registre.
5. La mise à jour automatique par installeur doit rester **désactivée** en
   portable, et la mise à jour native doit rester **vérifiée** (SHA256 +
   signature selon la politique).
6. Aucun secret (`.pfx`, jeton, mot de passe) ne doit entrer dans le dépôt.

## 2. Deux méthodes

### Méthode A — fusion guidée (recommandée)

On part de la nouvelle version upstream et on réintègre la personnalisation
fichier par fichier. C'est la méthode la plus sûre pour les futures versions.

### Méthode B — patch de référence

On applique `docs/PATCH-PERSONNALISATION-1.6.0.patch` sur une copie de la 1.6.0
d'origine, ou on l'utilise comme référence pour fusionner. Le patch peut ne pas
s'appliquer directement à une version plus récente : dans ce cas, utiliser
`git apply --3way` puis résoudre les conflits, ou revenir à la méthode A.

## 3. Préparation

Créer un dossier de travail neuf, par exemple `NEXUS-1.7.0-perso`, et y placer
la nouvelle version upstream. **Conserver** les fichiers upstream de la 1.6.0
(`runtime\`, `nexus.pyw`, `superviseur.py`, `outils\installer_python.ps1`,
`outils\python-prive.json`, profil « Averse de néons ») : ils ne font pas partie
de la personnalisation native/portable. Initialiser Git pour pouvoir comparer et
revenir en arrière :

```bat
cd NEXUS-1.7.0-perso
git init
git add .
git commit -m "upstream NEXUS 1.7.0"
```

Créer un environnement de build :

```bat
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-native.txt
```

Copier ensuite, depuis la version personnalisée de référence, uniquement les
fichiers de travail nécessaires à la comparaison :

```bat
:: exemple : dossier de référence
xcopy /E /I "D:\NEXUS-perso\docs" ".\docs-ref"
xcopy /E /I "D:\NEXUS-perso\outils" ".\outils-ref"
```

Ne pas copier `.venv`, `data`, `dist`, `build`, ni les fichiers personnels.

## 4. Méthode A — copier les nouveaux fichiers

Copier depuis la référence vers la nouvelle version :

```text
paths.py
logs.py
nexus_launcher.py
lancer_native.bat
Creer-NEXUS-Portable.bat
requirements-native.txt
nexus.spec
installer.iss
maj_natif.py
outils/build_native.py
outils/sign_native.ps1
outils/appliquer_maj.ps1
outils/verifier_personnalisation.py
outils/tests/test_paths.py
outils/tests/test_maj_natif.py
outils/tests/test_portable.py
.github/workflows/ci.yml
.github/workflows/build-native.yml
docs/GITHUB-FORK.md
docs/MODOP-PORTABLE.md
docs/PERSONNALISATION.md
docs/PATCH-PERSONNALISATION-1.6.0.patch
```

Puis fusionner les fichiers modifiés. Pour chaque fichier, garder la version
upstream comme base et réappliquer les changements décrits dans
`docs/PERSONNALISATION.md`. Les points les plus sensibles :

### 4.1 `paths.py` et l'ordre d'initialisation

`paths.py` doit rester importé **après** que les variables d'environnement
`NEXUS_DATA_DIR` / `NEXUS_PORTABLE` ont été posées par le lanceur. Vérifier :

- `APP_DIR`, `USER_ROOT`, `DATA_DIR`, `INSTALL_DIR` ;
- `FROZEN` (PyInstaller) ;
- `NEXUS_PORTABLE=1` → `USER_ROOT = dossier de l'exe` ;
- migration de l'ancien dossier sans écrasement ;
- `write_runtime` / `read_runtime` / `clear_runtime`.

### 4.2 `nexus_launcher.py`

Conserver dans cet ordre :

1. analyse des arguments ;
2. détection `portable.flag` **avant** `import paths` ;
3. `--configure` ;
4. instance unique ;
5. démarrage du serveur, `paths.write_runtime` ;
6. `app.start_services()` (qui écrit le marqueur de mise à jour) ;
7. tray + fenêtre WebView2.

Vérifier la présence de `--portable`, `_portable_flag`, `_mutex_name`,
`--install-autostart` bloqué en portable, `--remove-autostart` encore autorisé.

### 4.3 `maj.py` et `maj_natif.py`

La version source continue d'utiliser l'archive ZIP. La version gelée utilise
l'installeur :

- `derniere_release` sélectionne `NEXUS-*-Setup.exe` et `.sha256` ;
- `Updater.installer` branche sur `_installer_natif` si `paths.FROZEN` ;
- `_installer_natif` vérifie SHA256, Authenticode, politique de signature,
  sauvegarde l'installation, écrit le job et lance le helper ;
- `Updater.revenir` utilise la sauvegarde d'installation en gelé ;
- `maj_natif.marquer_demarrage_ok` est appelé par `app.start_services`.

### 4.4 `app.py`

Réappliquer :

- imports `paths`, `maj_natif` ;
- `start_services` / `stop_services` (bot, rappels, stats, alertes, updater) ;
- notifier natif et boucle d'alertes ;
- `RESTART_CODE` et `_redemarrer_pour_maj` ;
- routes `/api/maj`, `/api/maj/installer`, `/api/maj/revenir` ;
- `_journaliser_resultat_maj` (lecture `utf-8-sig`) ;
- `_single_instance_guard` (suffixe portable) ;
- marqueur `maj_natif.marquer_demarrage_ok()` en fin de `start_services`.

### 4.5 Chemins dans les modules métier

Réappliquer `paths` dans `deck.py`, `profiles.py`, `store.py`, `stats.py`,
`statistiques.py`, `configurer.py`, `bot.py`, `reminders.py`, `version.py`,
`maj_demarrage.py`. Les appels `mkdir(exist_ok=True)` deviennent
`mkdir(parents=True, exist_ok=True)` quand le dossier peut être imbriqué.

### 4.6 Front-end

Dans `static/js/version.js` :

- `maj.natif`, `maj.portable`, `d.taille` ;
- étapes `telechargement`, `verification`, `signature`, `sauvegarde`,
  `redemarrage` ;
- message spécifique portable et blocage de l'installation automatique.

Dans `static/js/rappels.js` et `static/js/philibert.js` : pas de notification
navigateur si `window.NEXUS_NATIVE`.

### 4.7 Build

Conserver `nexus.spec` avec :

- `outils/appliquer_maj.ps1` et `panel.ico` dans les données ;
- hooks webview, pystray, winotify, pycaw, winrt, keyring ;
- version/icône et exe `windowed`.

Conserver `installer.iss` avec :

- installation par utilisateur, WebView2, raccourcis ;
- `[InstallDelete]` de `_internal` et `NEXUS.exe` ;
- `UsePreviousTasks=yes`, `UsePreviousAppDir=yes` ;
- données `%LOCALAPPDATA%\NEXUS` jamais supprimées.

## 5. Méthode B — appliquer le patch

Le patch utilise les préfixes `old/` et `new/` : `-p1` est donc nécessaire.
Sur une copie **de la 1.6.0 d'origine** :

```bat
git apply --check -p1 --ignore-whitespace docs\PATCH-PERSONNALISATION-1.6.0.patch
git apply -p1 --ignore-whitespace docs\PATCH-PERSONNALISATION-1.6.0.patch
```

Pour une version plus récente, la méthode la plus fiable est de créer une
branche de personnalisation depuis la **1.6.0 d'origine**, d'y appliquer le
patch, puis de fusionner cette branche avec la nouvelle version :

```bat
git switch -c perso-1.6.0 v1.6.0
git apply -p1 --ignore-whitespace docs\PATCH-PERSONNALISATION-1.6.0.patch
git add -A
git commit -m "personnalisation native/portable 1.6.0"
git switch main
git merge perso-1.6.0
```

Un `git apply --3way` direct sur une version très différente peut échouer : les
blobs d'origine du patch ne sont pas dans le nouveau dépôt. En cas de conflit :
garder la fonctionnalité upstream, réappliquer le changement personnalisé, puis
lancer la vérification. Ne jamais utiliser `--reject` en aveugle.

Le patch ne dispense pas de lire `docs/PERSONNALISATION.md` : il peut être
incomplet si une future version déplace du code.

## 6. Vérification obligatoire

### 6.1 Invariants

```bat
.venv\Scripts\python.exe outils\verifier_personnalisation.py
```

Le script vérifie la présence des fichiers, les marqueurs `portable.flag`,
`maj_natif`, `appliquer_maj.ps1`, `[InstallDelete]`, la politique de signature,
etc. Il doit afficher `OK` et sortir avec le code 0.

### 6.2 Lint et tests

```bat
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe outils\tests\run_all.py
```

`run_all.py` doit passer **12/12** (ou plus) et ignorer `test_maj.py` hors dépôt
Git. Dans un dépôt Git, lancer aussi :

```bat
.venv\Scripts\python.exe outils\tests\test_maj.py
```

### 6.3 Build

```bat
.venv\Scripts\python.exe outils\build_native.py --installer --portable
```

Le build doit :

- signer l'exe avant l'installeur si un certificat est fourni ;
- passer le smoke test de l'exe ;
- produire l'installeur et le ZIP portable ;
- écrire les `.sha256` et `SHA256SUMS.txt`.

Pour un simple double-clic, `Creer-NEXUS-Portable.bat` fait la même chose en
mode portable uniquement, avec un environnement `.venv-build` séparé.
`Creer-NEXUS-Portable.bat --installer` construit aussi l'installeur.

### 6.4 Test du ZIP portable

Extraire le ZIP dans un dossier temporaire, puis :

```bat
NEXUS.exe --smoke-test --no-tray
```

Vérifier :

- code de sortie 0 ;
- création de `logs\nexus.log` et `data\` **dans le dossier portable** ;
- aucun `%LOCALAPPDATA%\NEXUS` créé ;
- `NEXUS.exe --install-autostart` sort avec le code 1 et ne modifie pas le
  registre ;
- `Lancer NEXUS.bat` et `LISEZMOI.txt` sont présents.

### 6.5 Test de l'installeur

Installer en silencieux dans un dossier temporaire, lancer le smoke test,
vérifier `--notify-test`, puis désinstaller. Les données doivent être conservées.

## 7. Critères d'acceptation

- [ ] `outils/verifier_personnalisation.py` : code 0.
- [ ] `ruff` : aucune erreur.
- [ ] `run_all.py` : tous les tests passent.
- [ ] `test_maj.py` : 50/50 dans un dépôt Git.
- [ ] `NEXUS.exe` démarre et `/api/version` répond.
- [ ] `NEXUS-Portable-<version>.zip` démarre sans installation.
- [ ] données du portable dans le dossier portable.
- [ ] autostart refusé en portable.
- [ ] installeur : installation, smoke test, désinstallation, données conservées.
- [ ] archives et hashes produits dans `dist\`.

## 8. En cas de doute

- Lire `docs/PERSONNALISATION.md` pour le rôle de chaque fichier.
- Comparer avec le patch de référence.
- Ne pas supprimer une fonctionnalité upstream pour faire passer un test :
  adapter la personnalisation.
- Si une API upstream change, garder le comportement (données hors programme,
  portable, mise à jour vérifiée) plutôt que la forme exacte du code 1.6.0.
