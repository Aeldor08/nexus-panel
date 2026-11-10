# Journal des versions

Format : `## [version] - date - titre`, puis une liste de changements.
Numérotation : **majeur.mineur.correctif** (ex. 2.4.1 = correctif de la 2.4).

## [3.25.0] - 2026-11-10 - Média plus réactif, tous les navigateurs et Deezer
- Réactivité : le serveur écoute les ÉVÉNEMENTS de Windows (piste, lecture / pause, position, nouvelle source)
  au lieu de relire l'état une fois par seconde seulement ; après une commande, l'état est relu tout de suite
  puis 2 fois juste après. La page reçoit le nouvel état dès qu'il change (écoute longue : /api/media?sig=…&attendre=…),
  au lieu d'interroger chaque seconde (2 requêtes en 6 s au lieu de 6) ; la barre de progression avance toute seule
- Boutons instantanés : ⏯ bascule au clic (0,7 ms), ⏭ / ⏮ estompent la piste jusqu'à l'arrivée de la suivante ;
  l'état réel remplace l'affichage dès qu'il arrive. La commande ne bloque plus le serveur (fil à part)
- Détection : tous les navigateurs courants (Opera GX / Opera distingués, Chrome, Edge, Firefox — qui s'annonce par
  un code — LibreWolf, Waterfox, Floorp, Zen, Brave, Vivaldi, Arc, Yandex…) ; lecteurs Deezer (appli du Store ou
  classique), Apple Music, iTunes, Tidal, Amazon Music, Qobuz, foobar2000, MusicBee, AIMP, Winamp, Plex… ; site
  deviné dans un navigateur (Deezer, YouTube, SoundCloud…) ; pastille violette Deezer
- Statistiques : Deezer (appli ou site), Apple Music, Tidal… comptés en « Musique » sans réglage
- Tests : outils/tests/test_media.py (31 vérifications) ; onglet Média vérifié dans Edge (commandes interceptées)

## [3.24.0] - 2026-11-10 - Post-it : plus de couleurs, couleur d'écriture, polices, boutons lisibles partout
- Boutons des post-it lisibles sur tous les thèmes : le style des boutons d'un profil (Dés du destin : cuir
  sombre, texte sombre sur papier clair) ne s'y applique plus ; texte et bordure suivent le papier (contraste
  mesuré ≥ 5,2 sur les 4 profils, modes Terminal et Sentinelle, fond clair comme foncé)
- 16 fonds au lieu de 6 (pastels du thème + menthe, ciel, lavande, corail, sable, blanc + papiers foncés kraft,
  ardoise, nuit, bordeaux), 9 couleurs d'écriture (automatique, noir, sépia, bleu marine, bordeaux, vert forêt,
  violet, blanc, or) dans une palette 🎨 qui s'ouvre au-dessus de la barre
- 9 polices au choix : celle du thème, les titres du thème (profils : variable --note-titre), et 7 polices de
  Windows (sans / avec empattement, manuscrite, plume, feutre, machine à écrire, élégante), avec repli proche
- Base : migration 4 (colonnes encre et fonte des notes, sauvegarde automatique avant) ; profils Dés du destin 2.1,
  Pluie d'étoiles 2.1, Sakura 1.11 (police de titre pour les post-it)
- Test : outils/tests/test_postit_couleurs.py (21 vérifications) ; test_postit.py toujours 15/15

## [3.23.0] - 2026-11-10 - Post-it : mode lecture et mode édition
- Mur des Souvenirs : les notes (post-it) ont deux états. En lecture : le texte seul et un petit ✎ dans
  l'angle en haut à droite. En édition (✎, double-clic sur le texte, ou toute nouvelle note) : texte modifiable,
  et la barre ✓ · couleurs · A− / A+ · 📌 · 🗑. ✓, Échap, Ctrl + Entrée ou un clic hors de la note la referment ;
  la dernière frappe est enregistrée en sortant. Changer la couleur ou la taille garde la note ouverte
- Échap dans une note ne quitte plus l'onglet ; au doigt, le ✎ est plus grand (pas de survol)
- Test : outils/tests/test_postit.py (15 vérifications dans Edge, profils Défaut et Sakura)

## [3.22.3] - 2026-11-10 - Barres de défilement : seulement quand il y a quelque chose à faire défiler
- Correctif : dans les blocs déplacés (Souvenirs, Deck, Lanceur, Journal…), des barres roses s'affichaient alors
  que rien ne dépassait, verrouillé ou non. Causes : la hauteur enregistrée des blocs était trop courte de quelques
  pixels (≈ 10 px, marges et coins des profils) ; et la branche fleurie de Sakura, qui se balance dans le coin
  des cartes, dépassait de 3 px à droite
- Désormais : jamais de barre horizontale dans un bloc (le contenu passe à la ligne, les décorations qui
  débordent de quelques pixels sont rognées) ; un bloc à qui il ne manque que quelques pixels (≤ 24 px)
  s'agrandit tout seul ; un contenu qui dépasse vraiment garde sa barre verticale (js/layout.js, ui.css)
- Sakura 1.10 : la branche du coin se balance vers l'intérieur de la carte
- Vérifié : 9 onglets × 4 profils × 2 modes, blocs en disposition libre → aucune barre inutile ; bloc réduit
  sous son contenu → barre verticale présente

## [3.22.2] - 2026-11-10 - Onglet Statistiques à côté de Réseau
- Barre d'onglets : Statistiques est désormais juste après Réseau (… Lanceur, Réseau, Statistiques, Agenda,
  Souvenirs, Journal), et la tuile Statistiques du sommaire suit le même ordre (après Réseau). Une disposition
  du sommaire déjà déplacée à la main garde ses places

## [3.22.1] - 2026-11-10 - Statistiques : un jeu n'est plus compté deux fois
- Correctif : Valorant apparaissait deux fois (« Valorant » et « VALORANT ») avec le même temps : le mode jeu
  reconnaissait « VALORANT.exe » pendant que jeux.json comptait « valorant-win64-shipping.exe ». Le jeu vu par le
  mode jeu n'est plus ajouté quand un jeu de jeux.json tourne déjà (statistiques.py)
- Données : « VALORANT » fusionné dans « Valorant » (8 et 9 novembre, temps du jour gardé, sans double somme) ;
  la ligne EOSOverlayRenderer (surcouche d'Epic, 2,2 h le 9 novembre, comptée avant le correctif 3.17.2) supprimée.
  Copies de la base avant chaque modification dans data/backups/
- Test : outils/tests/test_stats_doublon.py (4 vérifications, faux processus)

## [3.22.0] - 2026-11-10 - Dés du destin 2.0 : la table du Maître du donjon
- Refonte réaliste et détaillée, inspirée des tables de jeu de rôle (lumière de bougie, chêne, parchemin,
  cuir, dés polyédriques). Toutes les images sont des dessins ORIGINAUX rendus une fois (carte graphique) en WebP :
  - **sommaire** : table en chêne sombre (veines, cernes, nœuds, joints, usure, vernis) éclairée par deux
    bougies ; carte de donjon dessinée à l'encre sur parchemin (salles, couloirs, escalier, rose des vents,
    « ici gît le dragon… », sceau de cire) ; vrais dés polyédriques d4, d6, d8, d10, d12 et d20 en résine
    (rubis, os, nuit) aux chiffres gravés et dorés, numérotés selon la règle (faces opposées = n + 1, d10 de
    0 à 9), éclairés par la bougie la plus proche, avec leurs ombres ; pièces d'or. Objets placés dans les zones
    libres de l'en-tête (rien derrière l'horloge ni les boutons)
  - **cartes** en cuir de grimoire (grain, pores, plis fins) cousu d'or ; bordure dorée et runes conservées
  - **page de garde** : vrai mur de donjon (pierres taillées irrégulières, joints, fissures, mousse et
    salpêtre, suie au-dessus des torches, relief éclairé par les flammes) ; torches murales en bois cerclé de fer ;
    brasero en fer forgé riveté sur trépied, lit de braises et feu réaliste animé (16 images en boucle) ;
    le d20 de l'intro roule VRAIMENT en 3D (30 images) et s'arrête sur 20
  - dés des alertes (20 doré quand tout est résolu, 1 en os si critique) et mini-dé des boutons en rendu réaliste
