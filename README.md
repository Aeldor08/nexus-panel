# NEXUS — tableau de bord du PC

NEXUS affiche en direct l'état de ton PC Windows dans ton navigateur : processeur, mémoire, carte
graphique, températures, disques, réseau. Il propose aussi un lecteur de musique avec mélangeur de son,
un lanceur de jeux, un agenda, un mur de souvenirs, tes statistiques personnelles (temps de PC, de jeu, de
musique), un journal quotidien, un stream deck (gros boutons d'actions) et, si tu
veux, un bot Discord qui t'envoie des alertes.

Tout tourne **sur ton PC uniquement** : personne d'autre ne peut ouvrir NEXUS (sauf ton téléphone, si tu
l'autorises). Tes données restent sur ton PC : la seule connexion faite par NEXUS lui-même est la vérification
des mises à jour auprès de `api.github.com` (désactivable), plus le bot Discord si tu l'actives.

---

## Quelle version choisir ?

Tout se télécharge sur la page du dépôt GitHub → **Releases** (colonne de droite). Ne prends jamais
« Source code » : c'est un fichier technique de GitHub.

| | **Application Windows** *(recommandé)* | **Portable** | **Version source** |
|---|---|---|---|
| Fichier | `NEXUS-x.y.z-Setup.exe` (dernière release) | `NEXUS-Portable-x.y.z.zip` (release « version portable ») | `NEXUS-x.y.z.zip` (dernière release) |
| Installation | double-clic, 1 minute | dézipper, c'est tout | `installer.bat`, environ 10 minutes |
| Fenêtre | fenêtre NEXUS à part | fenêtre NEXUS à part | dans ton navigateur |
| Mises à jour | **automatiques** | **automatiques** (dossier modifiable) | automatiques |
| Tes données | `%LOCALAPPDATA%\NEXUS` | dans le dossier du portable (clé USB possible) | dans le dossier de NEXUS |
| Pour qui | tout le monde | une clé USB, un PC où on n'installe rien | modifier NEXUS, développeurs |

Les trois versions ont les mêmes fonctions. Windows 10 ou 11 en 64 bits est nécessaire.

> **Avertissement Windows SmartScreen.** NEXUS n'est pas signé avec un certificat payant : au premier
> lancement, Windows peut afficher « Windows a protégé votre ordinateur ». Clique sur **Informations
> complémentaires** puis **Exécuter quand même**. C'est normal pour un logiciel gratuit téléchargé.

---

## Installer l'application Windows (recommandé)

1. Dans la dernière release, télécharge **`NEXUS-x.y.z-Setup.exe`**.
2. Double-clique dessus (voir l'avertissement SmartScreen ci-dessus). Aucun droit administrateur n'est demandé :
   NEXUS s'installe pour ton compte Windows seulement, dans `%LOCALAPPDATA%\Programs\NEXUS`.
3. Choisis le dossier (celui proposé convient), puis les options : **raccourci sur le Bureau**,
   **LibreHardwareMonitor** (coché : températures du processeur, des disques et ventilateurs ; Windows demandera
   l'autorisation administrateur au lancement de NEXUS) et **lancement au démarrage de Windows** (décoché). Ces
   deux réglages se changent aussi plus tard dans **⚙ Réglages → Démarrage de Windows**.
   Puis **Installer**, et **Lancer NEXUS** à la fin.
4. Au premier lancement, une fenêtre de configuration s'ouvre :
   - **Mot de passe du Deck** (obligatoire) : il protège les boutons qui lancent des applis ou mettent le PC en
     veille, et il est demandé pour installer une mise à jour. **Note-le.**
   - **Bot Discord** (facultatif) : laisse vide si tu n'en veux pas, voir l'[étape 6](#étape-6--facultatif-bot-discord).
   - **Dépôt des mises à jour** : n'y touche pas ; même vide, NEXUS surveille le dépôt d'où vient
     l'installeur. Écris `non` seulement si tu ne veux aucune mise à jour.
5. NEXUS s'ouvre dans sa fenêtre et son icône apparaît près de l'horloge.

Ensuite :

- **Mises à jour** : NEXUS vérifie tout seul (au démarrage puis toutes les 6 heures) et te propose la nouvelle
  version. Tu valides avec ton mot de passe : il télécharge l'installeur, vérifie son empreinte SHA-256, sauvegarde
  l'installation, met à jour et redémarre. Si la nouvelle version ne démarre pas, l'ancienne est remise en place.
- **Changer le mot de passe ou Discord** : menu Démarrer → **Configurer NEXUS**.
- **Microsoft Edge WebView2** est nécessaire pour la fenêtre. Il est déjà présent sur Windows 11 et presque tous
  les Windows 10 ; sinon l'installeur te le signale et donne le lien.
- **Désinstaller** : Paramètres Windows → Applications → NEXUS (ou menu Démarrer → Désinstaller NEXUS). Le
  désinstallateur demande s'il faut **garder tes données** (`%LOCALAPPDATA%\NEXUS` : configuration, statistiques,
  photos, journal, Philibert, profils ajoutés) : **Non** par défaut, elles sont gardées et reprises si tu
  réinstalles ; **Oui** les efface définitivement, jeton du bot compris.
- **Températures du processeur** : LibreHardwareMonitor est installé avec NEXUS (option cochée). Si tu l'as
  décoché, voir l'[étape 5](#étape-5--facultatif-températures-du-processeur--librehardwaremonitor), avec le dossier
  `LibreHardwareMonitor` à créer dans `%LOCALAPPDATA%\Programs\NEXUS`. Sans lui, NEXUS fonctionne (températures
  « indisponibles »).
- **Tu avais déjà NEXUS sur ce PC** (portable, version ZIP avec `lancer.bat`, ancienne version) : menu Démarrer →
  **Importer mes données NEXUS** (ou `NEXUS.exe --importer`). La fenêtre cherche les autres NEXUS sur les disques et
  les clés USB (le plus récemment utilisé d'abord, avec ce qu'il contient), ou te laisse choisir le dossier. Elle
  reprend la configuration (mot de passe du Deck compris), l'agenda, le journal, les statistiques, Philibert, les
  souvenirs, les rappels, les téléphones appairés, le Deck, les actions et les profils ajoutés. Les deux NEXUS
  doivent être fermés : la fenêtre propose de le faire. Les données actuelles de l'application sont **remplacées**,
  après une copie dans `%LOCALAPPDATA%\NEXUS\sauvegardes-import\` ; l'autre NEXUS n'est **jamais modifié**
  (supprime-le quand tu as vérifié). Pas repris : journaux, caches, copies du code (`versions\`, `maj\`),
  LibreHardwareMonitor. Au tout premier lancement, une ancienne version source retrouvée par le raccourci « NEXUS »
  du Bureau est aussi reprise automatiquement (copie, sans rien écraser).
- **Où sont mes données ?** Programme (lecture seule) : `%LOCALAPPDATA%\Programs\NEXUS`. Données :
  `%LOCALAPPDATA%\NEXUS` (`config.json`, `data\` avec la base, les photos et Philibert, `logs\`, `profils\` ajoutés,
  `actions\`, sauvegardes de mise à jour). Jetons (bot Discord, GitHub) : gestionnaire d'identifiants de Windows.

## Version portable

1. Sur la page **Releases**, ouvre la release **« NEXUS x.y.z — version portable Windows »** et télécharge
   **`NEXUS-Portable-x.y.z.zip`**.
2. Clic droit → **Extraire tout…**, vers un dossier où tu peux écrire (Documents, clé USB…). Évite
   `C:\Program Files`.
3. Double-clique sur **`NEXUS.exe`** (ou `Lancer NEXUS.bat`). Au premier lancement, la même fenêtre de
   configuration que l'application Windows s'ouvre.

Tout reste dans ce dossier : configuration, `data\`, journaux, profils. Pour l'emporter ailleurs, déplace le
dossier entier. Il n'y a ni raccourci ni démarrage automatique (crée un raccourci vers `NEXUS.exe` si tu veux).
Pour y reprendre les données d'un autre NEXUS du PC : `NEXUS.exe --importer` (même fenêtre que l'application).

**Mettre à jour le portable** : comme l'application Windows, il se met à jour **tout seul** (depuis la
version 1.9.0). Une nouvelle version allume la pastille de version ; **Installer**, mot de passe du panel, puis
**Valider**. NEXUS télécharge `NEXUS-Portable-x.y.z.zip` (pré-release « version portable »), vérifie son
empreinte SHA256 et son contenu, sauvegarde `NEXUS.exe` et `_internal\` dans `maj\rollback\`, se ferme,
remplace seulement les fichiers du programme et se relance. Tes données (`config.json`, `deck.json`, `jeux.json`,
`data\`, `logs\`, `profils\`, `actions\`) ne sont jamais touchées. Si la nouvelle version ne démarre pas,
l'ancienne revient toute seule ; **↶ Revenir à la version précédente** marche aussi.

Il faut que le dossier du portable soit modifiable (pas une clé verrouillée ni `C:\Program Files`) ; sinon
NEXUS le dit et la mise à jour se fait à la main : ferme NEXUS, télécharge le nouveau ZIP, puis remplace
seulement `NEXUS.exe` et le dossier `_internal\`. C'est aussi le cas une seule fois pour passer d'un portable
antérieur à 1.9.0 à la 1.9.0.

---

## Installer la version source (aucune connaissance en Python nécessaire)

Compte environ 10 minutes. **Rien à installer sur Windows** : NEXUS apporte son propre Python (dossier
`runtime\`), indépendant du Python éventuellement installé sur le PC ; une mise à jour ou une désinstallation
de ce dernier ne le dérange jamais. Les étapes 5 et 6 (températures, Discord) valent pour les trois versions.

### Étape 1 — Dézipper NEXUS

Dans la dernière release, l'encadré **⬇️ Télécharger** donne un lien direct vers `NEXUS-x.y.z.zip`. Tu peux aussi
utiliser le zip qu'on t'a envoyé.

1. Fais un clic droit sur le fichier `NEXUS-x.y.z.zip` → **Extraire tout…** → **Extraire**.
2. Déplace le dossier obtenu à un endroit où tu le garderas, par exemple dans **Documents**.
   (Évite le Bureau synchronisé par OneDrive et les dossiers « Programmes ».)

### Étape 2 — (plus rien à faire : NEXUS a son propre Python)

Les anciennes versions de NEXUS demandaient d'installer Python soi-même : ce n'est plus le cas, passe à l'étape 3.

### Étape 3 — Lancer l'installation de NEXUS

1. Dans le dossier de NEXUS, double-clique sur **`installer.bat`**.
   - Si Windows affiche « Windows a protégé votre ordinateur » : clique sur **Informations
     complémentaires** puis **Exécuter quand même** (c'est normal pour un script téléchargé).
2. Une fenêtre noire s'ouvre et installe tout ce qu'il faut (1 à 3 minutes, il faut Internet) : le Python
   privé de NEXUS (14 Mo, paquet officiel de la Python Software Foundation sur nuget.org, empreinte SHA256
   vérifiée) dans `runtime\`, puis ses bibliothèques.
3. Elle affiche ensuite ce qu'elle a trouvé sur ton PC, par exemple :
   - `Carte graphique détectée : …` (NVIDIA, AMD ou Intel), puis la façon dont elle sera lue. Avec une
     carte **AMD ou Intel**, installe LibreHardwareMonitor (étape 5) pour avoir aussi sa température ;
   - `LibreHardwareMonitor n'est pas installé` : c'est facultatif, voir l'étape 5.

### Étape 4 — Répondre à l'assistant de configuration

Juste après, l'assistant pose quelques questions :

1. **Mot de passe du stream deck** (obligatoire) — il protège les boutons qui peuvent lancer des
   applis ou mettre le PC en veille. Tape-le deux fois (rien ne s'affiche pendant la frappe, c'est
   normal), ou appuie simplement sur **Entrée** pour qu'un mot de passe soit choisi pour toi :
   **note-le**, il ne sera plus jamais affiché.
2. **Bot Discord** (facultatif) — réponds `N` si tu n'en veux pas (tu pourras le faire plus tard).
   Pour le configurer, voir l'étape 6.

L'assistant crée le fichier `config.json`. Enfin, l'installateur propose un **raccourci NEXUS sur le
Bureau** : appuie sur `O` pour oui.

### Étape 5 — (Facultatif) Températures du processeur : LibreHardwareMonitor

Windows ne donne pas la température du processeur aux programmes ordinaires. Le logiciel gratuit
**LibreHardwareMonitor** sait la lire ; NEXUS l'utilise s'il est présent.

1. Va sur <https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases>, et dans la
   dernière version (section **Assets**), télécharge le fichier **`LibreHardwareMonitor-net472.zip`**
   (ou celui dont le nom ressemble le plus).
2. Dans le dossier de NEXUS, crée un dossier nommé exactement **`LibreHardwareMonitor`** (application Windows :
   dans `%LOCALAPPDATA%\Programs\NEXUS` ; portable : à côté de `NEXUS.exe`).
3. Dézippe le contenu du zip **dans** ce dossier : on doit avoir
   `LibreHardwareMonitor\LibreHardwareMonitor.exe`.
4. C'est tout : au prochain lancement, NEXUS le configure et le démarre tout seul.
   - Windows demande l'**autorisation administrateur** : clique sur **Oui** (sans cela, pas de
     température processeur).
   - Pour ne plus voir cette fenêtre à chaque lancement : **⚙ Réglages → Démarrage de Windows → Démarrer
     LibreHardwareMonitor sans la fenêtre d'autorisation**. Windows demande ton accord **une seule fois** ;
     LibreHardwareMonitor est alors copié dans `C:\Program Files\NEXUS\LibreHardwareMonitor` (que seul un
     administrateur peut modifier : aucun programme ne peut se glisser à sa place pour obtenir les droits) et une
     tâche planifiée `\NEXUS\LibreHardwareMonitor` le lance pour ton compte. Décocher retire la tâche et la copie
     (une autorisation aussi). Il faut un compte administrateur Windows.
   - La toute première fois, LibreHardwareMonitor propose d'installer le pilote **PawnIO** :
     accepte, c'est lui qui lit les capteurs.

Sans LibreHardwareMonitor, NEXUS fonctionne : les températures CPU et disques et les ventilateurs
affichent « indisponible ».

### Étape 6 — (Facultatif) Bot Discord

1. Va sur <https://discord.com/developers/applications> → **New Application** → donne un nom (ex. NEXUS).
2. Onglet **Bot** → **Reset Token** → **Copy** : c'est le **jeton** (garde-le secret).
3. Onglet **OAuth2 → URL Generator** : coche `bot` et `applications.commands`, puis les permissions
   *View Channels*, *Send Messages*, *Embed Links*. Ouvre le lien généré en bas et invite le bot sur
   ton serveur Discord.
4. Dans Discord : **Paramètres → Avancés → Mode développeur** (active-le). Ensuite :
   - clic droit sur ton nom → **Copier l'identifiant** : c'est ton **ID utilisateur** ;
   - clic droit sur le salon où tu veux les alertes → **Copier l'identifiant** : c'est l'**ID du salon**.
5. Version source : double-clic sur **`configurer.bat`**, garde ou change ton mot de passe, réponds `O` à la
   question Discord et colle le jeton, ton ID et l'ID du salon (clic droit dans la fenêtre noire = coller).
   Application Windows : menu Démarrer → **Configurer NEXUS** ; portable : `NEXUS.exe --configure`.
6. Relance NEXUS : le journal (`logs\nexus.log`) affiche `[Discord] Connecté : …`.

Commandes (pour toi seul, dans ce salon seulement) : `/stats`, `/disques`, `/gpu`, `/deck <bouton>`,
et `/command` qui les liste toutes.

---

## Utilisation au quotidien

*Application Windows et portable : NEXUS s'ouvre dans sa propre fenêtre ; fermer la fenêtre le laisse tourner près
de l'horloge (clic droit sur l'icône → **Quitter NEXUS** pour l'arrêter). Le reste de cette section concerne la
version source.*

- **Ouvrir NEXUS :** double-clic sur le raccourci **NEXUS** du Bureau (ou sur `lancer.bat`).
  NEXUS tourne en arrière-plan, **sans fenêtre noire** : son **icône** apparaît près de l'horloge et le
  navigateur s'ouvre tout seul sur `http://127.0.0.1:8000`. Clique sur **NEXUS** pour entrer.
- **L'icône près de l'horloge** (si elle est cachée : la petite flèche ^) : clic = ouvrir NEXUS ; clic droit
  = **Redémarrer NEXUS**, **Ouvrir le journal** (les messages du serveur, `logs\nexus.log`), **Quitter NEXUS**.
  Survole-la pour voir son état (en marche, mise à jour en cours…). Si le serveur plante, elle le relance
  toute seule (5 fois d'affilée au plus, puis une notification).
- **Fermer NEXUS :** clic droit sur l'icône → **Quitter NEXUS**.
- **Dépanner avec l'ancienne fenêtre noire :** `lancer.bat console` (messages du serveur en direct).
- **Changer le mot de passe ou Discord :** `configurer.bat`, puis clic droit sur l'icône → Redémarrer NEXUS.
- **Changer de mode :** bouton **◐** en haut (Terminal rouge / Sentinelle orange et bleu).
- **Changer de profil visuel :** bouton **🎨** en haut (voir « Profils visuels » ci-dessous).
- **Mettre à jour :** remplace les fichiers par ceux d'une version plus récente **sans toucher** à
  `config.json`, `deck.json` et au dossier `data\` (tes réglages et tes données).

## Construire l'application Windows et le portable (développeurs)

Prérequis : Python 3.11 ou 3.12, **Inno Setup 6** pour l'installeur (`winget install JRSoftware.InnoSetup`),
Internet au premier build. Facultatif : gitleaks (`winget install Gitleaks.Gitleaks`).

Une seule commande (ou double-clic sur **`Creer-NEXUS-Portable.bat`**, qui l'appelle) :

```bat
py -3.12 outils\build.py
```

Elle prépare l'environnement de build `.venv-build` (dépendances réinstallées seulement si un `requirements*.txt`
change), nettoie `dist\`, lance le lint (`ruff check`, `ruff format --check`), les tests, l'audit (`pip-audit`,
`gitleaks`), puis fabrique `NEXUS.exe` (PyInstaller, mode dossier : démarrage plus rapide qu'un fichier unique),
le teste au démarrage, construit `NEXUS-X.Y.Z-Setup.exe` (Inno Setup) et `NEXUS-Portable-X.Y.Z.zip`, avec leurs
`.sha256` et `SHA256SUMS.txt`. Options : `--sans-tests`, `--sans-audit`, `--sans-installeur`, `--sans-portable`,
`--sans-lhm`. LibreHardwareMonitor (MPL-2.0) est téléchargé une fois dans `build\tiers\` (version et empreinte
SHA256 fixées dans `outils\build_native.py`) et livré avec l'installeur (option cochée) et le portable.

Le dépôt GitHub à surveiller pour les mises à jour (remote `origin`, ou `--depot proprietaire/nom`) est embarqué
dans l'exe : une installation sait donc toute seule où chercher ses mises à jour. Sur chaque tag `v*`, la CI
(`.github/workflows/build-native.yml`) refait tout sous Windows et publie l'installeur et le portable s'ils manquent.

Tests : `python outils\tests\run_all.py` (`--couverture` pour la couverture, `.coveragerc`).

### Signature de code

L'exe et l'installeur ne sont **pas signés** : seule leur empreinte SHA-256 est vérifiée (publiée avec chaque
release, contrôlée par la mise à jour intégrée). Conséquences : Windows SmartScreen affiche « Windows a protégé
votre ordinateur » au premier lancement d'un fichier téléchargé (*Informations complémentaires → Exécuter quand
même*), et certains antivirus peuvent se méfier d'un exe PyInstaller non signé (faux positifs possibles).

L'étape est prête mais désactivée par défaut. Avec un certificat Authenticode (« code signing », payant ; les
certificats EV suppriment l'avertissement SmartScreen tout de suite, les certificats OV après un temps de
réputation) :

- en local : `py -3.12 outils\build.py --pfx C:\chemin\certificat.pfx` (mot de passe dans la variable
  `NEXUS_PFX_PASSWORD`) ou `--thumbprint <empreinte>` pour un certificat du magasin Windows ; il faut `signtool`
  (Windows SDK). L'exe est signé avant d'être mis dans l'installeur, puis l'installeur est signé ;
- en CI : secrets GitHub `WINDOWS_CERT_PFX_BASE64` (fichier .pfx en base64) et `WINDOWS_CERT_PFX_PASSWORD` ;
- pour signer après coup : `outils\sign_native.ps1`.

Une fois les releases signées, `mises_a_jour.signature` peut passer à `requise` (et `mises_a_jour.certificat` à
l'empreinte SHA1 du certificat) : la mise à jour intégrée refusera alors tout installeur non signé ou signé par
quelqu'un d'autre.

## Dépannage

| Problème | Solution |
|---|---|
| L'installation signale « Python prive de NEXUS n'a pas pu etre installe » | Vérifie la connexion Internet (NEXUS télécharge son Python une seule fois) et que le dossier n'est pas en lecture seule, puis relance `installer.bat`. |
| « Ce site est inaccessible » / `ERR_CONNECTION_REFUSED` | NEXUS ne tourne pas. Lance-le (raccourci NEXUS ou `lancer.bat`) : son icône apparaît près de l'horloge et le navigateur s'ouvre tout seul dès qu'il est prêt. S'il ne démarre pas : clic droit sur l'icône → **Ouvrir le journal**, ou lance `lancer.bat console` pour voir les messages en direct, et fais une capture d'écran de l'erreur (« [ERREUR] », « Traceback ») pour demander de l'aide. |
| « Le port 8000 est déjà utilisé » | NEXUS est déjà ouvert (regarde les icônes près de l'horloge, ou une ancienne fenêtre noire NEXUS), ou un autre programme utilise ce port : redémarre le PC. |
| Températures CPU « indisponibles » | Voir l'étape 5. LibreHardwareMonitor doit tourner (icône près de l'horloge Windows) et avoir été autorisé en administrateur. Test : <http://127.0.0.1:8085/data.json> doit afficher du texte. |
| GPU « indisponible » ou incomplet | NEXUS détecte tout seul la carte graphique (NVIDIA, AMD ou Intel) et l'affiche dans la même carte « GPU ». Les cartes **NVIDIA** sont lues entièrement par leur pilote. Les cartes **AMD et Intel** sont lues entièrement par LibreHardwareMonitor (étape 5) ; sans lui, NEXUS affiche quand même la charge et la mémoire vidéo (via Windows), mais pas la température. La ligne « lu par … » sous la carte indique la source utilisée. Si rien n'apparaît, mets à jour le pilote de la carte graphique. |
| Le bot Discord ne répond pas | Lis le message `[Discord]` dans le journal (clic droit sur l'icône → Ouvrir le journal) ; relance `configurer.bat` et vérifie le jeton et les deux ID. |
| La page a un affichage bizarre après une mise à jour | Ctrl+F5 dans le navigateur. |

---

## Média : lecture en cours

L'onglet **Média** affiche et pilote (⏮ ⏯ ⏭, clic sur la barre pour avancer) tout ce qui joue dans le panneau
multimédia de Windows :
- **applications** : Spotify, Deezer, Apple Music, iTunes, Tidal, Amazon Music, Qobuz, VLC, foobar2000, MusicBee,
  AIMP, Winamp, le Lecteur multimédia de Windows, Plex… ;
- **tous les navigateurs** : Opera GX, Opera, Chrome, Edge, Firefox (et LibreWolf, Waterfox, Floorp, Zen…),
  Brave, Vivaldi, Arc, Yandex… — avec le site deviné quand la page l'indique (Deezer, YouTube, SoundCloud…).

Les boutons réagissent au clic, sans attendre l'application, et l'écran suit les changements (piste suivante
lancée depuis Spotify, pause depuis le clavier…) dès que Windows les signale. Deezer, Apple Music, Tidal… sont
comptés en « Musique » dans les statistiques, même dans un navigateur.

## Agenda : évènements, anniversaires, rappels

**Ajouter :** onglet **Agenda** → clique sur un jour du calendrier → remplis le formulaire de la fenêtre du
jour (titre, date, heure, durée en minutes, description, répétition, date de fin, rappels) → **Ajouter**.
Sans heure, l'évènement dure toute la journée. Coche **🎂 C'est un anniversaire** pour un anniversaire :
il revient chaque année, toute la journée, avec l'âge si tu donnes l'année de naissance.

**Modifier ou supprimer :** dans la fenêtre du jour, **✎** sur l'évènement (le formulaire se remplit) puis
**Enregistrer**, ou **✕** pour supprimer. Si l'évènement se répète (un anniversaire aussi), NEXUS demande :

| Choix | Effet |
|---|---|
| **Cet évènement seulement** | seule cette date change (ou disparaît) ; toutes les autres restent comme avant |
| **Cet évènement et les suivants** | la série s'arrête la veille ; une nouvelle série commence à cette date avec tes changements. Le passé ne bouge pas |
| **Tous les évènements de la série** | toute la série change (ou est supprimée). Changer la date décale toutes les occurrences |

La répétition elle-même (tous les jours, semaines…) ne se change pas pour une seule date : choisis l'un des
deux autres. Les champs mal remplis (date impossible, durée négative…) sont signalés en rouge sous le champ.

**Fêtes et jours fériés :** le calendrier affiche tout seul les 11 jours fériés français (numéro du jour en
couleur, comme un calendrier papier) et les dates classiques : Épiphanie, Chandeleur, Saint-Valentin, Mardi
gras, Pâques, Pentecôte, fêtes des mères, pères et grands-parents, Fête de la musique, Halloween, réveillon,
Saint-Sylvestre et changements d'heure. Les dates mobiles (Pâques, Ascension, fête des mères…) sont calculées
sur ton PC, sans connexion. Le menu en haut du calendrier choisit **Fêtes et jours fériés**, **Jours fériés
seulement** ou **Sans les fêtes** (retenu sur cet appareil). Ce ne sont pas des évènements : pas de rappel.

**Rappels :** par défaut, 1 h puis 30 min avant chaque évènement. Ils s'affichent dans le panel (bannière en
haut à droite, avec un petit son), en notification Windows si les notifications sont activées, et sur Discord
si le bot est configuré. Ils sont calculés par NEXUS même si aucune page n'est ouverte.
- **Pour un évènement :** dans le formulaire, « Rappels » → **Personnalisés** → par exemple `1440, 60, 10`
  (1 jour, 1 h et 10 min avant). Vide = aucun rappel.
- **Pour tous :** dans `config.json`, section `agenda` :
  ```json
  "agenda": { "rappels_minutes": [60, 30], "heure_reference": "09:00", "rappels_discord": true }
  ```
  `heure_reference` sert de « début » aux évènements sans heure et aux anniversaires (rappels à 08:00 et
  08:30 avec les valeurs par défaut). Relance NEXUS après une modification.
- **Son :** ⚙ Réglages → « Jouer un son à chaque rappel » (par appareil), et **♪ Tester le son**.
- Un rappel n'est jamais envoyé deux fois, même si NEXUS redémarre. Si NEXUS était fermé à l'heure d'un
  rappel, il envoie au redémarrage le plus récent rappel manqué, si l'évènement n'a pas encore commencé.
  Un évènement créé 45 min avant son début ne reçoit que le rappel de 30 min. Si tu changes l'heure d'un
  évènement, ses rappels sont recalculés.

**Google Agenda (dans les deux sens) :** ⚙ Réglages → **Google Agenda**. Une fois relié, l'Agenda affiche
aussi les évènements de ton Google Agenda (bord bleu, pastille **G**, lien **↗** vers Google) et le formulaire
propose **Agenda : Google Agenda / NEXUS (sur ce PC seulement)**. Les évènements déjà dans NEXUS partent
tout seuls dans Google Agenda puis sont retirés de NEXUS, sans doublon (case « Envoyer automatiquement… », sauf
ceux gardés « sur ce PC seulement »). Créer, modifier (une occurrence, les suivantes, toute la série) ou
supprimer un évènement Google depuis NEXUS le change dans Google Agenda ; les changements faits dans Google
arrivent toutes les 10 minutes (réglable) ou tout de suite avec **⟳ Relire**, sous le calendrier. Les invitations
et les anniversaires de tes contacts sont en lecture seule. Les rappels de NEXUS (bannière, Discord) marchent
aussi pour les évènements Google. Mise en place unique (10 minutes, ton propre identifiant client sur Google
Cloud, gratuit) : [docs/GOOGLE_AGENDA.md](docs/GOOGLE_AGENDA.md). Le code secret et l'accès donné par Google
sont rangés dans le gestionnaire d'identifiants de Windows ; les réglages ne se changent que depuis le PC.

**Déplacer et redimensionner les fenêtres :** comme dans toutes les catégories, voir
[Réorganiser l'interface](#réorganiser-linterface-toutes-les-catégories).

**Sauvegarde :** au premier lancement de cette version, l'ancien agenda est copié dans
`data\backups\agenda-avant-format2-….json` avant d'être converti. Les anniversaires deviennent des
évènements « toute la journée » (l'ancienne heure est gardée dans le fichier, champ `ancienne_heure`).

## Souvenirs, statistiques personnelles, journal

Ces trois catégories gardent tout **sur ce PC**, dans `data\` : les photos dans `data\souvenirs\`, et le
reste dans la base `data\nexus.db`. Rien n'est envoyé sur Internet, et le bot Discord n'y a pas accès.
Une nouvelle installation démarre avec les trois catégories vides (et des dispositions par défaut propres).
Les notes du mur et sa disposition sont dans la base, jamais dans l'export d'un profil visuel ni dans la
copie à partager ; le bot Discord ne lit ni les notes, ni les photos, ni les dispositions, ni le détail des
statistiques. Avant chaque mise à jour de la base, une copie est faite dans `data\backups\`.

### Souvenirs (mur de photos)

- **Ajouter des photos :** onglet **Souvenirs** → glisse tes photos sur le cadre « Ajouter des photos », ou
  touche-le pour les choisir. Ça marche aussi depuis le **téléphone**, quand l'accès téléphone est activé :
  la galerie ou l'appareil photo s'ouvre. Choisis le jour du souvenir (aujourd'hui par défaut) et, si tu
  veux, une légende.
- Formats : **JPG, PNG, WebP**, 25 Mo maximum. Le vrai contenu du fichier est vérifié.
- **Métadonnées :** par défaut, NEXUS retire les informations cachées de la photo (appareil, date de prise
  de vue, **position GPS**). Coche « Garder les métadonnées » pour conserver le fichier d'origine tel quel.
- **Naviguer :** flèches ◀ ▶, « Aujourd'hui », choix d'une date, calendrier du mois (les jours avec des photos
  sont numérotés), frise des derniers jours. **Ce jour-là** montre la même date les années précédentes.
  **▶ Diaporama** fait défiler au hasard tes anciens souvenirs.
- Sur une photo : **✎** pour la légende, **📅** pour la déplacer vers un autre jour, **🗑** pour la supprimer du PC.

**Réorganiser le mur (chaque jour a le sien) :**
- **Déplacer** une photo ou une note : attrape sa poignée **⠿** en haut et fais-la glisser (à la souris, tu
  peux aussi glisser la photo elle-même ; un simple clic l'agrandit toujours).
- **Redimensionner :** coin **◢** en bas à droite (taille minimale et maximale pour rester lisible).
- Le dernier élément touché **passe devant** : photos et notes peuvent se superposer volontairement.
  Un aimant léger les aligne sur une grille ; garde **Alt** enfoncée pour le couper.
- **Au clavier :** Tab jusqu'à la poignée ⠿, puis flèches = déplacer, Maj + flèches = redimensionner.
- La disposition est **enregistrée par jour** : revenir sur un ancien jour affiche le mur exactement comme tu
  l'avais arrangé. Un jour jamais arrangé reçoit une grille propre ; une photo ajoutée se range sous les autres.
- **▦ Réorganiser automatiquement** remet le mur du jour en grille ; **↶ Annuler la dernière modification**
  revient en arrière (déplacements, tailles, rangement), tant que la page reste ouverte.
- Sur le **téléphone**, le même mur s'affiche réduit (jamais sous 55 %) ; s'il est plus large que l'écran,
  il défile de côté dans son cadre. Les poignées y sont plus grandes.

**Ajouter une note (post-it) :** bouton **＋ Ajouter une note** : une note sans photo apparaît sur le mur du
jour affiché, déjà ouverte en **édition** : écris directement dessus, c'est **enregistré pendant que tu écris**.
En édition, en bas de la note : **✓** pour terminer, **🎨** pour les couleurs, la **police**, **A− / A+** pour la
taille du texte, **📌** pour l'épingler et **🗑** pour la supprimer.
- **🎨 Couleurs :** 16 **fonds** (6 pastels accordés au mode et au profil visuel, 6 pastels fixes — menthe, ciel,
  lavande, corail, sable, blanc — et 4 papiers foncés — kraft, ardoise, nuit, bordeaux) et 9 couleurs
  d'**écriture** (automatique = foncée sur fond clair, claire sur fond foncé ; noir, sépia, bleu marine, bordeaux,
  vert forêt, violet, blanc, or).
- **Police :** celle du thème, les titres du thème (Uncial pour Dés du destin, Cinzel pour Pluie d'étoiles…), ou
  une police de Windows : sans empattement, avec empattement, manuscrite, plume, feutre, machine à écrire,
  élégante (sur un téléphone qui ne l'a pas : une police proche).
Une fois terminée (**✓**, **Échap**, **Ctrl + Entrée** ou un clic ailleurs), la note n'affiche plus que son texte
et un petit **✎** dans l'angle en haut à droite : un clic dessus (ou un double-clic sur le texte) la rouvre en
édition, avec toutes les options. Elle se déplace et se redimensionne comme une photo.
- **Note épinglée :** la même note s'affiche aussi sur tous les jours **suivants** (« 📌 depuis le … »). La
  modifier la change partout ; chaque jour garde sa propre place pour elle. Désépinglée, elle ne reste que
  sur son jour d'origine. La supprimer depuis n'importe quel jour la supprime partout (NEXUS te prévient).

### Statistiques personnelles

NEXUS mesure toutes les 10 s, sans ralentir les jeux :
- le temps actif et inactif, d'après le dernier évènement clavier ou souris ; un jeu au premier plan compte
  comme actif, pour la manette ;
- tes sessions, du début à la fin ;
- le temps par jeu, par appli et par catégorie ;
- la charge CPU et GPU, par heure.

L'onglet **Statistiques** affiche aujourd'hui, 7 jours ou 30 jours : camembert par catégorie, classement des
jeux, activité par heure ou par jour, et pics de CPU et GPU.

**Consulter un ancien jour :** cadre **Détail du jour**, sous le graphique. Choisis le jour avec ◀ ▶, le
calendrier (champ date) ou **en cliquant sur une barre** de « Activité par jour » (7 ou 30 jours) ;
« Aujourd'hui » y revient. Tu y vois l'heure de début et de fin, le temps actif et inactif, une **frise par
heure** (barres = temps actif, trait = charge CPU), la charge moyenne et les pics CPU et GPU, et le temps par
catégorie, par jeu, en musique et médias, et par appli. Un jour sans mesure l'indique clairement.

**Seuls des noms de processus et des durées sont enregistrés :** jamais de titre de fenêtre, d'historique de
navigation, de frappe ni de contenu d'écran.

**Configurer `jeux.json`** (créé au premier lancement à partir de `jeux.example.json`, à la racine de NEXUS) :

```json
{ "processus": {
    "valorant-win64-shipping.exe": { "nom": "Valorant", "categorie": "jeu" },
    "spotify.exe": { "nom": "Spotify", "categorie": "musique" } } }
```

- La clé est le nom du **.exe**, en minuscules ; tu le trouves dans le Gestionnaire des tâches, onglet Détails.
- Catégories : `jeu`, `musique`, `video`, `navigation`, `travail`, `autre`.
- Les changements sont pris en compte dans la minute, sans relancer NEXUS.
- Les jeux reconnus par le mode jeu sont comptés même s'ils ne sont pas dans la liste.
- Comment chaque catégorie est comptée :
  - **jeu :** tant qu'il tourne ;
  - **musique et vidéo :** seulement quand Windows indique qu'une lecture est en cours ;
  - **autres catégories :** quand l'appli est au premier plan et que tu es actif ;
  - **avec `"mode": "ouverte"` :** tant que l'appli est **ouverte** (même en arrière-plan) **et** que tu es actif
    (rien pendant l'inactivité).

**Déclarer une appli de travail (ex. Claude) :** ajoute une ligne dans `jeux.json` :

```json
"claude.exe": { "nom": "Claude", "categorie": "travail", "mode": "ouverte" },
"notion.exe": { "nom": "Notion", "categorie": "travail", "mode": "ouverte" }
```

`claude.exe` est le vrai nom du processus de l'application de bureau Claude (vérifié dans le Gestionnaire
des tâches) ; il est déjà dans `jeux.json`. La ligne Notion est un exemple à adapter : remplace-la par le .exe
de ton appli. **Limite :** NEXUS ne voit que les **applications installées**. Claude utilisé dans un
**onglet du navigateur** n'est pas détectable : il faudrait lire les titres des fenêtres, ce que NEXUS ne
fait jamais. Ce temps-là compte en « navigation ».

**Mettre en pause :** bouton **⏸ Mettre en pause** (puis ▶ Reprendre). **Conservation :** liste « Garder »,
de 30 jours à 5 ans ; les données plus anciennes sont effacées toutes seules. **Tout effacer :**
**🗑 Tout effacer**, puis tape `EFFACER` pour confirmer.

### Journal quotidien

- Chaque jour : une **humeur**, des **activités** à cocher et un texte libre. Tout est **enregistré
  pendant que tu écris** (« enregistré ✔ »).
- **Naviguer :** flèches, « Aujourd'hui », choix d'une date, **vue mois** (l'humeur de chaque jour écrit),
  **recherche** dans les textes. Les anciennes entrées se relisent et se modifient.
- **Activités proposées :** dans `config.json`, section `journal` → `activites` (liste de
  `{"emoji": "🎮", "nom": "Jeu"}`). Relance NEXUS après une modification.
- **Mot de passe :** coche « Demander le mot de passe du panel pour ouvrir le Journal » (c'est le mot de
  passe du stream deck). Le Journal se reverrouille après 15 min sans activité ; 🔒 le reverrouille tout de suite.
- **Exporter :** boutons **⤓ Markdown** et **⤓ Texte** : le fichier est téléchargé sur l'appareil qui le demande.
- **Visage du jour :** en haut à droite du jour, l'humeur en grand, avec les émojis des activités cochées en
  petit autour (en arc, ou en cercle s'il y en a beaucoup). Au-delà de 8 activités, un **+N** donne la liste
  au survol (au doigt : touche-le). La **vue mois** montre le même visage en plus petit (4 activités, puis +N).
- La vue mois est plus grande par défaut et suit la taille de son cadre : agrandis-le avec le coin ◢.

## Réorganiser l'interface (toutes les catégories)

Dans **chaque catégorie** (Sommaire, PC, Média et mélangeur, Deck, Lanceur, Réseau, Statistiques, Agenda,
Souvenirs, Journal), chaque bloc se déplace et se redimensionne, avec le même fonctionnement partout :
- **Déplacer :** attrape le bloc par son **titre** (ou par la poignée **⠿** des blocs sans titre) et fais-le glisser.
- **Redimensionner :** coin **◢** en bas à droite. Taille minimale pour rester lisible.
- **Au clavier :** Tab jusqu'au titre du bloc, puis **flèches** = déplacer, **Maj + flèches** = redimensionner
  (Ctrl : pas fin).
- **Pas de chevauchement accidentel :** un aimant léger aligne les blocs sur une grille et sur les bords des
  autres (Alt : sans aimant) ; un bloc posé sur un autre pousse celui-ci vers le bas. (Seul le mur des
  souvenirs permet de superposer exprès.)
- **Jamais de barre de défilement sur les pages aux valeurs qui bougent** (Sommaire, PC, Média, Réseau,
  Statistiques) : un bloc trop petit pour son contenu (police plus grande d'un profil, ligne en plus…) grandit
  tout seul à la taille du contenu et pousse les blocs du dessous. Il ne peut pas être réduit sous son contenu.
- Tant que tu ne bouges rien, chaque catégorie garde sa mise en page d'origine.
- La disposition est retenue **par catégorie, sur cet appareil** (le PC et le téléphone ont chacun la leur)
  **et par mode** (Terminal et Sentinelle ont chacun la leur).
- **Bouton de verrouillage** (en haut de chaque catégorie) : il affiche l'**état actuel** de la mise en page.
  **🔓 Déverrouillé** (vert) : les blocs se déplacent et se redimensionnent ; **🔒 Verrouillé** (ambre) : plus
  aucun déplacement ni redimensionnement, pour éviter les accidents au doigt. Un clic passe d'un état à l'autre ;
  l'état est retenu par catégorie, sur cet appareil. (Rien à voir avec le bouton du stream deck qui verrouille
  la session Windows.) **↺ Réinitialiser la disposition** remet la catégorie dans sa mise en page d'origine
  (pour ce mode, sur cet appareil).
- Les profils visuels changent l'apparence des blocs, jamais leur place ; les tailles de ⚙ Réglages
  (80 % à 150 %) agrandissent le contenu des blocs.
- Sur téléphone, les poignées sont plus grandes. Astuce : passe la mise en page en **🔒 Verrouillé** pour faire
  défiler la page sans attraper un bloc par erreur.

## Tailles de l'interface

**⚙ Réglages** (en haut) → un curseur par partie, de 80 % à 150 % : Lanceur (125 % par défaut), Stream deck
(115 %), Mélangeur de son (115 %), Agenda (105 %). Le changement est immédiat et retenu sur cet appareil.
**↺ Tailles par défaut** remet les valeurs d'origine. Les profils visuels ne peuvent pas annuler ces réglages.

---

## Profils visuels

Un **profil** change l'apparence du mode en cours (couleurs, polices, fond, formes, effets) sans rien
changer au fonctionnement ni aux données. Chaque mode (Terminal, Sentinelle) a son propre profil, et
chaque appareil retient le sien : le PC et le téléphone peuvent avoir des profils différents.

**Choisir un profil :** clique sur **🎨** en haut → choisis dans la liste. Le changement est immédiat,
sans recharger la page. La liste ne montre que les profils compatibles avec le mode en cours, avec
leurs couleurs. **Défaut** (l'apparence d'origine) est toujours là et ne peut pas être supprimé ; NEXUS y
revient tout seul si un profil est cassé ou a disparu.

Fournis en exemple : **Pure** (tout en pastel : fond menthe, cartes et onglets teintés par catégorie, les deux modes), **Ardoise** (sombre sobre, les deux modes), **Néon Minuit** (néon années 80,
Sentinelle), **Phosphore** (vieux terminal vert, Terminal), **Sakura** (cerisier en fleurs, les deux modes)
, **Pluie d'étoiles** (ciel cosmique, voie lactée, étoiles filantes, nuages aux bords ambrés et montagnes
dans la brume ; polices libres Cinzel et Inter incluses avec leurs licences ; les deux modes) et **Dés du
destin** (salle de donjon rouge et or : murs de pierre, torches, braises et brume, grands dés rouges aux
chiffres dorés, runes qui s'allument, jauges de lave ; polices libres Uncial Antiqua et Inter incluses ; les
deux modes). Son intro : un dé rouge roule, s'arrête sur 20, la salle s'éclaire en écarlate, les runes
s'allument et le logo NEXUS apparaît dans un éclat. Petit clin d'œil : quand toutes les alertes sont
résolues, un 20 doré apparaît un instant dans le coin ; à une nouvelle alerte critique, un 1 rouge.
Avec Sakura, la page de garde a sa propre intro : un cerisier pousse puis fleurit, et le logo NEXUS apparaît
porté par les pétales. « Passer l'intro », un clic ou une touche la passe. Au clic sur NEXUS, on s'envole
à travers les pétales jusqu'au sommaire.

**Passage au sommaire :** au clic sur NEXUS, Sakura, Pluie d'étoiles et Dés du destin s'ouvrent EN ROND
depuis le logo (anneau rose, bleu glacier ou de feu). ⚙ Réglages → « Passage au sommaire » permet de choisir
une autre fin **pour le profil visuel en cours** : ouverture en rond, vieille télé qui s'allume, simple fondu,
ou « celui du profil ». Chaque profil garde son propre choix (ex. Sakura en télé, Pluie d'étoiles en fondu),
retenu sur cet appareil, même après un changement de profil ou un redémarrage. (Le profil Défaut a sa propre
intro, sans ce réglage.)

**Couper les intros des profils :** ⚙ Réglages → décoche « Jouer l'intro animée des profils visuels »
(retenu sur cet appareil) : la page de garde s'affiche directement, avec le bouton NEXUS.

**Changer de profil en douceur :** au choix d'un profil dans 🎨, NEXUS affiche un bref écran de transition
(logo, « Chargement du profil … », version, barre) pendant qu'il précharge le profil et toutes ses images
et polices ; le nouveau thème n'apparaît, en fondu, qu'une fois tout prêt (≈ 1,5 s la première fois, ≈ 1 s
ensuite). Un clic pendant la transition est ignoré ; si tu en choisis plusieurs à la suite, c'est le dernier
qui s'applique. Si un profil ne se charge pas, NEXUS revient au précédent et te le dit. Sans animation : un
simple fondu court.

**Du bouton NEXUS au sommaire :** avec Sakura, Pluie d'étoiles et Dés du destin, la fin de l'animation et
l'apparition du sommaire se chevauchent (la page de garde s'efface pendant que le sommaire, préparé à
l'avance, se révèle) : feuilles qui passent encore au premier plan, étoiles qui restent en fond, souffle chaud
qui se dissipe.

Un profil peut animer la page de garde sans JavaScript : le panel indique l'étape en cours sur
`<body data-etat="intro | reconnexion | pret | veille | transition | arrivee | panel">`, et `profil.json`
peut régler la durée de l'intro et de la transition (champ `animations`). Pendant un changement de profil :
`<body data-profil-etat="changement | pret">` ; couleur d'accent d'un profil : variable `--accent-profil`.
Pour les alertes, le panel pose aussi `<body data-alerte="aucune | normale | critique">` et, pendant 3 s,
`data-alerte-evenement="nouvelle-critique | resolue"`. Tout est décrit dans `profils\FORMAT.md`, § 4.6.

**Ajouter un profil à la main :** dépose son dossier dans `profils\`, puis 🎨 → **⟳ Actualiser**. Un
profil invalide n'est pas proposé : il apparaît en bas du menu dans « profil(s) ignoré(s) » avec la liste
de ses erreurs. Pour le vérifier :

```bash
runtime\python.exe valider_profil.py profils\nom-du-profil
```

**Le créer avec Claude Code :** ouvre Claude Code dans le dossier de NEXUS et demande par exemple :
« *Crée-moi un profil style océan calme en suivant profils/FORMAT.md* ». Le fichier `profils\FORMAT.md`
décrit tout le format (fichiers, champs, variables CSS, sélecteurs, interdits, limites), et
`profils\_modele\` est un point de départ à copier. Quand tu modifies le `style.css` du profil actif, la
page se met à jour toute seule en quelques secondes.

**Légèreté :** les fichiers d'un profil (CSS, images, polices) restent en cache dans le navigateur : au
rechargement, seul le strict nécessaire repasse par le réseau, et une modification du profil est vue tout
de suite (l'adresse change avec le contenu). Les pages et les données du panel ne sont jamais gardées en
cache. Quand l'onglet du navigateur est caché, les animations sont mises en pause et le panel interroge le
PC moins souvent.

**Partager un profil :** 🎨 → bouton **⤓** sur le profil → un fichier `profil-xxx.zip`. De l'autre côté :
🎨 → **⤒ Importer…** et choisir le .zip, ou glisser-déposer le .zip ou le dossier sur le menu. NEXUS vérifie
le profil avant de l'installer ; si un profil du même nom existe, il demande s'il faut **remplacer**
l'existant ou **garder les deux** (le nouveau prend un suffixe, ex. `-2`). 🗑 supprime un profil.

**Sécurité :** un profil ne contient que du JSON, du CSS et des images ou polices (5 Mo maximum). NEXUS
refuse à l'import, et retire au chargement : `@import`, toute adresse Internet, `data:`, les chemins
absolus ou avec `..`, `expression()`, `javascript:`, les balises HTML, les SVG avec script. Rien n'est
jamais chargé depuis Internet. Les profils sont soumis à la même protection que le reste du panel :
ce PC, ou un téléphone appairé.

---

## Santé, journal d'activité, processus, focus

- **✚ Santé** (en haut, ou lien du sommaire) : l'état de chaque partie de NEXUS (serveur, bot Discord,
  LibreHardwareMonitor, carte graphique, suivi des statistiques, lecture en cours, mises à jour, base, disque,
  téléphone) et les dernières erreurs du serveur. Une pastille orange ou rouge s'allume sur le bouton quand quelque
  chose ne va pas : c'est le premier endroit à regarder quand un bloc ne s'affiche plus.
- **Journal d'activité** (2e onglet de la fenêtre Santé) : chaque action sensible avec l'heure et l'appareil :
  boutons et connexions du deck, mises à jour, appairage ou refus d'un appareil, fermeture d'un processus,
  sessions de focus. Gardé sur ce PC (`data\activite.jsonl`), jamais de mot de passe ni de jeton dedans.
- **PC → Processus → ▤ Classement** : tous les programmes, du plus gourmand au moins gourmand (processeur ou
  mémoire), avec un champ de **recherche** et **✖ Fermer** (confirmation demandée ; comme « Fin de tâche » ;
  Entrée ferme le programme quand il ne reste qu'un résultat). Les processus vitaux de Windows et
  NEXUS lui-même sont protégés, et la fermeture n'est possible que depuis le PC.
- **⏱ Focus** : minuteur Pomodoro (25 min de travail / 5 min de pause, pause longue toutes les 4 séances, tout est
  réglable). Le temps de travail compte dans **Travail** de tes statistiques, même si tu lis sans toucher au PC.
  Option « profil sobre » : le profil Ardoise s'applique pendant la session, puis ton profil revient.

## Mises à jour

NEXUS vérifie tout seul s'il existe une nouvelle version : au démarrage, puis toutes les 6 heures
(**⚙ Réglages → Version et mises à jour** : intervalle, désactivation, dépôt surveillé, jeton). Il ne
contacte que l'API des releases de GitHub (`api.github.com`) pour le dépôt configuré.

- Une nouvelle version allume une **pastille** sur le bouton de version et affiche une **notification** sur la
  page de garde et en haut du sommaire (un bandeau sur les autres onglets) : **Mettre à jour** ouvre
  directement l'installation, **Plus tard** repousse le rappel de 24 h.
- Rien ne s'installe sans **le mot de passe du panel** (celui du deck) **et ta validation** : à chaque mise à jour,
  un récapitulatif « Valider la mise à jour vers X ? » s'affiche ; « Annuler » ne touche à rien. Le bot Discord ne peut
  jamais lancer une installation ; il peut seulement te prévenir (option « Me prévenir sur Discord »).
- L'installation : téléchargement depuis le dépôt configuré seulement → contrôle **SHA256** (archive refusée
  si elle ne correspond pas) → **sauvegarde horodatée** du code, de `data\` et de `config.json` dans
  `sauvegardes-maj\` → remplacement du code et des profils officiels (jamais `data\`, `config.json`, ni tes
  profils personnels) → migrations (base et configuration, avec une sauvegarde avant chacune) →
  redémarrage et **test de démarrage**. Si le test échoue, tout est **restauré automatiquement** et un
  bandeau le dit clairement.
- **Revenir à la version précédente** (fenêtre Version) remet le code d'avant la dernière mise à jour.
- Dépôt **privé** : il faut un jeton GitHub en lecture seule limité à ce dépôt, voir `docs\JETON_GITHUB.md`.
- Sans connexion, limite de requêtes atteinte ou jeton invalide : un message clair, rien n'est touché.

Les **alertes** (disque plein, température…) ont un bouton **Ignorer** : l'alerte disparaît jusqu'à la prochaine
ouverture de NEXUS ou son prochain démarrage (mise à jour comprise), et revient si le souci persiste.

Un profil peut indiquer `"panel_min_version"` dans `profil.json` : s'il demande une version plus récente,
il est refusé avec un message au lieu de s'afficher de travers.

## Publier une version (développeurs)

Le fichier `VERSION` est la source de vérité, `CHANGELOG.md` suit le format *Keep a Changelog*.

1. Note les changements sous `## [Non publié]` dans `CHANGELOG.md` et commite-les.
2. Lance `.venv\Scripts\python.exe outils\release.py correctif` (ou `mineur`, `majeur`, ou un numéro précis).
   Il vérifie que l'arbre Git est propre, lance les tests, `valider_profil.py --tous` et la détection de
   secrets, fait avancer `VERSION`, date la section du CHANGELOG, commite, crée le tag `vX.Y.Z`, fabrique
   `dist\NEXUS-X.Y.Z.zip` (code seulement : ni `data\`, ni configuration réelle, ni journaux, sauvegardes ou
   références) et son `.sha256`, pousse, puis publie la release avec `gh release create`.
   `--sans-publier` s'arrête avant l'envoi.
   Il construit aussi **l'installeur** `NEXUS-X.Y.Z-Setup.exe` (+ `.sha256`), joint à la même release : c'est
   lui que les applications installées téléchargent pour se mettre à jour. Le ZIP portable part dans une
   pré-release `portable-X.Y.Z` à part (jamais dans `vX.Y.Z` : les versions source prennent le dernier `.zip`
   de la release). Il faut `.venv-build` (lancer une fois `Creer-NEXUS-Portable.bat`) et Inno Setup 6 ;
   `--sans-natif` publie seulement l'archive source, mais les applications installées ne pourront alors pas
   se mettre à jour vers cette version.
3. GitHub Actions relance tests, lint, validation des profils et détection de secrets à chaque push et
   pull request (`.github/workflows/ci.yml`) ; sur un tag `v*`, `release.yml` refabrique l'archive et son
   SHA256 et les joint à la release si elle ne les a pas.

## Partager NEXUS avec quelqu'un

Double-clic sur **`preparer_partage.bat`**. Il crée `partage\NEXUS-x.y.z.zip`, une copie **sans
aucune donnée personnelle** : il ne prend que le code et les fichiers d'exemple, puis vérifie la
copie et annule tout s'il y trouve un de tes secrets (jeton, mot de passe, ID Discord, nom
d'utilisateur Windows, nom du PC, chemins personnels, noms d'appareils). Envoie ce zip : la
personne suit ce README depuis l'étape 1.

Plus simple encore : envoie le lien de la page **Releases** et dis de prendre `NEXUS-x.y.z-Setup.exe`
(installation en un clic, mises à jour automatiques).

La liste de ce qui ne doit jamais être partagé est dans **`NE_PAS_PARTAGER.md`**.

---

## Philibert, l'iguane de NEXUS

Un petit iguane vert vit sous la barre du haut : il s'y promène, s'arrête, regarde autour de lui, cligne des yeux,
hoche la tête, se dore au soleil et dort la nuit. Sa bulle dit comment il va (cœur, **!** s'il a besoin de toi,
Zzz, petit nuage s'il est malade). **Clique sur lui** (ou ⚙ Réglages → 🦎 Ouvrir son île) pour rejoindre son île :
nourris-le (100 % végétal, les fruits sont des friandises), réchauffe-le sur le rocher chaud (c'est un lézard à
sang froid), baigne-le, nettoie, soigne-le, joue avec lui (quatre mini-jeux qui rapportent des coquillages), achète
de la nourriture, une lampe chauffante, des accessoires et de la déco, et lis son carnet (historique, succès,
cartes postales, fiches « Le savais-tu ? »).

- Tout est dessiné d'après nature : un vrai iguane vert (écaille ronde sous l'oreille, fanon dentelé, crête, queue
  annelée), un cocotier, un lagon turquoise, des crabes fantômes, des cumulus, la lune à sa vraie phase, les ombres
  qui suivent le soleil.
- Sa **boutique** propose aussi des pièces rares et légendaires (couronne d'or, diadème de nacre, cape royale, coffre
  au trésor…), chères mais jamais au détriment des soins. L'île a ses **bruits** selon la météo (vagues, pluie, vent,
  grenouilles la nuit, discrets et coupables) et un **mode sombre** (automatique selon le thème du panel).
- Toutes les règles chiffrées (jauges par heure, chaleur selon la météo, soleil ou lampe…) : `docs\PHILIBERT-REGLES.md`.
- **Le temps passe même NEXUS fermé** (heure réelle ; plus lentement la nuit et pendant tes absences).
- Une **tuile Philibert** sur le sommaire montre son humeur et ce dont il a besoin, avec des accès directs.
- L'île vit au rythme des **saisons** (selon le mois réel) et propose quatre mini-jeux, dont la **course au rocher
  chaud**. Le carnet garde un **album** : les étapes de sa vie et les Philibert d'avant.
- **Philibert ne meurt jamais** : malade trop longtemps, la tortue vétérinaire l'emmène se reposer (12 à 24 h) et
  il revient en forme avec une carte postale qui explique ce qui lui a manqué. Si tu t'absentes plusieurs jours,
  la voisine de l'île le prend en pension. **Mode vacances** dans ses réglages : tout est en pause.
- Réglages de Philibert : le voir ou non en haut, vitesse normale ou lente, sons, notification Windows ou
  Discord s'il tombe malade, recommencer avec un nouvel œuf. Règles détaillées : `docs\PHILIBERT.md`.
- Ses données restent sur ce PC (`data\philibert.json`, jamais partagé). Il s'immobilise en mode jeu et avec
  « réduire les animations » de Windows.

## Détails techniques

### Fichiers

| Fichier | Rôle |
|---|---|
| `installer.bat` | Installe NEXUS : Python privé `runtime\`, dépendances, configuration, raccourci |
| `lancer.bat` | Démarre NEXUS en arrière-plan (icône près de l'horloge) ; `lancer.bat console` : ancienne fenêtre noire |
| `nexus.pyw` / `superviseur.py` | L'icône près de l'horloge : démarre et relance le serveur, mises à jour, LibreHardwareMonitor, journal `logs\nexus.log` |
| `outils\installer_python.ps1` / `outils\python-prive.json` | Installe (ou refait) le Python privé : version, adresse nuget.org et empreinte SHA256 |
| `configurer.bat` / `configurer.py` | Assistant de configuration (crée `config.json`) |
| `preparer_partage.bat` / `outils\preparer_partage.py` | Prépare une copie propre à partager |
| `restaurer_version.bat` | Revient à une version précédente (sauvegardes dans `versions\`) |
| `app.py` | Serveur web (FastAPI) : routes, sécurité réseau, démarrage du bot |
| `stats.py` | Capteurs : CPU, RAM, disques, GPU, températures, ventilateurs, réseau, processus |
| `bot.py`, `deck.py`, `config.py` | Bot Discord, stream deck, lecture de la configuration |
| `audio.py`, `media.py`, `launcher.py`, `lan.py`, `gamemode.py`, `remote.py`, `store.py`, `version.py` | Son, lecture en cours, lanceur, réseau, mode jeu, accès téléphone, stockage, versions |
| `static\` | La page web (HTML, CSS, JavaScript) ; `static\js\profiles.js` et `static\profiles.css` : menu des profils |
| `db.py` | Base SQLite locale `data\nexus.db` : création, migrations numérotées (sauvegarde avant chaque migration) |
| `souvenirs.py`, `statistiques.py`, `journal.py` | Mur de souvenirs (photos, notes, disposition par jour), statistiques personnelles (service en arrière-plan, détail d'un jour), journal quotidien |
| `mur.py` | Calculs du mur de souvenirs : grille automatique, tailles mini / maxi (sans base ni fichiers) |
| `static\js\souvenirs.js`, `static\js\mur.js`, `static\js\statistiques.js`, `static\js\journal.js`, `static\perso.css` | Pages de ces trois catégories ; `mur.js` : mur libre et notes |
| `jeux.example.json` | Modèle de `jeux.json` (association processus → nom et catégorie) |
| `agenda.py` | Agenda : évènements, répétitions et exceptions, modification par portée, validation, migration |
| `reminders.py` | Rappels de l'agenda (calcul, envoi panel + Discord, mémoire des rappels envoyés : `data\rappels.json`) |
| `agenda_google.py` | Liaison avec Google Agenda : connexion OAuth (PKCE), copie locale `data\agenda_google.json`, conversions et écriture dans Google (guide : `docs\GOOGLE_AGENDA.md`) |
| `static\js\layout.js`, `static\js\blocs.js` | Blocs déplaçables et redimensionnables : le moteur unique (`layout.js`) et son application à toutes les catégories (`blocs.js`) |
| `static\js\rappels.js`, `static\js\reglages.js`, `static\ui.css` | Bannières de rappel, menu ⚙ Réglages (tailles), styles des blocs et de l'agenda |
| `philibert.py` | Philibert, l'iguane : temps qui passe, jauges, santé, vétérinaire, évolution, boutique, mini-jeux (règles : `docs\PHILIBERT.md`) |
| `static\js\philibert*.js`, `static\philibert.css` | Philibert en haut de la page, son dessin, son île et ses mini-jeux |
| `profiles.py` | Profils visuels : lecture du dossier `profils\`, vérification et nettoyage du CSS, import et export .zip |
| `valider_profil.py` | Vérifie un dossier ou un .zip de profil et explique les erreurs |
| `profils\` | Les profils visuels ; `FORMAT.md` (le format), `_modele\` (modèle à copier) |
| `config.example.json`, `deck.example.json` | Modèles sans aucune donnée réelle |
| `outils\LibreHardwareMonitor.config` | Réglages copiés dans LibreHardwareMonitor (serveur web local, port 8085) |

### `config.json` (créé par l'assistant)

- `discord` : `enabled`, `user_id`, `alert_channel_id`. Le jeton du bot est rangé dans le gestionnaire
  d'identifiants de Windows au démarrage (`token_windows: true` dans `config.json`, `token` vide) ; si le
  gestionnaire est indisponible, il reste dans `token`.
- `alerts` : seuils des alertes Discord — `cpu_temp`, `gpu_temp` (°C), `ram_percent`, `disk_percent` (%),
  `cooldown_minutes` (une alerte par type au plus toutes les X minutes), `check_seconds`.
- `agenda` : `rappels_minutes` (délais des rappels par défaut, en minutes), `heure_reference` (heure des
  rappels pour les évènements sans heure et les anniversaires), `rappels_discord` (`true` / `false`).
- `deck` : `password_hash` (empreinte PBKDF2 du mot de passe : le mot de passe lui-même n'est jamais
  enregistré), `rate_limit_per_minute`.
- `google_agenda` (réglé dans ⚙ Réglages → Google Agenda) : `client_id`, `agenda` (`primary` = agenda
  principal), `cible` (`google` / `nexus` : où vont les nouveaux évènements), `rappels`, `intervalle_minutes`.
  Le code secret du client et le jeton de Google sont dans le gestionnaire d'identifiants de Windows
  (`client_secret` / `jeton` seulement s'il est indisponible).

Sans `config.json`, NEXUS démarre quand même (deck et bot désactivés) et l'indique dans la fenêtre noire.

### Stream deck (onglet « Deck »)

Boutons dans `deck.json` (créé à partir de `deck.example.json`), modifiables dans l'onglet Deck
(**✎ Modifier**). Types d'actions en liste fermée :

| Type | Paramètres |
|---|---|
| `app` | `path` : chemin complet d'un `.exe`, `.lnk` ou `.url` ; `args` : liste optionnelle |
| `url` | `url` : adresse `http(s)://` |
| `media` | `key` : `play_pause`, `next`, `prev`, `volume_up`, `volume_down`, `mute` |
| `lock` | aucun (verrouille la session Windows) |
| `script` | `name` : fichier `.bat`, `.cmd`, `.ps1` ou `.py` du dossier `actions\` |
| `power` | `op` : `shutdown`, `restart` (après 15 s), `sleep` — confirmation obligatoire |

Le navigateur n'envoie que l'identifiant du bouton ; l'action est lue dans `deck.json`, vérifiée, et
chaque exécution est notée dans `logs\deck.log`.

### Accès depuis le téléphone

Désactivé par défaut. Bouton **📱 Téléphone** sur le PC → autoriser → scanner le QR code avec le
téléphone (même Wi-Fi).

- **Version source** : Windows demande d'autoriser Python sur les **réseaux privés** : accepte (une fois de plus
  après le passage au Python privé de NEXUS : c'est un autre `python.exe`, celui de `runtime\`).
- **Application Windows et portable** : si le pare-feu bloque, la fenêtre 📱 Téléphone l'indique et propose
  **Autoriser dans le pare-feu** (confirmation administrateur Windows). La règle porte sur le port de NEXUS
  (8765 par défaut), pas sur un programme : elle reste valable si le dossier portable est déplacé.
- L'adresse change d'une version à l'autre (source : port 8000, application/portable : 8765) : un téléphone
  appairé sur une version doit être appairé à nouveau sur l'autre.

- **Appli Android** (sans navigateur, plein écran) : `android\` construit `NEXUS-Android-x.y.z.apk` (≈ 50 Ko,
  seule permission : Internet). Installation et construction : `android\LISEZMOI.md`.

Seuls les appareils appairés passent ; les adresses Internet sont toujours refusées. Chaque nouvel appairage
s'affiche en **notification sur le PC** (et sur Discord si le bot est configuré) : si ce n'est pas toi,
📱 Téléphone → **Révoquer**. Un appareil qui ne s'est **pas connecté depuis 90 jours est oublié tout seul** (vieux
téléphone vendu ou perdu) : il suffit de l'appairer à nouveau. Les deux sont notés dans le journal d'activité.

### Autres réglages

- Seuils du bandeau d'alerte de la page : dictionnaire `ALERTS` en haut de `stats.py`.
- Port de NEXUS (8000) : `PORT` en haut de `app.py`. Port de LibreHardwareMonitor (8085) : `LHM_URL`
  dans `stats.py` et `outils\LibreHardwareMonitor.config`.
- Mode jeu : détection automatique des jeux, panel allégé pendant les parties ; option de changement
  de plan d'alimentation (désactivée par défaut) dans l'onglet PC. Carte « Mode jeu » : **⏸ Désactiver le
  mode jeu** (le panel ne s'allège plus ; la détection continue pour les statistiques, retenu au
  redémarrage) / **▶ Réactiver** ; **✖ Ce n'est pas un jeu** met le programme détecté dans les exceptions.
  Les surcouches (Epic EOSOverlayRenderer, Steam, NVIDIA…) ne sont jamais prises pour des jeux.
- Versions : bouton **vX.Y.Z** en haut (notes de version), sauvegarde automatique dans `versions\`,
  retour arrière avec `restaurer_version.bat` (les 8 versions les plus récentes sont gardées ; les sauvegardes
  faites avant une mise à jour en ligne, dans `sauvegardes-maj\`, sont gardées par 3). Mises à jour en ligne : voir « Mises à jour ».
- Tiers : polices et bibliothèques, voir `THIRD_PARTY.md`.

## Licence

NEXUS est distribué sous licence **MIT** (voir `LICENSE`) : libre d'utilisation, de modification et de
partage. LibreHardwareMonitor et les bibliothèques Python ont leurs propres licences.
