# Changelog

Toutes les évolutions notables de NEXUS sont notées ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et la numérotation
[Semantic Versioning](https://semver.org/lang/fr/) : **majeur.mineur.correctif**. Le fichier `VERSION`, à la
racine, est la source de vérité ; `outils/release.py` le fait avancer et complète ce journal.

## [Non publié]

## [1.14.1] - 2026-11-28

### Ajouté
- **Google Agenda : tes évènements NEXUS y partent tout seuls** (⚙ Réglages → Google Agenda, case cochée par
  défaut) : à la liaison puis à chaque relecture, les évènements encore enregistrés dans NEXUS (anniversaires
  compris) sont créés dans l'agenda Google relié, avec heure, durée, répétition (dates annulées ou modifiées
  comprises), rappels et note, puis retirés de NEXUS. Jamais de doublon, même si l'envoi est interrompu ; en cas
  de refus ou de coupure, l'évènement reste dans NEXUS et repart à la relecture suivante (erreur affichée sous le
  calendrier). Le choix « NEXUS (sur ce PC seulement) » du formulaire garde un évènement sur le PC. Résultat
  annoncé : « 12 évènements NEXUS envoyés dans Google Agenda »

### Corrigé
- **Google Agenda, rappels des journées entières** : « 1 jour avant » tombait à minuit chez Google au lieu de 9 h
  (heure de référence de NEXUS) ; les rappels sont maintenant convertis dans les deux sens

## [1.14.0] - 2026-11-28

### Ajouté
- **Agenda relié à Google Agenda, dans les deux sens** (⚙ Réglages → Google Agenda) : les évènements de ton
  Google Agenda s'affichent dans l'Agenda (pastille **G**, lien vers Google), et tu peux en créer, modifier (cette
  occurrence, les suivantes, toute la série) et supprimer depuis NEXUS ; seuls les champs changés sont envoyés
  (invités, lieu, visio gardés). Relecture toutes les 10 minutes (réglable) ou avec **⟳ Relire** ; copie locale
  pour l'affichage hors connexion et les rappels de NEXUS (bannière, Discord). Invitations et anniversaires des
  contacts en lecture seule ; répétitions plus riches de Google gardées telles quelles. Connexion OAuth avec ton
  propre identifiant client (guide : `docs/GOOGLE_AGENDA.md`) ; code secret et jeton dans le gestionnaire
  d'identifiants de Windows, réglages modifiables depuis le PC seulement

### Corrigé
- **Média, ⏯** : le bouton bascule tout de suite et ne fait plus d'aller-retour (❚❚ → ▶ → ❚❚) pendant que
  l'application (Spotify…) met quelques centaines de millisecondes à suivre ; l'état demandé est gardé jusqu'à ce
  que l'application le confirme (2,5 s au plus)
- **Média, volume de la source** : quand Spotify (ou une autre appli) refait du son, son curseur de volume revient
  dès que Windows le liste dans le mélangeur (environ 1 s) au lieu de rester plusieurs secondes sur « l'appli
  n'apparaît pas encore dans le mélangeur » ; message plus clair en attendant

## [1.13.0] - 2026-11-26

### Ajouté
- **Accès téléphone** : chaque nouvel appairage est signalé par une notification sur le PC (et sur Discord si le
  bot est configuré), avec le nom et l'adresse de l'appareil, pour le révoquer tout de suite si ce n'est pas toi.
  Un appareil qui ne s'est pas connecté depuis 90 jours est oublié tout seul (son ancien jeton est refusé) ; les
  deux sont notés dans le journal d'activité

## [1.12.1] - 2026-11-26

### Corrigé
- **Microsoft Defender mettait NEXUS 1.12.0 en quarantaine** (« Trojan:Win32/Bearfoos.A!ml », fausse alerte par
  apprentissage automatique sur ce fichier précis) : NEXUS se fermait d'un coup, puis ne s'ouvrait plus, raccourcis
  supprimés. Même code, exe reconstruit et vérifié par Defender. Si NEXUS ne s'ouvre plus chez toi : lance
  `NEXUS-1.12.1-Setup.exe`, tes données sont gardées (exe, raccourcis et entrée de désinstallation reviennent)
- Publication : Microsoft Defender analyse l'exe, l'installeur et le portable avant l'envoi ; rien n'est publié si
  l'un d'eux est détecté

## [1.12.0] - 2026-11-26

### Ajouté
- **Importer mes données NEXUS** (menu Démarrer, ou `NEXUS.exe --importer`) : une fenêtre trouve les autres NEXUS
  du PC (portable, version ZIP avec `lancer.bat`, ancienne version, sur les disques et les clés USB), montre ce
  qu'ils contiennent et quand ils ont servi, puis reprend leurs données dans ce NEXUS : configuration, agenda,
  journal, statistiques, Philibert, souvenirs, rappels, téléphones appairés, Deck, actions, profils ajoutés. Marche
  aussi quand l'application a déjà servi : ses données sont remplacées après une copie dans `sauvegardes-import\`,
  remise en place si la copie échoue. L'autre NEXUS n'est jamais modifié ; les NEXUS ouverts sont détectés et
  fermés sur demande (base copiée de façon cohérente, journal WAL compris)

## [1.11.0] - 2026-11-26