- Gardés tels quels : les jauges en traits de feu (projectile magique) et le fil rouge de sort qui ondule
- Performances : runes des cartouches désormais fixes (un SVG animé sur chaque carte forçait à tout redessiner) ;
  mesuré 161-165 images/s au repos et pendant l'ouverture, en 1720×900 comme en 3440×1440
- Profil complet d'avant sauvegardé : data/backups/des-du-destin-avant-refonte-dnd-20261110

## [3.21.0] - 2026-11-10 - Passage au sommaire choisi pour chaque profil
- ⚙ Réglages → « Passage au sommaire » règle désormais le profil visuel EN COURS (son nom est affiché) :
  ouverture en rond, vieille télé, simple fondu, ou « celui du profil » (le passage prévu y est indiqué).
  Chaque profil garde son propre choix, retenu sur cet appareil (localStorage « nexus-ouverture-profils »),
  même après un changement de profil ou un redémarrage. L'ancien réglage commun sert encore de repli aux
  profils jamais réglés. Avec le profil Défaut, une note explique que le réglage est par profil animé
- Test : outils/tests/test_ouverture.py (13 vérifications dans Edge : choix séparés Sakura / Pluie / Dés,
  mémoire après rechargement, animation réellement jouée, repli sur l'ancien réglage)

## [3.20.0] - 2026-11-10 - Nuages volumétriques, pied du cerisier, blocs sans barre de défilement
- Pluie d'étoiles 2.0 : nuages entièrement refaits en rendu VOLUMÉTRIQUE (marche de rayons sur la carte
  graphique, puis enregistrés en images WebP : aucun coût en plus à l'affichage). Chaque nuage est un volume
  de sphères fusionnées, sculpté par un bruit en « chou-fleur » à 5 échelles ; la lune (à gauche, lumière
  rasante) le traverse : ombres internes dans les replis, diffusion multiple (creux jamais noirs), lumière du
  ciel par le haut, base plate légèrement ondulée et plus sombre. Petits fractus isolés au lieu des boules.
  Couche lointaine plus douce et bleutée. Fichiers plus légers (294 + 180 Ko au lieu de 508 + 200 Ko).
  Générateur sauvegardé : data/backups/pluie-nuages-avant-volumetrique-20261110
- Sakura 1.9 : le pied de l'arbre n'est plus coupé par le bas de l'écran. Nouvelle couche pied.webp (même
  repère que l'arbre) : butte de terre, herbe rose en touffes (quelques brins vert tendre), tapis de pétales
  tombés plus dense sous la couronne et entre les racines, ombre de la couronne au sol, reflet de lune ; le haut
  de la terre est progressif, les racines s'y enfoncent. L'arbre est remonté de 6vh pour s'y poser (aussi
  pendant l'intro, où le sol apparaît en fondu). Vérifié en 1720×900, 1720×1000 et 3440×1440
- Blocs des pages aux valeurs qui bougent (Sommaire, PC, Média, Réseau, Statistiques) : plus de barre de
  défilement dans chaque case. Un bloc dont le contenu dépasse (Sakura : police plus grande ; disposition
  enregistrée trop petite) grandit à la taille du contenu et pousse les blocs du dessous (js/layout.js,
  option « ajuste »). Testé : tous les blocs réduits au minimum → aucun défilement, aucun chevauchement
- Mesures (3440×1440) : Sakura et Pluie d'étoiles ≈ 163-165 images/s au repos et ≈ 157-163 pendant
  l'ouverture

## [3.19.0] - 2026-11-09 - Agenda : fêtes et jours fériés
- Le calendrier affiche les 11 jours fériés français (numéro du jour et bandeau en couleur) et les dates
  classiques : Épiphanie, Chandeleur, Saint-Valentin, Mardi gras, Pâques, Pentecôte, fêtes des grands-mères,
  des mères, des pères et des grands-pères, Fête de la musique, Halloween, réveillon de Noël,
  Saint-Sylvestre, passages à l'heure d'été et d'hiver. Aussi dans la fenêtre du jour et dans « À venir »
- Calcul local (static/js/fetes.js, aucune connexion) : Pâques par l'algorithme grégorien, puis Ascension,
  Pentecôte, Mardi gras ; fête des mères au dernier dimanche de mai, décalée au 1er dimanche de juin quand
  elle tombe à la Pentecôte (ex. 2020, 2023). Vérifié sur les calendriers officiels 2024-2030
- Menu en haut du calendrier : « Fêtes et jours fériés » / « Jours fériés seulement » / « Sans les fêtes »
  (retenu sur cet appareil). Pas de rappel pour les fêtes (ce ne sont pas des évènements)

## [3.18.1] - 2026-11-09 - Onglet PC : plus de valeurs coupées en deux
- Cartes CPU, RAM et GPU : quand la carte est étroite, les valeurs se coupaient (« 62.2 » puis « % » à la
  ligne, « Go » seul, « °C » seul…). Chaque ligne (libellé + valeur) reste désormais d'un bloc, et si la place
  manque à côté de la jauge, les valeurs passent dessous sur toute la largeur ; seuls les petits détails
  (« max 3.62 GHz », « mém. 14001 MHz », source) peuvent passer à la ligne. Vérifié de 240 à 560 px de large,
  dans les 2 thèmes et les 3 profils

## [3.18.0] - 2026-11-09 - Animations à 60 images/s, phrase d'entrée fluide, valeurs PC stables
- Les animations dessinées par le panel (titre brouillé et pluie de l'intro, vumètres du mélangeur) sont
  bridées à 60 images/s (`nxImage`, index.html) au lieu de suivre l'écran (144/165 Hz) : mesuré 165 → 60.
  Les animations CSS (profils, page de garde) restent calculées par la carte graphique à la fréquence de
  l'écran : le navigateur ne permet pas de les brider (elles ne coûtent quasiment rien)
- Page de garde : « ▶ Clique sur NEXUS pour entrer » ne clignote plus par à-coups ; la phrase apparaît en
  fondu puis respire doucement, et la flèche avance et recule en glissant
- Sommaire, catégorie PC : CPU, températures, GPU et RAM ne se décalent plus quand une valeur monte ou
  descend (chiffres à chasse fixe, largeur réservée pour « 100 % » et « 100° ») ; vérifié dans les 2 thèmes
  et les 3 profils

## [3.17.6] - 2026-11-09 - Pluie d'étoiles et Dés du destin : intro et ouverture fluides
- Correctif Pluie d'étoiles 1.9 : les deux couches de nuages (SVG lourds à filtres, agrandis par la dispersion
  du cercle) sont rendues en images WebP (5600 px, rendu identique). Mesures (Edge, RTX 5070, 3440×1440) :
  gel au clic 158 → 0 ms, pire image pendant le cercle 237 → 25 ms, 89 → 158 images/s
- Correctif Dés du destin 1.7 : la page de garde tournait à ≈ 47 images/s et le cercle saccadait. Causes
  mesurées : le fond du donjon, les torches et les braises étaient des SVG animés en interne, redessinés en
  plein écran à chaque image ; la brume et la salle étaient des SVG lourds. Tous sont désormais des images
  WebP fixes ; le mouvement est porté en bloc par la carte graphique (torches qui vacillent, braises qui
  montent en boucle, dés flottants). Page de garde 47 → 162 images/s, sommaire 67 → 158, gel au clic
  55 → 0 ms, pire image pendant le cercle 97 → 36 ms, transition 57 → 160 images/s
- FORMAT.md : conseil « plusieurs SVG animés en grand → image fixe animée par opacity/transform »
- Anciens SVG sauvegardés dans data/backups/pluie-des-svg-avant-webp-20261109

## [3.17.5] - 2026-11-09 - Sakura : intro et ouverture fluides
- Correctif Sakura 1.8 : au clic sur NEXUS, l'écran se figeait ≈ 1 s, puis le cercle s'arrêtait par à-coups
  (120 à 300 ms) pendant que le fond continuait de bouger. Cause mesurée (Edge, RTX 5070, 3440×1440) : l'arbre
  et les deux couches de fleurs en volume étaient des SVG lourds à filtres (éclairage, grain), recalculés à
  chaque changement d'échelle (plongée, dispersion). Ils sont désormais rendus une fois en images WebP
  transparentes (2800 px, rendu identique, même moteur) : gel au clic 1 000 → 0 ms, pire image pendant le
  cercle 49-267 → 12 ms, 164 images/s (le maximum de l'écran). L'arbre qui pousse pendant l'intro reste en SVG
- FORMAT.md : conseil « SVG lourd à filtres agrandi pendant une transition → image WebP »

## [3.17.4] - 2026-11-09 - Mode jeu : l'onglet PC n'est plus mis en pause
- En mode jeu, le relevé des processus s'arrêtait (liste figée, « en pause (mode jeu) ») et l'onglet PC
  n'était rafraîchi que toutes les 2 s : désormais rien n'y est mis en pause, processus compris (relevé
  toutes les 2 s, affichage chaque seconde, comme hors jeu). Le mode jeu garde : animations coupées et scan
  automatique du réseau local (onglet Réseau) en pause
- Tests : outils/tests/test_modejeu_pc.py (jeu simulé : la liste des processus reste vivante)

## [3.17.3] - 2026-11-09 - Transitions des profils sans coupure : le cercle disperse l'animation
- Correctif : l'animation des profils (vagues de pétales et plongée de Sakura, lueur du feu de Dés du destin,
  étoiles qui filent de Pluie d'étoiles) était liée à l'état « transition » ; au moment où le cercle
  s'ouvrait (état « arrivee »), elle s'arrêtait net et la scène revenait d'un coup en place : coupure
- Les animations continuent désormais pendant toute l'ouverture (même animation, sans redémarrage), et le
  cercle les DISPERSE : la scène et les calques d'effet grossissent depuis le logo pendant qu'il s'ouvre
  (propriété scale, réglable par profil : --sp-disperse), puis il découvre le sommaire
- Transitions plus longues : Sakura 3,4 s (2,2 avant), Pluie d'étoiles et Dés du destin 3 s (1,5 et 1,4) ;
  le cercle part plus tôt (45 % au lieu de 60 %) et s'ouvre plus lentement (≈ 2,3 à 2,5 s) ; sommaire
  entièrement découvert à 4,1 s (Sakura) et 3,7 s (les deux autres)
- Versions : Sakura 1.7, Pluie d'étoiles 1.8, Dés du destin 1.6 ; FORMAT.md : règle « sans coupure »

## [3.17.2] - 2026-11-09 - Mode jeu : bouton pour le désactiver
- Carte « Mode jeu » (onglet PC) : bouton **⏸ Désactiver le mode jeu** / **▶ Réactiver le mode jeu**, à tout
  moment, retenu au redémarrage. Désactivé : le panel ne s'allège plus (animations, rafraîchissements, scans
  normaux) et le plan d'alimentation n'est jamais touché ; la détection continue pour les statistiques
  (temps de jeu). (Dés)activé en pleine partie : le plan d'alimentation suit aussitôt
- Bouton **✖ Ce n'est pas un jeu** : met le programme détecté dans les exceptions et quitte aussitôt le mode jeu
- Correctif détection : les surcouches (« overlay » : EOSOverlayRenderer d'Epic, gameoverlayui de Steam,
  NVIDIA Overlay…) ne sont plus prises pour des jeux, même installées dans un dossier de jeux
- Tests : outils/tests/test_modejeu.py (faux processus, aucune donnée réelle touchée)

## [3.17.1] - 2026-11-09 - Curseurs de volume fiables (mélangeur et carte Média)
- Correctif : en montant / descendant un volume, le curseur s'arrêtait parfois en plein geste ou revenait à
  une ancienne valeur (ex. 30 % après être passé de 20 à 40 %). Quatre causes, toutes corrigées :
  1. la protection « curseur tenu » sautait 400 ms après le premier mouvement, même en plein glisser : le
     sondage de l'état réécrivait alors le curseur sous le pointeur ;
  2. chaque seconde, les lignes du mélangeur étaient ré-insérées dans la page, ce qui ANNULE le glisser en
     cours dans le navigateur (c'est le « ça s'arrête alors que je bouge encore ») ;
  3. les réglages partaient toutes les 90 ms sans attendre le précédent : ils pouvaient se doubler et
     arriver dans le désordre (un ancien volume appliqué après le dernier) ;
  4. après le lâcher, un état lu avant le dernier réglage faisait revenir le curseur en arrière.
- Désormais : un curseur tenu n'est jamais réécrit ni déplacé ; un seul envoi à la fois par appli (seule la
  dernière valeur demandée attend) ; la valeur choisie reste affichée jusqu'à ce que le serveur la renvoie,
  lue après le dernier réglage (au plus 2,5 s, ensuite le serveur fait foi : réglage fait ailleurs) ; le
  curseur du mélangeur et celui de la carte Média restent synchronisés
