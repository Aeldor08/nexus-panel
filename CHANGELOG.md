# Changelog

Toutes les évolutions notables de NEXUS sont notées ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et la numérotation
[Semantic Versioning](https://semver.org/lang/fr/) : **majeur.mineur.correctif**. Le fichier `VERSION`, à la
racine, est la source de vérité ; `outils/release.py` le fait avancer et complète ce journal.

## [Non publié]

### Ajouté
- **Philibert**, un petit iguane vert virtuel (compagnon façon tamagotchi, dessins et règles originaux) : il se promène dans un couloir sous la barre du haut (sans jamais recouvrir un bouton ; seul son corps est cliquable), marche (toujours tourné vers là où il va : demi-tour avant de changer de sens), s'arrête, regarde autour de lui, cligne des yeux, hoche la tête, agite son fanon, se dore au soleil, dort la nuit, et montre son humeur dans une bulle (cœur, « ! » quand il a besoin de soin, Zzz, nuage s'il est malade)
- Son **île** (clic sur lui, ou ⚙ Réglages → Ouvrir son île) : plage, palmier où il dort, rocher chaud, flaque, mer turquoise et vagues, crabes, mouettes, ciel à l'heure réelle (aube, jour, coucher, nuit étoilée) et météo de l'île (nuages, pluie, arc-en-ciel) ; jauges (faim, bonheur, énergie, propreté, santé, chaleur), poids, âge, « ce qui ne va pas »
- Soins : nourrir (100 % végétal : verdure, légumes, fleurs ; fruits en friandises à limiter ; insectes, viande et croquettes refusés avec une astuce), chauffer au soleil ou sous une lampe chauffante (sang froid), éteindre la lumière la nuit, bain tiède ou de mer, nettoyer, soigner, caresser, féliciter, gronder doucement (caprices et vrais besoins)
- Philibert **ne meurt jamais** : malade trop longtemps, la tortue vétérinaire l'emmène en barque se reposer 12 à 24 h (jauges figées) ; il revient en forme avec une carte postale qui explique ce qui lui a manqué et donne un conseil ; pension chez la voisine pendant les longues absences ; mode vacances
- Évolution œuf → bébé → juvénile → adulte → vieux sage, avec une variante selon les soins (le Royal, le Gourmand, le Nageur, le Convalescent, l'Insulaire) ; mues, évènements de l'île
- Mini-jeux (Pluie de feuilles, Gauche ou droite ?, Le hochement), coquillages, boutique (nourriture, remède, lampe, accessoires, déco), garde-robe, carnet (historique, statistiques, 23 succès, cartes postales, 20 fiches « Le savais-tu ? »)
- **Saisons de l'île** selon le mois réel (printemps, été, saison des pluies, saison fraîche) : météo, chaleur, produit de saison moins cher à la boutique, décor (hibiscus et papillons, étoiles de mer, noix de coco tombées, bois flotté, guirlande en décembre), 2 fiches « Le savais-tu ? » et le succès « Les quatre saisons »
- 4e mini-jeu **Course au rocher chaud** : sauter les crabes et les noix de coco, attraper les rayons de soleil, éviter l'ombre des nuages ; il part avec sa vraie chaleur et finit étalé sur le rocher de l'île ; succès « Coureur du soleil »
- **Album** du carnet : une photo de chaque étape de sa vie, et les Philibert d'avant (gardés quand on recommence avec un nouvel œuf)
- **Tuile Philibert sur le sommaire** : humeur, besoin principal, âge, coquillages, et accès directs (Nourrir, Jouer, Boutique, Carnet)
- Animations et design revus : marche de lézard (pattes en diagonale et en deux segments, corps qui ondule, queue en S, vitesse accordée aux pas), respiration, petit saut au clic ; palmes au vent, écume, reflets, rayons du soleil, étoiles qui scintillent, lucioles ; cœurs, miettes, gouttes et étoiles autour de lui ; jauges en cartes, bulle de paroles, tuiles d'actions à icônes dessinées, palette de nuit
- **Dessin réaliste** de Philibert, de son île et de ses objets (d'après de vraies descriptions d'espèces et des photos de lagons) : iguane naturaliste (grande écaille ronde sous l'oreille, fanon dentelé, crête d'épines, queue annelée, longs doigts griffus, texture d'écailles ; il fonce quand il a froid), œuf de reptile dans son nid ; ciel voilé à l'horizon, cumulus à base plate, lune à sa vraie phase, Voie lactée ; mer en perspective qui miroite, reflets sous le soleil ou la lune, lagon turquoise, dentelle d'écume ; cocotier annelé aux palmes pennées, rocher volcanique, herbes des dunes, liseron de mer, ombres portées selon le soleil ; crabes fantômes, goélands, frégate, papillons ; aliments, objets, carte postale et pancarte dessinés comme les vrais ; mêmes dessins dans les mini-jeux ; fenêtre de l'île plus grande, scène sur toute la largeur (plus de bandes sur les côtés), Philibert du haut 20 % plus grand
- Réglages de Philibert : affichage en haut, vitesse du temps, sons, notification Windows ou Discord (facultatives, jamais en mode jeu), mode vacances, nouvel œuf (double confirmation)
- Moteur côté serveur (`philibert.py`, routes `/api/philibert…`) : temps qui passe même NEXUS fermé, valeurs et récompenses calculées par le serveur (anti-triche), données dans `data\philibert.json` ; moments marquants dans le journal d'activité (catégorie « Philibert ») ; tests `outils/tests/test_philibert.py`

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