### Ajouté
- **⚙ Réglages → Démarrage de Windows** (sur le PC) : une case **Lancer NEXUS au démarrage de Windows** (icône près de
  l'horloge, sans fenêtre ni navigateur ; toutes les versions, portable comprise) et une case **Démarrer
  LibreHardwareMonitor sans la fenêtre d'autorisation** : Windows demande ton accord une seule fois, puis
  LibreHardwareMonitor est copié dans `Program Files` (modifiable seulement par un administrateur) et lancé par une
  tâche planifiée pour ton compte, sans plus aucune fenêtre ; décocher retire tout. Réglages notés dans le journal
  d'activité (catégorie « Démarrage de Windows »)

## [1.10.2] - 2026-11-25

### Modifié
- **Installeur Windows aux couleurs de NEXUS** : fenêtre sombre, page d'accueil et page de fin illustrées (logo
  hexagonal, dégradé cyan → magenta, petite courbe d'activité), logo en haut des autres pages, fond discret en nids
  d'abeille ; images nettes à tous les zooms de Windows (`outils/images_installeur.py`) ; textes de l'assistant
  plus chaleureux et au tutoiement, comme dans NEXUS

## [1.10.1] - 2026-11-25

### Ajouté
- Fenêtre **Version** : une ligne **« Type d'installation »** (Application Windows, Portable ou Version source)
  en tête des mises à jour, pour savoir d'un coup d'œil quelle version de NEXUS est ouverte et comment elle se met
  à jour

## [1.10.0] - 2026-11-25

### Ajouté
- **Installeur** : LibreHardwareMonitor livré en option cochée (températures du processeur, des disques et
  ventilateurs ; version 0.9.6 officielle, empreinte vérifiée) ; à la désinstallation, choix de **garder** (par
  défaut) ou **supprimer** ses données, jeton du bot compris. Le ZIP portable livre aussi LibreHardwareMonitor
- **Reprise d'une ancienne version source** (dossier avec `lancer.bat`) : au premier lancement de l'application
  installée, ses données sont copiées (configuration, base, photos, Philibert, actions, profils), l'ancien dossier
  n'est jamais modifié ; `NEXUS.exe --importer <dossier>` pour un dossier donné
- Le **jeton du bot Discord** est rangé dans le gestionnaire d'identifiants de Windows (plus en clair dans
  `config.json`)
- `outils/build.py` : tout construire d'une commande (lint, tests, audit, exe, installeur, portable, SHA256) ;
  la CI publie l'installeur et le portable à chaque tag s'ils manquent

### Corrigé
- **Deck** : un mot de passe changé avec « Configurer NEXUS » pendant que NEXUS tournait n'était pris en compte
  qu'au redémarrage (l'ancien restait accepté, les sessions ouvertes aussi) : `config.json` est relu dès qu'il
  change et les sessions sont révoquées
- `config.json` (ou `deck.json`) enregistré en « UTF-8 avec BOM » (Bloc-notes, PowerShell) était déclaré
  illisible : NEXUS repartait sur les valeurs par défaut (Deck désactivé)
- Installeur : textes accentués abîmés dans l'assistant (« CrÃ©er un raccourci ») ; la désinstallation fermait
  aussi un NEXUS portable ouvert ; installer par-dessus un NEXUS ouvert s'arrêtait
- Points d'accès sans corps (vérifier les mises à jour, etc.) : JSON obligatoire, comme les autres, pour qu'un
  autre site ouvert dans le navigateur ne puisse pas les déclencher (version source)
- Les erreurs des boucles de fond (relevé des processus, mode jeu) sont écrites dans le journal au lieu d'être
  ignorées en silence

### Modifié
- Code reformaté (ruff format) et lint élargi ; fins de ligne uniformisées ; tests des parties critiques
  (configuration, base et migrations, authentification, profils, statistiques, migration des données)
- Retirés : le kit de personnalisation 1.6.0 (patch de 243 Ko et documents, désormais intégrés) et du code mort

## [1.9.2] - 2026-11-25