- Serveur : numéro d'ordre des réglages par page (une requête plus ancienne arrivée en retard est ignorée) ;
  réglage exécuté hors de la boucle principale (il ne bloque plus les autres requêtes) ; une lecture de l'état
  faite pendant un réglage n'est plus gardée en cache

## [3.17.0] - 2026-11-09 - Passage au sommaire : ouverture en rond ou vieille télé
- Page de garde des profils : nouvelle fin de transition au choix du profil (`animations.ouverture` dans
  profil.json : `fondu`, `cercle`, `tele`). « cercle » : un trou aux bords doux part du logo et s'agrandit
  jusqu'aux coins exacts de l'écran, bordé d'un anneau lumineux, comme la fin de la pluie de code du thème
  par défaut ; « tele » : vieille télé qui s'allume (noir, ligne lumineuse qui s'étire, ouverture verticale
  dans un éclair). Uniquement transform / opacity et un masque animé (propriété CSS déclarée), aucun script
  image par image
- Sakura 1.6, Pluie d'étoiles 1.7, Dés du destin 1.5 : ouverture en rond, anneau rose / bleu glacier / de feu
  (cœur doré, flamme orange, fumée rouge) ; leur décor reste en place et continue d'animer autour de
  l'ouverture (avant, il s'effaçait d'abord, puis tout disparaissait en fondu)