### Corrigé
- Mises à jour : la vérification de la signature de l'installeur (et le script de mise à jour) ne tombe plus en panne quand NEXUS est lancé depuis PowerShell 7 : Windows PowerShell n'hérite plus d'un chemin de modules qu'il ne sait pas charger (c'est ce qui faisait échouer la CI de GitHub depuis le 19/11)

## [1.9.1] - 2026-11-25

### Corrigé
- Philibert : la saison en haut de l'île ne reste plus **bloquée sur « Saison des pluies »** (elle suivait les mois réels, de septembre à novembre) : les quatre saisons de l'année de l'île (printemps, été, saison des pluies, saison fraîche) se suivent maintenant dans l'ordre, 3 à 6 jours chacune ; les saisons spéciales de l'île continuent de s'y ajouter

## [1.9.0] - 2026-11-24

### Ajouté
- **La version portable se met à jour toute seule**, comme l'application Windows : une nouvelle version allume la
  pastille de version, **Installer** (mot de passe du panel puis validation) télécharge `NEXUS-Portable-x.y.z.zip`
  (pré-release « version portable »), vérifie son empreinte SHA256 et son contenu (bonne version, aucun fichier de
  données, aucun chemin dangereux), sauvegarde `NEXUS.exe` et `_internal\` dans `maj\rollback\`, ferme NEXUS,
  remplace seulement les fichiers du programme et le relance. Tes données (`config.json`, `data\`, `profils\`…),
  LibreHardwareMonitor et tes propres dossiers à côté ne sont jamais touchés. Si la nouvelle version ne démarre pas,
  l'ancienne revient toute seule ; **↶ Revenir à la version précédente** marche aussi. Le dossier du portable doit
  être modifiable (sinon NEXUS l'indique et la mise à jour reste manuelle) ; un portable antérieur se met à jour une
  dernière fois à la main

### Corrigé
- Mises à jour de l'application Windows : seul le NEXUS du dossier mis à jour est fermé (un autre NEXUS, portable par
  exemple, n'est plus arrêté) ; un retour en arrière ne supprime jamais `config.json`, `data\`, `profils\`… ; messages
  accentués du résultat corrects (script en UTF-8 avec BOM pour PowerShell 5.1)

## [1.8.0] - 2026-11-23

### Ajouté
- **Mode repos** : quand NEXUS n'est plus au premier plan depuis 20 s (autre fenêtre active, NEXUS sur un second écran), les animations décoratives se mettent en pause (Philibert, éclats, balayages) ; les valeurs, alertes et notifications continuent. Retour immédiat au focus ou au passage de la souris. Réglable dans ⚙ Réglages → Économie. Mesuré sur un écran 165 Hz : affichage + carte graphique de 30 % à 1,2 % d'un cœur
- **Animations limitées à 60 images/s** (js/fps60.js) : sur un écran 144/165 Hz, les animations en boucle (Philibert, voyants, balayage, glitch) avancent 60 fois par seconde au lieu de suivre l'écran ; même mouvement, recalculs de style de 170 à environ 70 par seconde, travail de la fenêtre environ divisé par deux. Réglable dans ⚙ Réglages → Économie
- **Application Windows** : installeur `NEXUS-x.y.z-Setup.exe` avec mises à jour automatiques (dépôt embarqué dans l'exe) ; `release.py` le publie à chaque version, le portable dans une pré-release à part
- **Demi-écran** : onglet PC en cases 2 par 2, en-tête compact, onglets sur une ligne

### Corrigé
- Philibert : le bouton **« Le faire revenir »** (Philibert en pension chez la voisine) répond de nouveau : le calque
  invisible des crottes, posé sur toute la scène de l'île, captait le clic à sa place (seules les crottes le captent
  maintenant)
- Application Windows et portable : LibreHardwareMonitor (dossier `LibreHardwareMonitor` à côté de `NEXUS.exe`) est maintenant démarré au lancement, comme en version source ; avant, la version exe ne profitait que d'un LibreHardwareMonitor déjà lancé ailleurs
- Fenêtre native : activer ou couper l'accès téléphone ne ferme plus NEXUS ; le pare-feu Windows (NEXUS.exe ≠ Python) est détecté et une règle par port est proposée

### Modifié
- Balayage de l'en-tête limité à 30 images/s (il repeignait toute la barre à chaque image d'un écran 144/165 Hz)
- Exe plus léger : décodeur AVIF de Pillow retiré (inutilisé, les souvenirs acceptent JPEG/PNG/WebP) ; portable 39,6 → 35,5 Mo

### Personnalisation native et portable
- Portée sur NEXUS 1.6.0 (Python privé, superviseur d'arrière-plan, profil « Averse de néons »)
- Lancement : les dépendances ne sont plus réinstallées à chaque démarrage ; elles ne sont vérifiées que si `requirements.txt` a changé (marque `runtime\requirements.installe` ou `.venv\.requirements.sha256`)
- Données : nouveau module `paths.py` ; en version installée, les données vont dans `%LOCALAPPDATA%\NEXUS` (config, `data\`, `logs\`, `actions\`, profils personnels), les ressources restent en lecture seule. Migration automatique de l'ancien dossier au premier lancement, sans écrasement ; mode portable avec `NEXUS_DATA_DIR` ou `NEXUS_PORTABLE=1`
- Journal : les messages et erreurs sont aussi écrits dans `logs\nexus.log` (rotation à 5 Mo), utile sans console
- Réseau local : port configurable par `NEXUS_PORT` (0 = port libre), jeton local `NEXUS_TOKEN` pour les requêtes loopback en version installée, instance unique par session Windows
- Sécurité : en-têtes `X-Frame-Options`, `X-Content-Type-Options` et `Referrer-Policy` sur les réponses ; limite de taille des corps JSON ; révocation des sessions du deck quand le mot de passe change
- Fenêtre native (Phase 1) : `nexus_launcher.py` (pywebview/WebView2), icône dans la zone de notification (pystray), fermeture dans le tray, instance unique avec activation de la fenêtre existante, toasts Windows (winotify), démarrage automatique optionnel, `lancer_native.bat` et `requirements-native.txt`
- Notifications : les rappels, alertes CPU/RAM/disque et évènements de Philibert passent par les toasts Windows en mode natif ; le navigateur garde ses notifications en mode web
- Exécutable autonome (Phase 2) : `nexus.spec` + `outils/build_native.py` (PyInstaller onedir, icône, version, données) ; `requirements-native.txt` contient PyInstaller
- Installeur Windows : `installer.iss` (Inno Setup 6), installation par utilisateur dans `%LOCALAPPDATA%\Programs\NEXUS`, raccourcis NEXUS / Configurer NEXUS / Désinstaller, vérification WebView2, désinstallation qui conserve `%LOCALAPPDATA%\NEXUS`
- Premier lancement : fenêtre de configuration native (mot de passe, Discord, dépôt des mises à jour), sans console ; raccourci « Configurer NEXUS » (`NEXUS.exe --configure`)
- Signature : `outils/sign_native.ps1` pour signer l'exe et l'installeur avec un certificat Authenticode (signtool)
- Mises à jour natives (Phase 3) : en version installée, NEXUS télécharge `NEXUS-x.y.z-Setup.exe`, vérifie le SHA256 et la signature Authenticode, sauvegarde l'installation, puis un helper PowerShell ferme NEXUS, installe en silence et relance
- Rollback natif : si la nouvelle version ne confirme pas son démarrage, l'ancienne installation est restaurée et relancée ; « Revenir à la version précédente » utilise la même sauvegarde
- Signature configurable : `mises_a_jour.signature` (`auto`, `requise`, `ignoree`) et `mises_a_jour.certificat` (empreinte SHA1 attendue)
- Build : `outils/build_native.py` signe l'exe avant l'installeur et écrit `*.sha256` + `SHA256SUMS.txt` ; CI Windows sur tag `v*` (artefacts, sans publication automatique) et documentation du fork (`docs/GITHUB-FORK.md`)
- Version portable : `outils/build_native.py --portable` produit `NEXUS-Portable-x.y.z.zip` (exe, `_internal`, `portable.flag`, `Lancer NEXUS.bat`, `LISEZMOI.txt`) ; le drapeau `portable.flag` place les données dans le dossier de l'exe, désactive le démarrage automatique et donne un mutex d'instance unique propre au dossier ; mise à jour manuelle, sans installeur
- Adaptation des futures versions : kit de personnalisation (retiré en 1.9.3, désormais intégré au dépôt)

### Corrigé
- Tests : `test_modejeu.py` n'utilise plus `StopIteration` dans une génératrice (interdit depuis Python 3.7) ; `run_all.py` ignore proprement `test_maj.py` hors dépôt Git

## [1.7.0] - 2026-11-18

### Modifié
- Philibert, **« Gauche ou droite ? »** : partie courte de **5 manches avec 3 vies** (chaque erreur en coûte une), **sans aucun indice** sur le côté où il va tourner la tête ; le but est la partie parfaite (5 sur 5 sans perdre de vie), qui rapporte le plus : 15 coquillages, puis 8, 4 selon les vies perdues ; succès « Devin de l'île » et marque « Yeux rubis » liés aux parties parfaites

## [1.6.0] - 2026-11-18 - Averse de néons

### Ajouté
- **Téléchargement plus simple** : chaque release GitHub commence par un encadré « Télécharger » avec le lien
  direct vers l'archive et l'installation en trois étapes
- **Profil visuel « Averse de néons »** (v1.2, modes Terminal et Sentinelle) : une ville de nuit sous la pluie. Fond :
  une rue-canyon en perspective centrale serrée d'enseignes (tubes de néon, caissons lumineux à signes inventés,
  enseignes de boutiques), câbles tendus au-dessus de la rue, carpe holographique translucide, brume éclairée par les
  enseignes, vapeur qui monte de la chaussée, passants sous des parapluies, trottoirs et passage piéton, méga-tour à
  écran géant qui se perd dans une brume bleu-violet, reflets étirés et ronds de pluie dans les flaques (violet et
  magenta en Terminal, bleu, cyan et ambre en Sentinelle), pluie en deux plans qui tombe en biais (fine au loin, plus
  longue et plus rapide au premier plan, aussi sur téléphone), deux groupes d'enseignes qui scintillent ; cartes en verre fumé à liseré néon, jauges et barres
  en tubes de néon (couleur selon le niveau, tube rouge qui grésille en critique), alertes en enseignes lumineuses.
  Page de garde : on lève les yeux entre les tours sous la pluie, les enseignes s'allument dans le flou, la mise au
  point se fait, des projecteurs balaient la brume et le logo NEXUS s'allume comme un néon ; au clic, on s'envole
  entre les tours et la scène s'ouvre en rond, bordée d'un anneau néon. Dessins originaux rendus une fois en WebP,
  version portrait allégée pour le téléphone, versions fixes sans animation et en mode jeu, contraste du texte
  d'au moins 4,5:1 sur toutes les vues

## [1.5.0] - 2026-11-18

### Ajouté
- **NEXUS autonome sur Windows** : il apporte son propre Python (dossier `runtime\`, Python 3.12 officiel de la
  Python Software Foundation, téléchargé une seule fois depuis nuget.org avec vérification de l'empreinte SHA256)
  et ne dépend plus du Python installé sur le PC : une mise à jour, un changement de version ou une désinstallation
  de ce dernier ne casse plus NEXUS. Plus besoin d'installer Python avant NEXUS. Le Python privé est isolé (ni
  paquets « utilisateur », ni `PYTHONPATH` de Windows) ; un nouveau Python privé n'est installé qu'une fois prêt et
  testé, et l'ancienne installation `.venv` reste utilisable en secours
- **Icône près de l'horloge, sans fenêtre noire** : NEXUS tourne en arrière-plan ; clic = ouvrir NEXUS, clic droit
  = Redémarrer NEXUS, Ouvrir le journal (`logs\nexus.log`), Quitter NEXUS ; état au survol (en marche, mise à jour
  en cours…) ; notification si le serveur ne peut pas démarrer (port déjà pris, 5 plantages d'affilée) ; une seule
  icône à la fois (un 2ᵉ lancement ouvre simplement le panel). Elle fait tout ce que faisait la fenêtre noire :
  première configuration, dépendances (seulement quand `requirements.txt` change : démarrage plus rapide),
  LibreHardwareMonitor, mises à jour préparées depuis le panel, relance après un plantage
- `lancer.bat console` : l'ancienne fenêtre noire, pour dépanner

### Modifié
- Installations existantes : au premier lancement après la mise à jour, `lancer.bat` installe le Python privé (une
  fenêtre s'ouvre, 1 à 3 minutes, Internet nécessaire), puis NEXUS démarre avec son icône. Le raccourci du Bureau
  créé par `installer.bat` ouvre désormais l'icône directement. Avec l'accès téléphone, Windows redemande une fois
  l'autorisation « réseaux privés » (nouveau `python.exe`)
- Une mise à jour appliquée depuis une ancienne fenêtre noire continue sans accroc avec le nouveau `lancer.bat`

### Modifié
- Profil **Dés du destin 3.0** : visuels entièrement refaits, plus riches et plus nets (tous rendus une fois, dessins originaux, rendu 3D procédural)
  - **Table du Maître du donjon** en 4K : chêne veiné à la lueur d'une bougie, carte de donjon dessinée à l'encre sur parchemin, sceau de cire, pièces d'or en relief et vrais dés polyédriques (d4, d6, d8, d10, d12, d20) en **résine rubis translucide** aux chiffres d'or gravés, faces opposées justes (n + 1) ; image allégée sur téléphone
  - **Cartes en cuir de grimoire** avec équerres de laiton ciselé aux coins, couture et filet d'or ; boutons en jetons laqués cerclés d'or, onglet actif en sceau de cire, icônes du sommaire en sceaux, lecture en pièce d'or ; menus et dialogues assortis ; post-it en tons de parchemin
  - **Jauges en traits de feu** redessinées : cœur blanc, halo, langues de flamme et étincelles, tête embrasée
  - **Alertes plus lisibles** : plaque sombre et étiquette contrastée ; un 20 doré quand tout est résolu, un 1 rouge sur un dé d'obsidienne qui tremble pour une alerte critique
  - **Nouvelle intro** : une bougie s'allume, la lumière gagne la table, un d20 est lancé, rebondit et roule en vraie 3D (60 images, flou de mouvement, éclairage qui suit, ombre portée) puis s'arrête sur 20 dans un éclat d'or ; anneau de runes en or gravé autour du logo
  - Version fixe complète sans animation (`prefers-reduced-motion`) et en mode jeu ; profil plus léger (1,2 Mo au lieu de 1,8 Mo)

## [1.4.1] - 2026-11-17

### Modifié
- Philibert : **pluie plus naturelle** : une vraie averse enregistrée en plein air au bord de l'océan (CC0, « Outdoor Rain with Distant Ocean » de Jeff Final Boss), bouclée sans couture ; le tonnerre ne change pas

### Corrigé
- Philibert : si le serveur NEXUS date d'avant les réglages de volume, le curseur ne revient plus à 60 % en silence : le volume s'applique et un message demande de redémarrer NEXUS pour l'enregistrer

## [1.4.0] - 2026-11-17

### Ajouté
- Philibert : **volumes réglables** : un curseur pour les bruits de l'île et un pour les petits sons et les mini-jeux (Réglages), plus un petit curseur dans l'en-tête de chaque mini-jeu ; le changement s'entend tout de suite
- Philibert : **bain animé** (il marche jusqu'à l'eau, y entre en éclaboussant, nage à moitié immergé en ondulant de la queue avec des ronds à la surface, puis ressort et s'ébroue) et **montée dans le palmier** le soir (il grimpe le long du tronc jusqu'à sa palme ; il redescend la tête la première le matin)

### Modifié
- Philibert : **pluie et orage réalistes** : de vrais enregistrements libres de droit (CC0, OpenGameArt) remplacent les sons synthétisés ; averse en boucle, vrais coups de tonnerre qui roulent, plus fréquents pendant la saison des tempêtes

### Corrigé
- Philibert : allumer ou éteindre la lanterne ou la lampe chauffante ne fait plus repartir de zéro les animations de l'île (vagues, crabes, oiseaux, nuages)

## [1.3.0] - 2026-11-17

### Ajouté
- Philibert : **marques**, de nouvelles mutations qui s'ajoutent à la couleur du corps, une par partie du corps : fanon (orangé, rouge, bleu, rayé), crête (orangée, bicolore), queue annelée, yeux (rubis, azur), motif de la peau (moucheté, rayé, dégradé) ; elles apparaissent à une mue selon sa vie, avec une rareté (commune, rare, très rare), se voient partout et dans l'album, et ont leur section dans l'onglet « Couleurs » du carnet ; succès « Un iguane unique »
- Philibert : un **crabe violoniste** (carapace bleu-vert, énorme pince orange qu'il agite pour faire signe) et un **goéland qui se pose** sur la plage, marche, regarde autour de lui, picore le sable et repart

### Modifié
- Philibert : **goélands redessinés** d'après des photos et des vidéos de goélands argentés (bec jaune à tache rouge, œil cerclé d'orange, manteau gris, bouts d'ailes noirs à miroirs blancs, pattes roses) avec un vrai cycle de battement (main de l'aile repliée au poignet en remontant, aile étendue en descendant) et un plané qui s'ajuste au vent
- Philibert : **crabes fantômes redessinés** (carapace granuleuse, longs pédoncules, pattes articulées) : ils courent de côté pattes en alternance, s'arrêtent net, dressent les yeux, agitent la pince et s'enfouissent dans le sable en laissant dépasser les yeux
- Philibert : la saison de l'île en cours s'affiche **sans durée ni compte à rebours** (en-tête de l'île et partout ailleurs) : on voit quelle saison il fait, sa fin reste une surprise

## [1.2.0] - 2026-11-17

### Ajouté
- Philibert : **saisons de l'île en roulement**, en plus des saisons du calendrier (printemps, été, saison des pluies, saison fraîche, qui restent la base de la météo, du décor et des produits de saison) : chaque île a son roulement de périodes de 2 à 7 jours au hasard, parfois du temps ordinaire ; **4 saisons de l'île** (grande floraison, saison des tempêtes, saison des brumes, ponte des tortues) qui s'ajoutent à la saison du calendrier (un peu plus ou moins de pluie, de nuages et de chaleur, un 2ᵉ produit de saison, leur décor) ; l'en-tête montre les deux saisons et combien de temps il reste à celle de l'île ; succès « Saisons de l'île »
- Philibert : **sieste sur le rocher chaud** (fatigué au soleil, il s'y endort et se réchauffe ; « Chauffer » pendant une sieste le pose sur le rocher sans le réveiller) et petits **« z z Z »** au-dessus de lui quand il dort
- Philibert : **mutations de couleur** à la mue, selon sa vie (alimentation, soleil, bains, jeux, froid, maladies soignées trop tard, nuits réveillées…) : Émeraude, Orangé, Doré, Turquoise, Mélanique, Cendré, Arlequin, Lunaire et le très rare Leucique, en trois intensités ; onglet « Couleurs » dans le carnet, succès « Couleurs uniques »

### Modifié
- Philibert, mini-jeux : **difficulté qui monte pendant la partie** et **palier affiché** dans chaque jeu ; parties plus longues (une bonne partie dure 2 à 3 minutes) qui finissent toutes seules en cas d'échec (vies, erreurs) ; **Pluie de feuilles** : un palier toutes les 20 s (plus vite, plus de feuilles, plus d'insectes), 5 vies, 3 min au plus ; **Course au rocher chaud** : 10 étapes de plus en plus rapides, obstacles plus serrés, 3 vies, barre de progression par étape ; **Gauche ou droite ?** : 20 manches, un coup d'œil de Philibert trahit souvent le côté, de plus en plus bref, fin à la 3ᵉ erreur
- Philibert : « Le hochement » s'appelle désormais **« En rythme »** : suites de 3 à 14 gestes, hochements de tête ET fanon de plus en plus rapides à chaque manche, à reproduire en entier
- Philibert : **récompenses des jeux selon le palier atteint et la durée** (jusqu'à 20–30 coquillages par bonne partie), plafond journalier des jeux porté à **120 coquillages** ; anti-triche renforcé : un score, un palier ou une distance impossibles pour la durée réelle de la partie sont refusés (partie close, rien gagné)
- Philibert : crabes et goélands redessinés et animés (le crabe file de côté par à-coups, s'arrête, redresse les yeux et agite la pince ; le goéland bat des ailes coudées au poignet puis plane) ; yeux un peu plus grands et plus brillants, tête du bébé plus ronde

## [1.1.1] - 2026-11-17

### Corrigé
- Journal verrouillé : l'écran « Journal verrouillé » ne saute plus en bas à gauche, et il n'écrase plus la disposition du Journal ; une fois déverrouillé, la carte du jour (humeurs) et la vue mois restent à leur place (une disposition déjà abîmée par ce défaut est remise à l'origine automatiquement)
- Disposition des blocs : un tableau reconstruit (page qui change de contenu) ne fait plus oublier la place des autres blocs enregistrés

## [1.1.0] - 2026-11-16 - Philibert arrive !

**Philibert arrive !** Un petit iguane vert vient vivre dans NEXUS. Il se promène sous la barre du haut et, d'un clic,
t'emmène sur son île tropicale : nourris-le de verdure, réchauffe-le au soleil (c'est un lézard à sang froid), joue
avec lui, décore son île et regarde-le grandir, de l'œuf au vieux sage. Il ne meurt jamais : s'il est malade trop
longtemps, une tortue vétérinaire prend soin de lui. Tout est dessiné d'après nature, et ses données restent sur ton PC.

### Ajouté
- **Philibert dans la barre du haut** : il marche dans un couloir à lui (sans jamais recouvrir un bouton ; seul son corps est cliquable), toujours tourné vers là où il va, s'arrête, regarde autour de lui, cligne des yeux, hoche la tête, agite son fanon, se dore au soleil et dort la nuit ; sa bulle montre son humeur (cœur, « ! » s'il a besoin de toi, Zzz, nuage s'il est malade)
- **Son île** (clic sur lui, la tuile du sommaire, ou ⚙ Réglages → Ouvrir son île) : ciel à l'heure réelle (aube, jour, coucher, nuit étoilée avec la lune à sa vraie phase), météo de l'île (nuages, pluie, arc-en-ciel), lagon, cocotier où il dort, rocher chaud, flaque, crabes, oiseaux, papillons, lucioles ; jauges (faim, bonheur, énergie, propreté, santé, chaleur), poids, âge et « ce qui ne va pas »
- **Soins** : nourrir (100 % végétal : verdure, légumes, fleurs ; fruits en friandises à limiter ; insectes, viande et croquettes refusés avec une explication), chauffer au soleil ou sous une lampe chauffante, éteindre la lumière la nuit, bain tiède ou de mer, nettoyer, soigner, caresser, féliciter, gronder doucement (caprices et vrais besoins)
- **Il ne meurt jamais** : malade trop longtemps, la tortue vétérinaire l'emmène se reposer 12 à 24 h (jauges figées) et il revient avec une carte postale qui explique ce qui lui a manqué ; pension chez la voisine pendant les longues absences ; mode vacances
- **Il grandit** : œuf → bébé → juvénile → adulte → vieux sage, avec une variante selon les soins reçus (l'Insulaire, le Royal, le Gourmand, le Nageur, le Convalescent) ; mues et évènements de l'île
- **Saisons de l'île** selon le mois réel (printemps, été, saison des pluies, saison fraîche) : météo, chaleur, décor et produit de saison moins cher
- **Quatre mini-jeux** qui rapportent des coquillages : Pluie de feuilles (la souris reste dans le cadre pendant la partie), Course au rocher chaud, Gauche ou droite ?, En rythme (petit et grand hochements et fanon, une nouvelle suite au hasard à chaque manche, de plus en plus vite) ; une partie se lance pour 8 d'énergie et peut être **abandonnée** (sans gain, l'énergie dépensée ne revient pas)
- **Boutique** : nourriture, remède, lampe chauffante, 15 accessoires (tête, yeux, cou) et 9 décorations, dont des pièces **rares**, **très rares** et **légendaires** faites à la main par les artisans de l'île voisine (tricorne de pirate, couronne d'or, diadème de nacre, monocle doré, collier de perles, médaille d'or, cape royale, statue tiki, petit phare, coffre au trésor, bénitier et sa perle) ; les soins essentiels restent toujours bon marché
- **Garde-robe** et **carnet** : historique, album (chaque étape de sa vie et les Philibert d'avant), statistiques, 24 succès, cartes postales, 20 fiches « Le savais-tu ? »
- **Tuile Philibert sur le sommaire** : humeur, besoin principal, âge, coquillages, et accès directs (Nourrir, Jouer, Boutique, Carnet)
- **Bruits de l'île** selon la météo, tous synthétisés et très discrets : vagues, pluie et tonnerre lointain, vent, goélands le jour, grillons et petites grenouilles la nuit ; bouton pour les couper dans l'en-tête de l'île
- **Mode sombre** de l'interface de l'île : bouton clair/sombre dans l'en-tête de l'île, et réglage automatique (selon le thème du panel et la nuit sur l'île), clair ou sombre ; contrastes vérifiés
- **Réglages** : le voir en haut ou non, vitesse du temps, sons, bruits de l'île, couleurs, notification Windows ou Discord (facultatives, jamais en mode jeu), mode vacances, nouvel œuf (double confirmation)
- **Dessin naturaliste** : un vrai iguane vert (grande écaille ronde sous l'oreille, fanon dentelé, crête d'épines, queue annelée, longs doigts griffus, texture d'écailles ; il fonce quand il a froid), cocotier annelé, cumulus, mer en perspective, reflets du soleil et de la lune, ombres qui suivent le soleil ; fenêtre de l'île grande, scène sur toute la largeur
- **Sur le PC seulement** : depuis le téléphone (accès réseau), pas d'iguane, d'île ni de tuile, et le serveur refuse ses routes (« réservé au PC »)
- **Côté serveur** (`philibert.py`, routes `/api/philibert…`) : le temps passe même NEXUS fermé, valeurs et récompenses calculées par le serveur (anti-triche), données dans `data\philibert.json` (jamais partagées) ; moments marquants dans le journal d'activité (catégorie « Philibert »)
- **Document pour l'administrateur** `docs/PHILIBERT-REGLES.md` : toutes les règles chiffrées (évolution de chaque jauge par heure, chaleur selon l'endroit, la météo et la saison, soleil ou lampe chauffante, soins, aliments, maladie, absences, croissance, mini-jeux), avec des exemples calculés par le vrai moteur
- `outils/release.py --titre "…"` : titre de la version dans l'en-tête du CHANGELOG (« ## [X.Y.Z] - date - titre », lu par le panel) et comme titre de la release GitHub (la CI le reprend aussi)

### Corrigé
- `NE_PAS_PARTAGER.md` : le nom du fichier `data\focus.json` était abîmé

## [1.0.10] - 2026-11-16

### Corrigé
- Souvenirs : le texte d'un post-it n'est plus effacé quand on change sa couleur, son écriture, sa taille ou sa police juste après avoir écrit (le texte en attente est enregistré d'abord)
- Agenda : une note ou une tâche en cours d'écriture n'est plus écrasée par le rechargement automatique (toutes les 5 min, changement de mois) ; l'éditeur écrit toujours dans la bonne note
- Journal : la zone de texte ne change plus de taille au F5 : elle s'adapte au texte du jour, et si on la redimensionne, la hauteur est retenue pour ce jour

### Modifié
- Souvenirs : la taille des post-it et des photos du mur se règle même quand la page est verrouillée

## [1.0.9] - 2026-11-15

### Ajouté
- Média, sur téléphone : boutons − et + de part et d'autre de chaque curseur de volume (carte de lecture et mélangeur) : 5 % par appui (arrondi au multiple de 5), appui maintenu pour aller vite ; « 100 % » ne se coupe plus sur deux lignes
- Mises à jour : notification « NEXUS X est disponible » sur la page de garde et en haut du sommaire, avec « Mettre à jour » (ouvre directement l'installation, curseur dans le mot de passe ; validation toujours demandée) et « Plus tard » ; la bannière flottante ne s'affiche plus que sur les autres onglets ; la page relit l'état 25 s et 1 min après son ouverture (juste après la vérification du serveur au démarrage), puis toutes les 2 min

## [1.0.8] - 2026-11-11

### Ajouté
- Classement des processus : champ de recherche (au fil de la frappe, sans majuscules ni accents, « .exe » facultatif, partie trouvée surlignée, rang d'origine gardé) ; Entrée propose de fermer le programme quand il ne reste qu'un résultat (toujours avec confirmation) ; Échap vide d'abord la recherche

### Modifié
- Thèmes par défaut (Terminal et Sentinelle) plus lumineux en haut de page : titre NEXUS plus brillant, sous-titre et petits textes plus clairs, onglets en texte clair sur des plaques plus visibles (les profils visuels gardent leur propre apparence)

## [1.0.7] - 2026-11-11

### Modifié
- Profil « Pure » 1.2, encore plus pastel : fond menthe aux halos ciel, lavande, pêche, citron et rose ; cartes teintées de la couleur de leur catégorie avec un bandeau pastel ; un onglet de couleur différente par catégorie (l'onglet ouvert souligné) ; barre du haut en dégradé ciel → lavande → pêche ; boutons et raccourcis teintés ; textes gardés foncés (contraste revérifié dans les deux modes)

## [1.0.6] - 2026-11-11

### Modifié
- Profil « Pure » 1.1 : fond vert pastel clair (halos ciel, lavande, pêche et citron), cartes blanches bien détachées avec un bandeau pastel de la couleur de leur catégorie, icônes et encadrés teintés, barre du haut dans un panneau blanc translucide ; contraste revérifié dans les deux modes et sur téléphone

## [1.0.5] - 2026-11-11

### Modifié
- Processus : lus en un seul appel système Windows (`winproc.py`, comme le Gestionnaire des tâches) au lieu d'interroger chaque processus : ~3 ms au lieu de ~430 ms toutes les 2 s ; le serveur au repos passe d'environ 15 % à moins de 1 % d'un cœur, et répond plus vite (le verrou de Python n'est plus monopolisé)
- Bot Discord : discord.py (~30 Mo de mémoire) n'est chargé que si le bot démarre vraiment (jeton configuré)
- `/api/stats` : un seul relevé par demi-seconde, partagé par tous les appareils ouverts (PC, téléphone)
- Page : l'onglet PC (jauges, courbes, listes) n'est dessiné que quand il est affiché ; ailleurs, seuls l'historique des courbes, les voyants, le mode jeu et les alertes sont mis à jour (0,05 ms par seconde au lieu de ~4 ms)
- Espace disque : `versions\` garde les 8 sauvegardes de code les plus récentes, `sauvegardes-maj\` les 3 dernières sauvegardes de mise à jour, `dist\` et `partage\` seulement la dernière version

### Corrigé
- Avertissement Python (séquence d'échappement) dans l'assistant de configuration

## [1.0.4] - 2026-11-10

### Ajouté
- Profil visuel « Pure » (les deux modes) : thème clair, fond blanc bleuté, bleu ciel et touches pastel (lavande, menthe, pêche), cartes blanches arrondies et ombres douces, page de garde claire, commandes du lecteur rondes ; contraste du texte vérifié sur tous les onglets, fenêtres et menus, et sur téléphone

## [1.0.3] - 2026-11-10

### Ajouté
- Santé de NEXUS (bouton ✚ Santé, lien du sommaire) : état du serveur, du bot Discord, de LibreHardwareMonitor, de la carte graphique, du suivi des statistiques, de la lecture en cours, des mises à jour, de la base, du disque et de l'accès téléphone ; dernières erreurs et avertissements du serveur ; pastille quand quelque chose ne va pas
- Journal d'activité des actions sensibles (onglet de la fenêtre Santé, filtrable) : deck (boutons, connexions), mises à jour (installation, retour, jeton, réglages, mots de passe refusés), appareils (appairage, appareil refusé ou retiré), fermetures de processus, sessions de focus ; gardé dans `data\activite.jsonl`
- PC : classement complet des processus (par processeur ou par mémoire) avec un bouton « Fermer » et confirmation ; processus vitaux de Windows et NEXUS lui-même protégés ; réservé au PC (jamais depuis le téléphone)
- Minuteur Pomodoro et mode focus (bouton ⏱ Focus) : travail / pause / pause longue réglables, suspendre, passer, arrêter, son et message à chaque fin de phase ; le temps de travail compte dans « Travail » des statistiques ; profil sobre (Ardoise) pendant la session sans changer le profil choisi ; `body[data-focus]` pour les profils

## [1.0.2] - 2026-11-10

### Ajouté
- Alertes : bouton « Ignorer » sur chaque alerte ; elle revient à la prochaine ouverture de NEXUS (nouvel onglet) ou à son prochain démarrage (mise à jour comprise) si le souci persiste
- Mises à jour : étape de validation obligatoire à chaque mise à jour (récapitulatif « Valider la mise à jour vers X ? »), aussi exigée par le serveur pour cette version précise ; idem pour le retour à la version précédente

### Corrigé
- Sommaire : les alertes n'apparaissent plus en double (une seule barre, sous les onglets)
- Mises à jour : l'heure de la dernière vérification n'est notée qu'une fois la réponse de GitHub reçue

## [1.0.1] - 2026-11-10

### Modifié
- Sommaire plus léger : une tuile (et les alertes) n'est réécrite que si son contenu change, et tout se met en pause quand l'onglet est caché
- Mises à jour : un jeton peut être fourni par la variable d'environnement `NEXUS_MAJ_JETON` (tests automatiques ; jamais enregistré)
- Copie de partage : la documentation et `THIRD_PARTY.md` sont incluses
- Intégration continue : dépendances de test dans `requirements-dev.txt` (client de test des versions récentes de Starlette)

## [1.0.0] - 2026-11-10 - Première version publiée

Première version diffusée par un dépôt Git et des releases GitHub. Elle reprend tout le panel développé
jusqu'ici (version interne 3.25.0 ; le détail de son historique est dans `docs/HISTORIQUE-INTERNE.md`).

### Ajouté
- Tableau de bord du PC : processeur, mémoire, carte graphique, températures, disques, ventilateurs, réseau, processus, mode jeu
- Média : lecture en cours (Spotify, Deezer, tous les navigateurs…), commandes instantanées, mélangeur de son par application
- Stream deck (boutons d'actions protégés par mot de passe), lanceur de jeux et d'applications, accès depuis le téléphone (appairage)
- Agenda (évènements, répétitions, anniversaires, rappels, fêtes et jours fériés), to-do et notes
- Souvenirs (mur de photos et post-it par jour), statistiques personnelles (temps de PC, de jeu, de musique), journal quotidien
- Profils visuels (Sakura, Pluie d'étoiles, Dés du destin, Néon minuit, Phosphore, Ardoise) en modes Terminal et Sentinelle ; champ `panel_min_version` (compatibilité)
- Bot Discord facultatif (alertes, rappels, commandes réservées au propriétaire)
- Mises à jour : vérification automatique des releases du dépôt configuré (au démarrage puis toutes les 6 h, réglable), bannière et pastille, installation au clic avec le mot de passe du panel, vérification SHA256, sauvegarde horodatée, test de démarrage et restauration automatique en cas d'échec, retour à la version précédente, écran de transition aux couleurs du profil
- Jeton GitHub en lecture seule rangé dans le gestionnaire d'identifiants de Windows (`docs/JETON_GITHUB.md`)
- Schéma de `config.json` numéroté avec migrations (sauvegarde avant chacune), en plus des migrations de la base SQLite
- Publication : `outils/release.py` (contrôles, version, CHANGELOG, tag, archive propre + SHA256, release), intégration continue GitHub Actions (tests, lint, profils, secrets)

### Sécurité
- Aucune donnée personnelle ni secret dans le dépôt : `.gitignore` strict, modèles `*.example.json`, contrôle par gitleaks et `outils/scan_perso.py`