- ⚙ Réglages → « Passage au sommaire » : celui du profil, ouverture en rond, vieille télé ou simple fondu
  (mémorisé sur l'appareil). En mode jeu (animations coupées) : toujours un simple fondu, jamais d'écran figé
- FORMAT.md : `ouverture`, `--sp-anneau`, personnalisation de `#splash .sp-anneau`

## [3.16.6] - 2026-11-09 - Verrous fiables, journal encore plus lisible, cerisier en masses fleuries
- Correctif verrouillage : l'état d'un onglet n'était lu qu'au moment où l'onglet devenait visible ; un onglet
  caché ou reconstruit en arrière-plan (ex. au changement de profil) repartait « déverrouillé » et son bouton
  pouvait afficher un état faux (un clic enregistrait alors le mauvais état). L'état est désormais lu dès la
  création, et chaque bouton se met à jour à chaque changement : verrouillé reste verrouillé, quels que soient
  le profil, le mode et les rechargements
- Journal : icônes encore plus grandes. Vue du mois : visage 92 px (humeur 40 px, activités 19 px), 74 px sur
  tablette, 46 px sur téléphone ; visage du jour 140 px ; boutons d'humeur 62 px, activités en 28 px
- Sakura 1.5 (d'après les modèles fournis) : couronne en grosses masses fleuries en volume (dessus rose pâle,
  dessous rose profond, cœur de couronne comblé, petites fleurs sur le côté éclairé, une partie des masses
  devant les branches), branches sombres visibles entre les masses ; tronc très épais penché en S, fait de
  4 torons torsadés ; racines « en doigts » noueuses qui s'étalent sur le sol
- Correctif Sakura : sans animation (mode jeu, animations réduites), l'arbre de la page de garde reprenait la
  perspective 3D de la grille du thème de base et apparaissait écrasé au bas de l'écran

## [3.16.5] - 2026-11-09 - Journal : visages plus lisibles ; Sakura : arbre plus réaliste
- Journal, vue du mois : humeur et activités du jour en plus grand (visage 72 px au lieu de 50 : humeur
  30 px, activités 15 px ; 58 px sur tablette, 44 px sur téléphone) ; les cases qui en ont un s'agrandissent
  un peu, le visage ne déborde jamais de sa case
- Sakura 1.4 : nouvel arbre original. Tronc épais torsadé (cannelures en spirale, écorce à bandes de
  lenticelles, fissures, cicatrices de branches), empattement large et racines-contreforts sinueuses qui
  sortent de terre puis s'y enfoncent ; branches en courbes lisses, section conservée aux fourches,
  jonctions fondues dans la branche mère, volume éclairé par la lune, rameaux en zigzag, plus aucune boucle ;
  fleurs aussi le long des branches (éperons), couronne pleine et équilibrée (meilleure charpente choisie
  parmi 80 tirages) ; rien ne déborde du cadre ; pousse de l'intro terminée en ≈ 2,8 s

## [3.16.4] - 2026-11-09 - Pluie d'étoiles : nuages « chou-fleur »
- Pluie d'étoiles 1.6 : nuages refaits d'après l'ensemble des modèles fournis. Relief en chou-fleur sur
  plusieurs échelles (grosses bouffées couvertes de bouffées moyennes, elles-mêmes couvertes de petites),
  chacune arrondie par la lumière, plis gris doux entre elles ; masse dense et presque opaque d'un blanc
  lunaire ; silhouettes en dôme qui s'abaissent sur les côtés ; bords nets à fine frange ; trois types :
  cumulus en tours, bancs allongés à dessous plat, lambeaux. Les bouffées sont légères et s'additionnent
  comme une vraie masse nuageuse : l'éclairage lit enfin le relief intérieur (avant, la densité saturait et
  l'intérieur restait plat). Toujours statiques, calculés une seule fois

## [3.16.3] - 2026-11-09 - Pluie d'étoiles : montagnes entières sur écran large, nuages affinés
- Correctif montagnes : sur un écran très large (ex. 3440 px), l'image était agrandie à la largeur de l'écran
  et le haut des sommets était rogné (crête plate). Mêmes montagnes, prolongées à gauche et à droite
  (partie centrale identique) : sur écran large on voit plus de crête, jamais des sommets coupés
- Nuages (Pluie d'étoiles 1.5) : toile deux fois plus large (nuages de même taille sur tous les écrans, nuages
  supplémentaires sur les côtés), dessous bosselé au lieu d'une ligne droite sombre, morceaux détachés plus
  fins et translucides, cœur plein (les fentes restent sur les bords), plus de taches grises, plan lointain
  en bande douce sur l'horizon ; le nuage placé derrière le logo est écarté (le halo du logo le salissait)

## [3.16.2] - 2026-11-09 - Pluie d'étoiles : nuages encore plus réalistes
- Pluie d'étoiles 1.4 : nuages plus naturels, d'après de nouveaux modèles : bords déchiquetés et filandreux
  (double effilochage, duvet fin), fentes et creux sombres qui découpent la masse en bouffées, morceaux
  détachés autour des nuages, dessous qui se déchire, blancs plus lumineux et ombres plus profondes (les creux
  laissent deviner le ciel) ; plan lointain et miniature assortis. Toujours statiques, calculés une seule fois
- Correctif : les couches du ciel posées sur <html> (nuages lointains, étoiles proches, filantes) se
  peignaient PAR-DESSUS les cartes du panel ; ordre des couches désormais imposé (derrière les données)
- Page de garde : les nuages dérivent lentement comme dans le panel (ils restent sur leur propre calque,
  dessinés une fois, au lieu d'être recalculés avec les étoiles qui scintillent)

## [3.16.1] - 2026-11-09 - Pluie d'étoiles : vrais cumulus
- Pluie d'étoiles 1.3 : nuages redessinés en cumulus au clair de lune (dômes arrondis en « chou-fleur »,
  sommets blancs, plis et base gris-bleu, bords vaporeux qui s'effilochent), nuages lointains assortis et
  nouvelle miniature. Nuage procédural original : bouffées douces + bruit fractal + éclairage diffus et
  ombre propre, calculés une seule fois (SVG statiques, aucune animation interne ; 24 et 18 Ko)
- Lisibilité : halo de nuit sous le titre, l'horloge, la date et les aides posés directement sur le ciel

## [3.16.0] - 2026-11-09 - Optimisation, vumètres fluides, verrou qui affiche son état
- Mise en cache des profils : CSS, images et polices servis à une adresse versionnée (`?v=<signature>`,
  ajoutée aussi aux `url(assets/…)`) et gardés un an par le navigateur ; sans version : `no-cache` + ETag
  (réponse 304). Pages et API jamais en cache. Rechargement avec Dés du destin : 18 → 2 requêtes au serveur,
  237 → 12 Ko ; la feuille du profil n'est plus téléchargée deux fois (l'en-tête reprend l'adresse versionnée)
- Changement de profil plus court quand tout est déjà en cache (détection fiable par Resource Timing) :
  Sakura 1,46 → 1,05 s
- Animations : pause complète quand l'onglet est caché (`html.nx-pause`), interrogations du PC espacées ;
  page de garde (grille, balayage, respiration du logo et des voyants) et alerte critique animées par
  `transform` / `opacity` seulement (filtres et ombres fixes) ; `will-change` limité aux états qui animent
- SVG des profils : motifs répétés regroupés par `<use>`, espaces superflus retirés (Sakura 804 → 696 Ko) ;
  scintillements des étoiles, flammes et runes synchronisés par paliers (`steps()`, grille de 0,5 s) :
  l'image de fond plein écran n'est plus redessinée 60 fois par seconde mais 2 à 4 fois, sans différence visible
- Mélangeur : vumètres lissés à l'écran (montée ≈ 45 ms, descente ≈ 380 ms, sans scintillement), niveaux
  lus 10 fois par seconde en une seule petite requête (`/api/audio/niveaux`, ≈ 0,15 ms côté serveur au lieu
  de 15 à 20 ms pour l'état complet) ; barre dessinée par `clip-path` dans un bloc `contain: layout paint` ;
  sans animation : valeur appliquée directement. `--valeur` du vumètre suit aussi ce rythme, et
  `data-niveau` reste bien `bas` pour les volumes (comme documenté)
- Disposition : le bouton affiche l'ÉTAT — « 🔓 Déverrouillé » (vert) ou « 🔒 Verrouillé » (ambre), avec
  `aria-pressed` et une infobulle qui dit ce que fait le clic ; toujours mémorisé par catégorie et par appareil.
  (Le bouton du stream deck qui verrouille la session Windows n'est pas concerné)
- Profils : Sakura 1.3, Pluie d'étoiles 1.2, Dés du destin 1.4, Néon Minuit 1.0.1, Phosphore 1.0.1
  (même apparence, moins coûteux)
- FORMAT.md : conseils de performance (filtres fixes, `will-change`, paliers pour les SVG animés, `<use>`)
  et mise en cache

## [3.15.0] - 2026-11-09 - Transitions fluides, nouvel arbre Sakura, nuages réalistes
- Changement de profil en douceur, pour tous les profils : écran NEXUS neutre (« Chargement du profil … »,
  version, barre, accent du profil d'arrivée), préchargement de la feuille ET de toutes ses images et polices,
  bascule seulement quand tout est prêt, fondu d'apparition ; ≈ 1,5 s (≈ 1 s en cache) ; clics absorbés,
  demandes successives mises en file (la dernière gagne) ; retour au profil précédent si le chargement
  échoue ; fondu court sans animation. États `body[data-profil-etat="changement|pret"]`, variable `--accent-profil`
- Bouton NEXUS → sommaire : fin d'animation et apparition du sommaire qui se chevauchent (fondu ease-in-out
  de la page de garde, tuiles en cascade), sommaire préparé à l'avance ; nouvel état `body[data-etat="arrivee"]`.
  Sakura : les feuilles passent encore au premier plan ; Pluie d'étoiles : les étoiles restent en fond ;
  Dés du destin : souffle chaud qui se dissipe sur le sommaire
- Correctif page de garde : la barre de défilement de la page restait visible à droite (bande coupée) car le
  verrou de défilement n'atteignait pas la fenêtre ; il est posé sur <html> jusqu'à la fermeture complète
- Sakura 1.2 : nouvel arbre original (tronc penché et torsadé sur une butte aux racines apparentes, écorce
  texturée, nœuds, couronne large et irrégulière, branches fines très ramifiées, floraison en lavis rose et
  grappes de tailles variées, fleurs lointaines floues, pétales emportés par le vent, halo rosé) ; pousse puis
  floraison qui explose ; sol séparé, aussi large que l'écran (plus de coupure sur les bords)
- Pluie d'étoiles 1.1 : nuages volumineux (bouffées superposées, bords effilochés et grain par filtres SVG
  statiques, sommets éclairés ambre / rose par l'horizon, bases bleu sombre, cœur sombre), plan lointain flou
  et bleuté, dérives à vitesses différentes et lente déformation ; nouvelle miniature

## [3.14.3] - 2026-11-09 - Sakura plus réaliste
- Profil Sakura 1.1 : cerisier redessiné, généré par ramification (tronc, branches maîtresses, rameaux),
  écorce à lenticelles éclairée par la lune ; floraison détaillée (fleurs à 5 pétales échancrés en dégradé,
  étamines, bourgeons, jeunes feuilles bronze), en deux couches de profondeur, éclairage côté lune ; ciel
  étoilé, collines dans la brume, lune en relief, pétales tombés au sol
- Plus fluide : seules les branches poussent dans l'image, les fleurs éclosent en CSS (opacity / transform) ;
  les pétales qui tombent sont des images fixes déplacées (aucun redessin), avec un léger balancement et une
  seconde couche de pétales proches sur le panel
- Transition de 2,2 s : environ trois fois plus de pétales, en trois nuées de profondeurs différentes, sans
  filtre de flou ; versions allégées sur téléphone et sans animation

## [3.14.2] - 2026-11-08 - Dés du destin : jauges en traits de feu
- Profil Dés du destin 1.2 : les jauges deviennent des traits de feu lancés comme un sort (cœur brûlant,
  flammes qui filent vers l'arrière en remontant, étincelles en traîne, tête embrasée qui palpite au bout),
  rouge sombre / orange / orange vif selon le niveau ; jauges plus fines (22 px au lieu de 34, températures,
  musique et mélangeur aussi) ; lueur sans filtre recalculé à chaque image

## [3.14.1] - 2026-11-08 - Dés du destin : jauges de feu, intro du brasero
- Profil Dés du destin 1.1 : jauges CPU, RAM, GPU, températures, disques, musique et mélangeur en tubes de
  verre remplis de FEU (trois couches de flammes, étincelles ; rouge, orange, blanc chaud selon le niveau),
  valeur en gros sur fond sombre ; l'animation du feu ne repart plus à chaque mise à jour des jauges
- Disques : longues fioles sur toute la largeur, lettre et pourcentage en gros, espace libre dessous,
  liseré ambré « presque plein »
- Intro de 9 s : une braise s'allume, le brasero et les torches s'embrasent, la salle s'éclaire, le dé roule
  dans la lumière orangée jusqu'au 20, onde de chaleur et étincelles, puis le logo ; fil rouge de sort qui
  ondule en fond, derrière les cartes. Versions fixes sur téléphone, en mode jeu et sans animation
- Panel : chaque jauge expose sa valeur aux profils (`--valeur`, `data-niveau`), voir FORMAT.md § 4.8

## [3.14.0] - 2026-11-08 - Mur libre, post-it, détail des stats, interface réorganisable
- Souvenirs : mur libre PAR JOUR. Chaque photo et chaque note se déplace (poignée ⠿, ou la photo à la souris)
  et se redimensionne (coin ◢), avec taille mini / maxi ; le dernier touché passe devant (superposition
  volontaire possible) ; souris, doigt et clavier (flèches, Maj + flèches). Disposition enregistrée par jour
  dans la base (jour, élément, x, y, largeur, hauteur, z) ; un jour jamais arrangé reçoit une grille propre.
  Boutons « Réorganiser automatiquement » et « Annuler la dernière modification ». Même mur sur le
  téléphone, réduit (55 % minimum, défilement de côté dans son cadre)
- Souvenirs : notes façon post-it sans photo (texte modifiable sur la note et enregistré pendant l'écriture,
  6 couleurs pastel accordées au mode et au profil, taille du texte, suppression) ; option « épingler » : la
  même note se répète sur les jours suivants (désactivée par défaut)
- Statistiques : cadre « Détail du jour » (début, fin, actif, inactif, frise par heure, CPU / GPU moyens et
  pics, temps par catégorie, par jeu, musique et médias, par appli), navigation jour précédent / suivant /
  Aujourd'hui / date, clic sur une barre de l'activité par jour ; message clair pour un jour sans données
- Statistiques : option `"mode": "ouverte"` dans jeux.json (compte tant que l'appli est ouverte ET que tu es
  actif) ; Claude (`claude.exe`) ajouté en « travail », et une ligne d'exemple (Notion) à adapter
- Journal : vue mois plus grande et redimensionnable ; les émojis des activités cochées s'affichent en petit
  autour du visage d'humeur (arc ou cercle, « +N » avec la liste au survol au-delà de 8), aussi dans la vue mois
- Toutes les catégories (Sommaire, PC, Média, Deck, Lanceur, Réseau, Agenda, Souvenirs, Statistiques,
  Journal) : chaque bloc se déplace et se redimensionne avec le même moteur que l'agenda (aimant léger,
  pas de chevauchement accidentel, clavier) ; disposition retenue par catégorie, par appareil et par mode ;
  boutons Verrouiller et Réinitialiser la disposition dans chaque catégorie. La mise en page d'origine est
  gardée tant que rien n'est déplacé. L'ancienne disposition de l'agenda est reprise
- Base de données : migrations 2 et 3 (tables des notes et des dispositions ; disposition par défaut pour
  les photos existantes), avec copie de sauvegarde automatique avant migration

## [3.13.0] - 2026-11-08 - Profil Dés du destin
- Nouveau profil visuel « Dés du destin » (Terminal et Sentinelle) : salle de donjon aux murs de pierre et
  vieilles poutres, torches qui vacillent, braises qui montent et brume au sol, grands dés rouges translucides
  aux chiffres dorés qui flottent en tournant avec une lueur qui bat comme un cœur ; cartes en pierre sombre à
  bordure d'or gravée, runes qui s'allument une à une, coins ornés ; jauges en barres de lave ; au survol d'un
  bouton, un mini-dé tourne et les runes s'embrasent ; alertes au pulse ambré, critiques avec un dé qui tremble
- Intro de 5 s : un dé rouge roule et rebondit dans le noir, s'arrête sur 20, la salle s'éclaire en écarlate,
  un cercle de runes s'allume, puis le logo NEXUS apparaît dans un éclat ; transition de 1,4 s
- Polices libres Uncial Antiqua (titres) et Inter (textes et chiffres) incluses, avec leurs licences OFL
- Nouveaux états pour les profils : `body[data-alerte]` (aucune, normale, critique) et
  `body[data-alerte-evenement]` (nouvelle-critique, resolue) pendant 3 s, documentés dans FORMAT.md § 4.6
- Un profil dont le CSS désigne un fichier d'assets/ manquant est maintenant considéré comme invalide : le panel
  revient au profil Défaut au lieu d'afficher un profil à moitié chargé

## [3.12.0] - 2026-11-08 - Profil Pluie d'étoiles
- Nouveau profil visuel « Pluie d'étoiles » (Terminal et Sentinelle) : ciel indigo et violet, voie lactée
  qui respire, étoiles qui scintillent sur deux profondeurs, étoiles filantes espacées, nuages sombres aux
  bords ambrés et rosés qui dérivent, montagnes aux arêtes bleu glacier avec de la brume, parallaxe au
  défilement ; cartes et boutons en verre sombre, étoiles à quatre branches aux coins, éclat glacé au survol,
  barres et jauges avec halo bleuté, alertes au pulse ambré (rouge discret si critique)
- Polices libres Cinzel (titres) et Inter (textes et chiffres) incluses, avec leurs licences OFL
- Intro de 4,6 s : le ciel s'illumine, les étoiles apparaissent, des étoiles filantes passent, puis le logo
  NEXUS surgit avec un éclat ; transition d'1,5 s vers les étoiles au clic sur NEXUS
- ⚙ Réglages : case « Jouer l'intro animée des profils visuels » (par appareil) pour couper toutes les intros
- Export d'un profil : les licences et notes (.txt, .md) à la racine du profil sont maintenant incluses

## [3.11.0] - 2026-11-08 - Souvenirs, statistiques personnelles et journal
- Nouvelle catégorie Souvenirs : le jour en grand et l'heure, mur de photos par jour (glisser-déposer ou bouton,
  aussi depuis le téléphone), légende, déplacement vers un autre jour, suppression ; calendrier, frise,
  « Ce jour-là » (mêmes dates les années passées), diaporama aléatoire ; JPG / PNG / WebP vérifiés, 25 Mo max,
  miniatures, métadonnées EXIF et position GPS retirées par défaut (option pour les garder)
- Nouvelle catégorie Statistiques : temps actif / inactif, sessions, temps par jeu et par catégorie (jeux.json),
  musique et vidéo comptées seulement pendant une lecture, charge CPU / GPU par heure ; aujourd'hui, 7 et 30 jours ;
  pause, durée de conservation, tout effacer ; uniquement des noms de processus et des durées
- Nouvelle catégorie Journal : humeur, activités (config.json), texte enregistré pendant l'écriture, vue mois,
  recherche, export Markdown / texte, option mot de passe avant d'ouvrir
- Données locales dans data\ (base SQLite data\nexus.db avec migrations, photos dans data\souvenirs\),
  exclues du partage et de Git ; jamais lues par le bot Discord ; réponses jamais mises en cache
- Onglet Horloges retiré (data\clocks.json conservé, plus utilisé)

## [3.10.0] - 2026-11-08 - Profil Sakura
- Nouveau profil visuel « Sakura » (modes Terminal et Sentinelle) : nuit prune ou bleu nuit, roses sakura,
  blanc crème, vert tendre ; cartes ornées de branches fleuries, boutons qui fleurissent au survol, barres
  qui poussent comme une branche avec un bourgeon au bout, pétales qui tombent lentement, éclat doux des alertes
- Intro Sakura sur la page de garde (une fois par session) : un cerisier pousse et fleurit, feuilles et
  pétales virevoltent, le logo NEXUS apparaît porté par les pétales ; « Passer l'intro », un clic ou une touche
- Au clic sur NEXUS : envol de 2 s à travers les pétales jusqu'au sommaire
- Pour tous les profils : état de la page de garde sur <body data-etat="intro | reconnexion | pret | veille |
  transition | panel"> et champ « animations » dans profil.json (durée de l'intro, transition remplacée),
  sans aucun JavaScript dans les profils ; documenté dans profils\FORMAT.md
- Animations réduites (réglage Windows) : la page de garde se ferme en simple fondu

## [3.9.0] - 2026-11-08 - Agenda modifiable, rappels, fenêtres et tailles
- Agenda : modifier un évènement ou un anniversaire (titre, date, heure, durée, description, répétition,
  date de fin, rappels) ; pour une série : « cet évènement seulement », « cet évènement et les suivants »
  ou « toute la série » (modifier comme supprimer) ; erreurs affichées sous chaque champ
- Rappels 1 h puis 30 min avant (réglables dans config.json et par évènement), calculés par le serveur :
  bannière dans le panel avec son, notification Windows, message Discord ; jamais en double, même après
  un redémarrage ; heure de référence 09:00 pour les anniversaires et les journées entières
- Fenêtres de l'agenda plus grandes, déplaçables et redimensionnables (souris et doigt), disposition
  mémorisée par appareil, boutons Verrouiller et Réinitialiser la disposition
- Menu ⚙ Réglages : taille du lanceur (125 %), du stream deck (115 %), du mélangeur (115 %) et de l'agenda,
  de 80 à 150 %, par appareil ; les profils visuels ne peuvent pas les annuler
- Nouveau format de l'agenda (format 2) : l'ancien fichier est sauvegardé dans data\backups\ puis converti
  sans perte ; les anniversaires deviennent des évènements « toute la journée »

## [3.8.1] - 2026-11-08 - Notes de version lisibles
- Corrigé : la note de la version actuelle s'affichait en colonne d'un mot de large (le curseur
  clignotant de l'en-tête et la version actuelle partageaient le même nom de style)
- Corrigé : les points écrits sur plusieurs lignes étaient coupés dans les notes de version

## [3.8.0] - 2026-11-08 - Cartes graphiques AMD et Intel
- Détecteur de carte graphique : NEXUS reconnaît toute carte branchée (NVIDIA, AMD, Intel) avec son nom et
  sa mémoire vidéo, et choisit tout seul la meilleure façon de la lire
- AMD / Intel : lues par LibreHardwareMonitor (charge, VRAM, température, point chaud, conso, fréquences,
  ventilateur) ; sans lui, charge et VRAM via les compteurs de Windows (comme le Gestionnaire des tâches)
- Toujours une seule carte « GPU » : chaque ligne s'affiche si la source la fournit ; la source utilisée
  (« lu par … ») et un conseil s'il manque la température sont indiqués sous la carte
- Carte dédiée affichée en premier quand il y a aussi un GPU intégré au processeur
- Bot Discord (/stats, /gpu), alertes et sommaire compatibles avec toutes les cartes
- Message de démarrage : carte détectée et source choisie

## [3.7.0] - 2026-11-08 - Profils visuels
- Menu 🎨 en haut, dans les deux modes : choix du profil visuel (couleurs, polices, fond, formes, effets),
  appliqué tout de suite sans recharger ; mémorisé par mode et par appareil ; aperçu des couleurs
- Profil « Défaut » intégré, non supprimable, utilisé automatiquement si un profil est cassé ou a disparu
- Dossier profils\ : un sous-dossier par profil (profil.json, style.css, assets\), détecté sans redémarrer
  (⟳ Actualiser, et mise à jour automatique du profil actif quand son style.css change)
- 3 profils d'exemple : Ardoise (sobre), Néon Minuit (Sentinelle), Phosphore (Terminal)
- profils\FORMAT.md (format complet, pensé pour Claude Code), profils\_modele\, valider_profil.py
- Exporter / Importer un profil en .zip (ou dossier glissé-déposé), avec choix Remplacer / Garder les deux
- Sécurité : CSS analysé et nettoyé (pas d'@import, d'adresse Internet, de data:, de « .. », d'expression(),
  de javascript:, de balise HTML, même cachés par des échappements), SVG sans script, 5 Mo maximum, types
  de fichiers limités, fichiers servis avec une politique anti-script ; mêmes protections réseau que le panel

## [3.6.1] - 2026-11-08 - Démarrage fiable
- Corrigé : « Ce site est inaccessible » (ERR_CONNECTION_REFUSED) au lancement : le navigateur s'ouvrait
  après 3 s fixes, avant que NEXUS soit prêt (surtout au premier lancement ou sur un PC plus lent).
  NEXUS ouvre maintenant lui-même le navigateur dès que le serveur répond
- Le diagnostic matériel ne retarde plus le démarrage du serveur
- Port 8000 déjà utilisé : message clair au lieu de 5 redémarrages inutiles
- La fenêtre noire rappelle de rester ouverte ; dépannage du README complété

## [3.6.0] - 2026-11-08 - Partage
- installer.bat : vérifie Python (3.10+), crée l'environnement .venv, installe les dépendances,
  vérifie le matériel, lance l'assistant et propose un raccourci sur le Bureau
- Assistant de première configuration (configurer.bat) : mot de passe du deck (seule une empreinte
  est enregistrée), bot Discord facultatif (jeton, ton ID, salon) ; crée config.json et deck.json
- Au démarrage, message clair si aucun GPU NVIDIA ou si LibreHardwareMonitor est absent / ne répond pas
- preparer_partage.bat : copie propre dans partage\ (dossier + zip), sans config, données, sessions,
  journaux ni sauvegardes, avec vérification automatique qu'aucun secret ne s'y trouve
- README réécrit pas à pas pour débutant, licence MIT, NE_PAS_PARTAGER.md, .gitignore complété
- Noms des ventilateurs déplacés dans data\ (avec les autres données personnelles)

## [3.5.0] - 2026-11-08 - Terminal devient Ultron
- Le thème Terminal prend le look Ultron en rouge (rouge incandescent, chrome argenté, alvéoles,
  œil qui balaie) à la place de l'ancien vert phosphore
- Sentinelle reste en orange avec des touches de bleu
- Glitch vers Terminal : « PRISE DE CONTRÔLE… » puis « CONTRÔLE ACQUIS »
- Correction du glitch : l'animation attend que la page soit dessinée avant de la dévoiler

## [3.4.0] - 2026-11-08 - Transitions de thème
- Sentinelle passe à l'orange (armure) avec des touches de bleu holographique : boutons, carte Média,
  reflets de l'œil, liseré de l'onglet actif, halo en bas à droite ; titres en chrome doré
- Sentinelle → Terminal : animation de glitch (tremblement, couleurs séparées, bandes corrompues, bruit,
  « SIGNAL CORROMPU »), puis « root@nexus:~# accès rétabli »
- Terminal → Sentinelle : le terminal se dérègle, puis « correction du glitch » : une ligne orange et bleue
  balaie l'écran de haut en bas et répare tout sur son passage, jusqu'à « SYSTÈME STABILISÉ »
- Animations désactivées si Windows demande de réduire les animations

## [3.3.1] - 2026-11-08 - Sentinelle aux couleurs JARVIS
- Le thème Sentinelle garde son style (chrome, alvéoles, œil qui balaie) mais passe aux couleurs JARVIS :
  bleu holographique, touches or, fond bleu nuit, titres en chrome bleuté
- Températures trop chaudes de nouveau en rouge (bien visibles sur le bleu)

## [3.3.0] - 2026-11-08 - Thème Sentinelle
- Nouveau thème « Sentinelle » inspiré d'Ultron : rouge incandescent, titres en métal chromé, logo argenté,
  fond en alvéoles métalliques, « œil » rouge qui balaie sous l'en-tête, onglets en plaques biseautées
- Bouton « ◐ Thème » dans la barre du haut pour passer de Terminal (vert) à Sentinelle (rouge) ;
  le choix est mémorisé (séparément sur le PC et sur le téléphone)
- Page de garde et pluie de code aux couleurs du thème choisi
- Couleurs du panel centralisées en variables (facile d'ajouter d'autres thèmes)

## [3.2.0] - 2026-11-08 - DA hacking
- Nouvelle direction artistique « terminal de hacker » : vert phosphore en couleur principale,
  magenta et jaune gardés en touches cyberpunk, fonds vert-noir, grille et lignes de balayage vertes
- En-tête façon invite de commande (root@nexus:~#) avec curseur clignotant
- Onglets en [ COMMANDES ], titres de cartes en [01] >, raccourcis du sommaire en ./Nom, barres en blocs
- Textes agrandis partout (petits textes +2 px, titres et valeurs +8 à 15 %), sur PC comme sur téléphone
- Page de garde et pluie de code passées en vert

## [3.1.0] - 2026-11-08 - Commande d'aide Discord
- Nouvelle commande /command : liste de toutes les commandes du bot, des boutons utilisables avec /deck
  et des seuils d'alerte (réponse visible par toi seul)

## [3.0.1] - 2026-11-08 - Horloge stable
- Corrigé : à chaque seconde, l'horloge jaune changeait de largeur et décalait les voyants API / GPU / LHM
  et les boutons de la barre du haut (largeur fixe + chiffres à chasse fixe)
- Chiffres à chasse fixe aussi pour l'heure du sommaire, les horloges mondiales, la veille et les valeurs en direct

## [3.0.0] - 2026-11-08 - Bot Discord et stream deck
- Bot Discord (discord.py) dans le même programme : /stats, /disques, /gpu (lecture seule) et /deck,
  réservés à ton compte et à ton salon ; alertes automatiques (CPU, GPU, RAM, disque) avec anti-spam
  et message de retour à la normale ; NEXUS démarre même sans jeton ou avec un jeton invalide
- Stream deck : onglet « Deck » avec de gros boutons tactiles (3 par ligne sur téléphone), défini dans deck.json
- Actions en liste fermée : application, URL, touches multimédia, verrouillage, script du dossier actions/,
  éteindre / redémarrer / veille (confirmation obligatoire) ; le navigateur n'envoie que l'id du bouton
- Mode édition (ajouter, modifier, réordonner, supprimer) validé côté serveur ; journal logs/deck.log
- Deck protégé par mot de passe (config.json) avec limite de requêtes ; option "discord" pour /deck
- Configuration centralisée dans config.json (exclu de Git) avec config.example.json et .gitignore
- Code réorganisé : stats.py (capteurs), bot.py, deck.py, config.py, app.py (serveur)

## [2.9.1] - 2026-11-08 - Correctifs de la version mobile
- Corrigé : sur téléphone, la page glissait à gauche et à droite et montrait des zones noires
  (la ligne de volume du lecteur et le tableau des appareils élargissaient toute la page)
- Lecteur Média sur mobile : image en entier, cadre adapté au format (16:10 ou carré), commandes centrées,
  volume sur deux lignes
- Pochette jamais rognée (PC et mobile) : image entière sur un fond flou de la même image
- Fenêtre Version (et Téléphone) bien centrée et lisible sur mobile
- Champs de saisie en 16 px sur mobile (évite le zoom automatique de certains téléphones)
- Tableau des appareils : colonne MAC masquée sur mobile, défilement dans la carte

## [2.9.0] - 2026-11-08 - Accès depuis le téléphone
- Accès depuis le téléphone sur le Wi-Fi de la maison, désactivé par défaut (bouton « 📱 Téléphone » sur le PC)
- Appairage par QR code ou code à 6 chiffres (valable 2 min, usage unique, 5 essais max, essais limités par minute)
- Seuls les appareils appairés accèdent à NEXUS ; adresses Internet toujours refusées ; jetons stockés hachés ;
  liste des appareils avec renommage et révocation ; réglages réservés au PC
- Protection contre le « DNS rebinding » (en-tête Host vérifié), y compris pour le PC
- Version mobile : onglets qui défilent au doigt, boutons plus grands, mise en page en une colonne
- Icône NEXUS pour « Ajouter à l'écran d'accueil » du téléphone
- Corrigé : cartes floues sur les écrans haute densité après leur animation d'apparition

## [2.8.1] - 2026-11-08 - Effet matrice et transitions fluides
- L'entrée devient une pluie de code façon « matrice » de 4 s, sur 3 profondeurs (katakana et hexadécimal,
  cyan / magenta / jaune), avec le mot NEXUS qui se forme dans la pluie
- Fondu enchaîné page de garde → matrice : la page recule et floute par-dessus la pluie déjà opaque
  (le sommaire n'apparaît plus en transparence)
- Ouverture matrice → sommaire : un cercle aux bords doux s'agrandit depuis le centre, la pluie ralentit,
  les tuiles du sommaire arrivent en cascade
- Rendu identique à 60 Hz, 144 Hz ou plus (traînées calculées selon le temps écoulé)

## [2.8.0] - 2026-11-08 - Page de garde interactive et plongée dans le réseau
- La page de garde reste affichée : on entre en cliquant sur NEXUS (logo ou titre), ou avec Entrée / Espace
- Le logo NEXUS de l'en-tête ramène à la page de garde (reconnexion rapide)
- Mise en veille après 45 s sans activité : l'écran s'éteint comme un tube cathodique (heure, voyant, logo qui respire)
  et se rallume avec effet d'allumage dès qu'on bouge la souris ou appuie sur une touche
- Nouvelle animation d'entrée : plongée dans un tunnel d'hexagones et de flux de code hexadécimal,
  traits de vitesse, glitch et flash, puis arrivée sur le sommaire

## [2.7.0] - 2026-11-08 - Page de garde
- Écran de démarrage animé : emblème NEXUS tracé au néon, titre aux lettres brouillées qui se verrouillent,
  grille en perspective, balayage lumineux
- Journal de démarrage avec de vraies vérifications (CPU, RAM, GPU, capteurs, sortie audio, réseau, mode jeu)
- « ACCÈS AUTORISÉ » puis ouverture en volets sur le sommaire ; clic ou touche pour passer
- Une fois par lancement (pas à chaque rechargement) ; lien « Rejouer l'intro » dans le sommaire
- Nouveau logo NEXUS : en-tête, onglet du navigateur et icône du raccourci du bureau

## [2.6.0] - 2026-11-08 - NEXUS et sommaire
- Le panel s'appelle désormais NEXUS (titre, onglet du navigateur, raccourci du bureau)
- Nouvel écran Sommaire : une tuile par catégorie avec un aperçu en direct (CPU/GPU, lecture en cours,
  dernier jeu avec bouton « Jouer », ping, prochain événement, heures dans le monde)
- Accès direct aux sous-parties (ex. PC → GPU, Réseau → Appareils) : la carte visée est mise en évidence
- Bouton « ◀ Retour », onglet « ⌂ Sommaire », logo cliquable et touche Échap pour revenir au sommaire
- Les liens directs fonctionnent aussi en favori (ex. 127.0.0.1:8000/#reseau/appareils)

## [2.5.1] - 2026-11-07 - Correctif : plantage en réglant le son
- Corrigé : le serveur plantait (« Failed to fetch », API en rouge) en bougeant les curseurs de son
  (objets audio Windows libérés depuis le mauvais thread, et libérés deux fois pour le vumètre général)
- lancer.bat redémarre automatiquement le serveur en cas d'arrêt inattendu (5 fois max)

## [2.5.0] - 2026-11-07 - Volume et mélangeur de son
- Curseur de volume dans le lecteur pour la source en cours (Spotify, navigateur…)
- Mélangeur de son dans l'onglet Média : volume général de la sortie audio + volume et muet par application
- Vumètres en direct pour chaque application
- Icônes réelles des applications dans le mélangeur

## [2.4.0] - 2026-11-07 - Mode jeu
- Détection automatique des jeux (Steam, Riot, Rockstar, Epic, Xbox…, Valorant malgré l'anti-triche)
- Badge « MODE JEU » dans la barre du haut
- Panel allégé pendant les parties : scans en pause, animations coupées, rafraîchissement toutes les 2 s
- Option : bascule automatique du plan d'alimentation (désactivée par défaut)
- Système de versions : numéro de version, notes de version, sauvegarde automatique, restauration

## [2.3.0] - 2026-11-07 - Thème cyberpunk avancé
- Fond néon avec grille en perspective et lignes de balayage
- Titre « glitch », onglets inclinés, cartes à bordure dégradée et numérotées
- Police d'affichage condensée et aberration chromatique sur les chiffres
- Barres animées, alertes à bandes de danger

## [2.2.0] - 2026-11-07 - Agenda : répétitions et anniversaires
- Événements répétés : chaque jour, semaine, mois ou année
- Anniversaires avec calcul de l'âge et rappel à 9 h
- Suppression d'une seule occurrence ou de toute la série

## [2.1.0] - 2026-11-07 - Claude dans le panel
- Bouton « ✦ Claude » dans la barre du haut
- Tuiles Claude et claude.ai dans le lanceur

## [2.0.0] - 2026-11-07 - Onglets
- Onglet Média : Spotify, YouTube et tout lecteur Windows (jaquette, progression, contrôles)
- Onglet Lanceur : jeux Steam avec jaquettes, applications avec icônes
- Onglet Réseau : ping, qualité, coupures, test de débit, appareils connectés
- Onglet Agenda : calendrier, to-do, notes
- Onglet Horloges : horloge mondiale

## [1.4.0] - 2026-11-07 - Noms des ventilateurs
- Renommage des ventilateurs directement dans le panel

## [1.3.0] - 2026-11-07 - Processus, énergie et alertes
- Top des processus (CPU et RAM)
- Ventilateurs, consommation CPU/GPU, fréquences
- GPU détaillé (watts, fréquences, ventilateur, bridage)
- Alertes avec notifications Windows

## [1.2.0] - 2026-11-07 - Températures CPU, réseau et style
- LibreHardwareMonitor intégré et démarré automatiquement
- Débits Ethernet en direct
- Premier style cyberpunk

## [1.1.0] - 2026-11-07 - Démarrage fiable
- lancer.bat trouve Python même hors du PATH
- Raccourci « Panel PC » avec icône

## [1.0.0] - 2026-11-07 - Première version
- CPU, RAM, GPU, disques et températures en temps réel
