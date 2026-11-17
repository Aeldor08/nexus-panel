# Philibert, l'iguane de NEXUS — conception

Philibert est un petit iguane vert qui vit dans NEXUS : il se promène le long de la barre du haut et, quand on
clique sur lui, on rejoint son île au milieu de la mer pour s'occuper de lui. C'est un compagnon façon
« tamagotchi-like », entièrement original (dessins SVG, sons de synthèse, noms et règles écrits pour NEXUS).

Deux principes guident toutes les règles :

- **A — Philibert ne meurt jamais.** Aucun « game over », aucun texte culpabilisant. Au pire, une tortue
  vétérinaire vient le chercher en barque pour qu'il se repose ; il revient en forme avec une carte postale qui
  explique gentiment ce qui lui a manqué.
- **B — C'est un vrai iguane vert** : herbivore (il refuse insectes, viande et croquettes) et lézard à sang froid
  (jauge de CHALEUR, soleil, lampe chauffante). Les fiches « Le savais-tu ? » ne contiennent que des faits vrais
  et simples, jamais de conseil vétérinaire réel.

## 1. Fichiers

| Fichier | Rôle |
|---|---|
| `docs/PHILIBERT-REGLES.md` | Toutes les règles chiffrées, pour l'administrateur (jauges par heure, chaleur selon la météo, soleil ou lampe, soins, jeux) |
| `philibert.py` | Moteur du jeu : temps qui passe, jauges, santé, vétérinaire, évolution, boutique, mini-jeux, succès. Aucune dépendance au reste de NEXUS (horloge et notifications injectables) |
| `app.py` | Routes `/api/philibert…` (minces : tout est calculé par le moteur) |
| `data/philibert.json` | État de Philibert (sur ce PC uniquement, hors Git, listé dans `NE_PAS_PARTAGER.md`) |
| `static/js/philibert.js` | Philibert qui se promène en haut de la page + sa bulle |
| `static/js/philibert-dessin.js` | Le dessin SVG de Philibert (stade, variante, humeur, accessoires, pose), d'après l'anatomie de l'iguane vert |
| `static/js/philibert-nature.js` | Les éléments de nature réalistes partagés par l'île et les mini-jeux (cocotier, nuages, oiseaux, crabe fantôme, papillons, rocher, noix de coco, feuilles, hibiscus, scarabée) |
| `static/js/philibert-ile.js` | L'île (fenêtre), les soins, la boutique, la garde-robe, le carnet, les réglages |
| `static/js/philibert-jeux.js` | Les quatre mini-jeux |
| `static/js/philibert-icones.js` | Les icônes dessinées de l'île (actions, jauges, météo, saisons, son) |
| `static/js/home.js` | La tuile « Philibert » du sommaire (humeur, besoin, âge, coquillages, accès directs) |
| `static/philibert.css` | Styles (l'île garde son propre univers de couleurs, lisible avec tous les profils) |
| `outils/tests/test_philibert.py` | Tests sans navigateur (horloge simulée), inscrits dans `run_all.py` |

## 2. Le temps

- L'état est **calculé par le serveur** à partir des horodatages : NEXUS fermé, le temps passe quand même.
  À chaque lecture, le moteur rejoue le temps écoulé par pas de 10 minutes (au plus 3 jours rejoués : au-delà,
  Philibert est déjà en pension, voir § 6).
- Heure **réelle locale** du PC. Phases du ciel : aube 6 h–8 h, jour 8 h–18 h, coucher 18 h–21 h, nuit 21 h–6 h.
  Philibert **dort de 21 h à 7 h** en haut du palmier.
- **Vitesse** : normale (×1) ou lente (×0,5 : jauges et âge avancent deux fois moins vite).
- **Rythme ralenti la nuit** : pendant son sommeil, faim et bonheur baissent trois fois moins vite.
- **Absence** : si personne ne s'est occupé de lui depuis plus de 8 h, tout baisse deux fois moins vite et les
  jauges ont des **planchers** (faim 20, bonheur 25, propreté 20, chaleur 20, énergie 20 ; santé jamais sous 5).
- **Météo** de l'île : déterministe (même météo sur le PC et le téléphone), par tranches de 2 h : soleil, nuages,
  pluie (jamais deux tranches de pluie de suite), arc-en-ciel la tranche qui suit une pluie. Les proportions
  dépendent de la saison (ci-dessous).
- **Saisons de l'île** : elles ne suivent **pas** le calendrier réel. Chaque île a son roulement : une saison dure
  de 2 à 7 jours (au hasard, reproductible), puis une autre lui succède (jamais la même deux fois de suite) ; huit
  saisons (chiffres complets dans `docs/PHILIBERT-REGLES.md`) : printemps, été, saison des pluies, saison fraîche,
  grande floraison, saison des tempêtes, saison des brumes, ponte des tortues. Chacune change la météo, la chaleur,
  le produit de saison et le décor. Fiches « Le savais-tu ? » de saison ; succès « Quatre saisons » et « Tour des
  saisons » (les huit). La guirlande de décembre reste liée au vrai mois de décembre.
- **Sieste sur le rocher** : fatigué en plein soleil, il fait sa sieste à plat ventre sur le rocher chaud et s'y
  réchauffe ; des « z z Z » montent au-dessus de sa tête dès qu'il dort (sable, rocher ou palmier).
- **Mutations de couleur** : à chaque mue, sa peau peut changer selon sa vie (alimentation, soleil, bains, jeux,
  froid, maladies soignées trop tard, nuits réveillées…) : Émeraude, Orangé, Doré, Turquoise, Mélanique, Cendré,
  Arlequin, Lunaire, et le très rare Leucique ; trois intensités ; onglet « Couleurs » du carnet.

## 3. Les jauges (0 à 100)

| Jauge | Baisse (par heure, éveillé, vitesse normale) | Remonte avec |
|---|---|---|
| Faim (100 = rassasié) | −5 (−2,5 s'il a froid : il digère lentement) | repas de verdure, légumes, fleurs, fruits |
| Bonheur | −3 (−2 s'il est bien chaud) | jeux, caresses, félicitations, bain de mer, fleurs, friandises |
| Énergie | −4 éveillé ; +14/h en dormant (+7 si la lumière reste allumée) | sommeil, sieste |
| Propreté | −1,5, et −2 de plus par crotte présente | nettoyer, bain |
| Santé | voir § 5 | bons soins, remède, repos au chaud |
| Chaleur | tend vers la température de l'endroit où il est (§ 4) | rocher au soleil, lampe chauffante |

Autres valeurs : **corpulence** (50 = idéale ; « ventre rond » au-dessus de 75), d'où un **poids** affiché en
grammes selon le stade ; **âge** en jours (le temps chez le vétérinaire ou en pension ne compte pas) ;
**discipline** (0–100) ; **UV** (cachée : soleil reçu ces derniers jours).

## 4. Sang froid : la chaleur

La chaleur se rapproche de la « température cible » de l'endroit où il est (vite quand il se réchauffe, plus
lentement quand il refroidit) :

| Endroit | Soleil | Nuages | Pluie | Nuit |
|---|---|---|---|---|
| Rocher chaud (« Chauffer ») | 95 | 70 | 45 | 30 |
| Plage (par défaut le jour) | 62 | 52 | 38 | 25 |
| Palmier (il y dort) | — | — | — | 28 |
| Sous la lampe chauffante allumée | au moins 76 le jour, 72 la nuit | | | |

- **Chauffer** : il va sur le rocher, se met à plat ventre et revient à la plage tout seul quand il a assez chaud
  (≥ 92) ou au bout de 2 h. À l'aube et au coucher, le rocher au soleil donne 65.
- **Lampe chauffante** (boutique, 40 coquillages) : à céramique, elle chauffe sans éclairer — il peut dormir
  dessous. Indispensable les jours de pluie et les nuits.
- **Froid** (chaleur < 35) : lent, peu d'appétit (un repas ne nourrit qu'à 60 %), tombe malade plus facilement.
  Il fonce un peu de couleur (comme un vrai iguane qui absorbe mieux la chaleur).
- **Chaud** (≥ 70) : actif, joueur (bonheur qui baisse moins vite, jeux un peu plus généreux).
- **UV** : chaque heure au soleil sur le rocher la recharge (+25/h, +10 sous les nuages). Elle baisse de 1,2/h ;
  sous 25, la santé baisse doucement (« il manquait de soleil » : le soleil aide à des os solides).

## 5. Santé, maladie, vétérinaire (principe A)

États progressifs, toujours visibles dans la liste « Ce qui ne va pas » :
**en forme → fatigué / grognon → malade → parti se reposer chez le vétérinaire**.

- **Santé** : +1,5/h quand tout va (faim ≥ 35, propreté ≥ 35, chaleur ≥ 40, corpulence ≤ 75, UV ≥ 25).
  Baisse : faim < 20 (−2,5/h), propreté < 25 (−1,5/h), chaleur < 35 (−2/h), ventre rond > 78 (−0,8/h),
  UV < 25 (−0,6/h), énergie < 15 (−1/h). Chaque baisse est comptée dans des **causes** (froid, fruits, faim,
  propreté, soleil, fatigue) qui servent aux explications et à la carte postale.
- **Malade** quand la santé passe sous 35 (ou 5 friandises en 24 h : indigestion ; la santé descend alors à 34). La maladie porte le nom de la
  cause principale : rhume (froid), indigestion (fruits), faiblesse (faim), petite infection (propreté),
  os fragiles (soleil), épuisement (fatigue). Il tousse, devient vert pâle, bouge peu.
- **Guérir** : le **remède** (boutique, 8 coquillages) donne +25 de santé et guérit s'il est au chaud
  (chaleur ≥ 50) ; au froid il n'agit qu'à moitié (« réchauffe-le d'abord »). Le **repos au chaud** (chaleur ≥ 60,
  endormi ou énergie ≥ 40) fait remonter la santé de 1,2/h ; guéri tout seul à 60.
- **Vétérinaire** : malade pendant 18 h cumulées (ou santé au plancher pendant 3 h) → la tortue vétérinaire
  arrive en barque et l'emmène. Panneau « Philibert se repose chez le vétérinaire — retour dans X h ».
  Durée : 12 h + 4 h par cause importante, **24 h au plus**. Pendant ce temps, rien ne baisse.
- **Retour** : jauges remises à un bon niveau (faim 70, bonheur 65, énergie 80, propreté 90, santé 85,
  chaleur 75, ventre ramené vers l'idéal), et une **carte postale de la tortue** qui explique les deux causes
  principales et donne un conseil. Coût : 15 coquillages au plus, **jamais bloquant** (sans coquillages, la tortue
  offre la consultation).
- **Conséquence douce** : deux séjours ou plus orientent l'évolution vers « Philibert le Convalescent »
  (toujours mignon, avec son petit pansement). Un séjour empêche seulement « le Royal » ; tous les succès restent
  possibles.

## 6. Absences, pension, vacances

- **Mode vacances** (réglages) : Philibert part en pension chez la voisine (sa cabane est sur l'île d'à côté, à l'horizon).
  Tout est en pause : jauges, âge, maladie. On le fait revenir quand on veut.
- **Pension automatique** : si personne ne s'est occupé de lui depuis 3 jours (s'il est malade à ce moment-là, la
  tortue vétérinaire passe d'abord), ou s'il revient du vétérinaire sans que personne soit passé entre-temps, la
  voisine le prend en pension et s'occupe bien de lui : il t'attend en forme (jauges remontées à un niveau correct). Il n'y a donc jamais plusieurs séjours chez
  le vétérinaire d'affilée pendant une longue absence : **même après des semaines, Philibert va bien**.

## 7. Régime alimentaire (principe B)

| Catégorie | Aliments (prix en coquillages) | Effet |
|---|---|---|
| Repas du quotidien | trèfle de l'île (gratuit, illimité, +15), feuilles de pissenlit (2), feuilles de mûrier (3), chou vert (2), courge (3), haricots verts (3) | faim +25 à +32, santé +1, corpulence +1,5 à +2 |
| Fleurs | hibiscus (4), fleur de pissenlit (3, il adore) | faim +8/+12, bonheur +12/+15 |
| Friandises | mangue (5), papaye (5), figue (5), banane (8, rarement) | bonheur +20, faim +10, corpulence +6 à +8 |
| Refusés (jamais en boutique) | grillon, ver de farine, croquettes pour chat, jambon, poisson | il refuse avec une mimique et une astuce |

- **Variété** : au moins 3 verdures différentes dans ses 6 derniers repas → santé +3 en bonus.
- **Trop de fruits** : ventre rond, santé qui baisse, indigestion à 5 friandises en 24 h.
- Les aliments refusés n'apparaissent que comme **pièges** : insectes qui tombent dans « Pluie de feuilles », et
  évènements de l'île (un touriste oublie des croquettes, une mouette lâche un poisson). Les proposer à Philibert
  ne fait aucun mal : il refuse, et on débloque une fiche « Le savais-tu ? ».
- Il n'a plus faim au-dessus de 95 : il ne mange pas (rien n'est dépensé).
- **Crottes** : environ 3 h après un repas (au plus 4 au sol). S'il prend un bain juste avant, il la fait dans
  l'eau (vrai comportement d'iguane) : on change l'eau, rien à ramasser.

## 8. Autres soins

- **Bain tiède** (flaque) : propreté +35, santé +2 (une fois par jour), aide la mue. **Bain de mer / nager** :
  propreté +25, bonheur +10, énergie −10, chaleur −15, il compte pour « le Nageur ». 20 min entre deux bains.
- **Mue** : tous les 2 jours d'âge (bébé, juvénile), 5 jours (adulte), 7 jours (sage). Il pèle par morceaux,
  ça le gratte (bonheur −0,5/h) ; un bain la termine, sinon elle finit seule au bout de 30 h.
- **Lumière / dodo** : de 21 h à 7 h il dort en haut du palmier. Il faut **éteindre la lumière** (sinon il dort
  mal : énergie +7/h au lieu de +14, bonheur −0,5/h). La lumière se rallume à 7 h. Le réveiller (nourrir, bain,
  caresser) le rend **grognon** pendant 1 h (bonheur −8). On ne joue pas la nuit.
- **Sieste** : le jour, s'il tombe sous 15 d'énergie, il fait une sieste jusqu'à 50.
- **Attention / discipline** : il appelle (« ! » dans sa bulle) soit pour un **vrai besoin** (une jauge sous 30,
  malade, crottes, mue, froid), soit par **caprice** (de temps en temps, moins souvent quand la discipline monte).
  « Il veut jouer / il réclame de l'attention » (le besoin *ennui* et les caprices) n'apparaît **que si son bonheur
  est à 30 ou moins** (`SEUIL_ATTENTION`) : un caprice en cours disparaît dès qu'il est plus heureux ; la page applique
  la même règle (bulle « ! », pastille « Il t'appelle »).
  *Gronder (doucement)* un caprice : discipline +10. Gronder un vrai besoin : il est triste, et on lui montre ce qui
  ne va pas. *Féliciter* juste après une bonne action (repas de verdure, bain, retour du rocher) : discipline +4,
  bonheur +6. Ignorer un caprice deux heures : discipline +3 ; ignorer un vrai besoin : bonheur −5.
- **Caresser** : bonheur +4 (effet toutes les 2 min au plus), il agite son fanon.

## 9. Évolution

| Stade | Âge (jours de vie) | Apparence |
|---|---|---|
| Œuf | 10 premières minutes | œuf dans le sable chaud |
| Bébé | 0 à 2 j | grosse tête, petite queue |
| Juvénile | 2 à 7 j | plus long, crête qui pousse |
| Adulte | 7 à 30 j | variante choisie selon les soins |
| Vieux sage | 30 j et plus | même variante, teinte plus douce, barbichette de fanon |

Variante, décidée en devenant adulte (dans cet ordre) :
1. **le Convalescent** — 2 séjours ou plus chez le vétérinaire (petit pansement, écharpe) ;
2. **le Royal** — santé moyenne ≥ 80, bonheur moyen ≥ 70, ≤ 20 % de friandises, aucun séjour (couleurs orangées de parade des mâles : crête, fanon, pattes) ;
3. **le Gourmand** — ≥ 30 % de friandises ou ventre rond (tout rond, joues pleines) ;
4. **le Nageur** — au moins 8 bains de mer (crête bleutée, rayures marines) ;
5. **l'Insulaire** — sinon (le vert classique de l'île).

## 10. Mini-jeux (coquillages + bonheur)

Il faut qu'il soit éveillé, pas malade, avec au moins 15 d'énergie. Chaque partie : **énergie −8 prise au
lancement**, corpulence −2. On peut **abandonner** une partie (bouton « Abandonner », ou ✕) : aucun gain, et l'énergie
dépensée pour la lancer ne revient pas. Toutes les règles chiffrées : `docs/PHILIBERT-REGLES.md`.

1. **Pluie de feuilles** (30 s) : déplacer Philibert (souris, doigt ou flèches) pour attraper les feuilles et
   fleurs qui tombent du palmier en évitant les insectes (il les refuserait). Pendant la partie, la souris reste
   dans le cadre (verrouillage du pointeur du navigateur ; Échap, Alt+Tab ou la touche Windows la libèrent). Si le
   navigateur le refuse, la souris reste libre et un message le dit.
2. **Gauche ou droite ?** (5 manches) : deviner de quel côté il va tourner la tête. Le côté est tiré par le
   serveur *après* le choix.
3. **Le hochement** (jeu de mémoire et de rythme) : Philibert « parle » avec trois gestes, ceux d'un vrai iguane
   vert — petit hochement, grand hochement, fanon déployé ; il faut répéter sa suite (boutons, ← → ↓ ou 1 2 3).
   À chaque réussite, le serveur tire **une nouvelle suite au hasard**, plus longue d'un geste (de 3 à 10, jamais
   trois fois le même geste d'affilée), et Philibert va **de plus en plus vite** (un temps passe de 0,78 s à 0,34 s ;
   la vitesse est affichée). Le serveur refuse une réponse donnée avant la fin de la démonstration.
4. **Course au rocher chaud** (30 s au plus) : il court vers le rocher ; on saute (Espace, ↑, clic, doigt)
   par-dessus les crabes et les noix de coco ; les rayons de soleil le réchauffent (+1 point, il court plus vite),
   l'ombre des nuages le refroidit. Il part avec **sa vraie chaleur du moment**. Arrivé : il finit étalé sur le
   vrai rocher de l'île (chaleur +10). Récompense : rayons ÷ 3 (+3 s'il arrive), 10 au plus ; arrivée annoncée
   avant 22 s refusée par le serveur ; succès « Coureur du soleil » (arriver avec 15 rayons).

**Anti-triche** : partie ouverte par le serveur (jeton à usage unique), durée minimale vérifiée, score borné,
récompense calculée par le serveur, **60 coquillages par jour au plus** gagnés aux jeux.

## 11. Coquillages, boutique, garde-robe

- On commence avec 20 coquillages. On en gagne aux mini-jeux, en **ramassant** sur la plage (1 à 3, toutes les
  3 h), avec certains évènements et les succès.
- **Boutique** : aliments, remède (8), lampe chauffante (40, une fois), 15 accessoires et 9 décorations. Chaque objet
  a une **rareté** (`RARETES`) : *commun*, *rare*, *très rare*, *légendaire*. Les pièces rares sont faites à la main
  par les artisans de l'île voisine, en un seul exemplaire : c'est ce qui justifie leur prix.

  | Emplacement | Communs | Rares et plus |
  |---|---|---|
  | Tête | chapeau de paille 25, couronne d'hibiscus 30, bob de pêcheur 35 | tricorne de pirate 180 (rare), couronne d'or 450 (très rare), diadème de nacre 800 (légendaire) |
  | Yeux | lunettes de soleil 20, lunettes en cœur 45 | monocle doré 150 (rare) |
  | Cou | foulard 15, collier de fleurs 18, nœud papillon 30 | collier de perles 220 (rare), médaille d'or 400 (très rare), cape royale 900 (légendaire, posée sur le dos) |
  | Île | château de sable 12, coquillages 10, bouée 15, parasol 20, hamac 30 | statue tiki 120 et petit phare 260 (rares), coffre au trésor 500 (très rare), bénitier et sa perle 750 (légendaire) |

  Avec ≈ 60 coquillages par jour aux jeux et les ramassages, une pièce légendaire demande une bonne dizaine de jours.
  Les **soins essentiels ne sont jamais bloqués** : remède et nourriture restent à 10 coquillages au plus, le trèfle
  est gratuit et un séjour chez la vétérinaire ne demande jamais plus que ce qu'on a. Succès « Pièce de collection »
  pour un premier objet légendaire. Dans la boutique : ruban et bordure de couleur (bleu, violet, or ; reflet doré
  qui passe sur les pièces légendaires).
- **Garde-robe** : un accessoire par emplacement (tête, yeux, cou), visible sur l'île et en haut de la page. Placement
  vérifié sur chaque stade (bébé, juvénile, adulte, vieux sage) et chaque posture (debout, à plat au soleil,
  endormi) : chapeaux et couronnes posés sur le crâne, derrière les yeux ; colliers et foulard derrière l'écaille
  de la joue puis sous la gorge (un peu plus bas sur le vieux sage, à cause de ses bajoues) ; la cape se pose sur le
  dos, sous les pattes de devant, et suit la marche ; la médaille est plus petite sur le bébé.

## 12. Carnet

Historique (naissance, éclosion, maladies, séjours chez le vétérinaire, mues, évolutions… 300 lignes au plus),
statistiques (repas, friandises, bains, jeux, refus, séjours, saisons…), **succès** (24), **cartes postales** reçues,
fiches **« Le savais-tu ? »** débloquées (20), âge en jours.

**Album** : une photo de chaque étape de sa vie (éclosion, juvénile, adulte avec sa variante, vieux sage) et
les **Philibert d'avant** : quand on recommence avec un nouvel œuf, l'ancien part vivre sur une île voisine et
garde sa place dans l'album (portrait, dates, âge, repas, parties, mues, succès, séjours chez la tortue ; 30 au
plus). Un œuf qui n'a pas éclos n'y entre pas.

**Tuile du sommaire** : humeur, besoin principal, âge et coquillages, avec des accès directs (Nourrir, Jouer,
Boutique, Carnet). Elle reste là même si Philibert est masqué en haut de la page : c'est toujours une entrée vers
son île.

## 13. Notifications et réglages

- **Sur le PC seulement** : depuis le téléphone (accès réseau), Philibert n'apparaît pas (ni en haut, ni île, ni tuile,
  ni réglage) et le serveur refuse `/api/philibert…` (« réservé au PC »), comme les mises à jour.

- **Bulle** sur Philibert en haut de la page quand il a vraiment besoin de soin (« ! »), cœur quand il est
  heureux, « Zzz » la nuit, nuage gris quand il est malade.
- **Notification Windows** (facultative, via le navigateur, comme les alertes de NEXUS) quand il tombe malade ou
  part chez le vétérinaire — jamais en mode jeu. **Discord** (facultatif) via le bot de NEXUS s'il est configuré.
- **Bruits de l'île** (réglage *ambiance*, et bouton dans l'en-tête de l'île) : tout est synthétisé (Web Audio, aucun
  fichier) et très discret — houle et écume toujours, pluie (et tonnerre lointain en saison des pluies), vent par
  ciel couvert ou en saison fraîche, goélands le jour au soleil, grillons et petites grenouilles la nuit. Seulement
  quand l'île est ouverte, l'onglet visible, hors mode jeu et avec les petits sons activés ; coupés avec « réduire
  les animations ».
- **Couleurs de l'interface** (bouton lune/soleil dans l'en-tête de l'île, qui bascule entre clair et sombre, ou
  réglage *theme*) : *automatique* (sombre si le fond du profil du panel est sombre ou
  s'il fait nuit sur l'île), *clair* ou *sombre*. Contrastes vérifiés : texte ≥ 12 : 1, texte secondaire ≥ 7 : 1,
  pastilles et encadrés ≥ 7 : 1, rubans de rareté ≥ 5,8 : 1. La scène, elle, suit toujours l'heure de l'île.
  Le rafraîchissement automatique (toutes les 30 s) attend qu'on ait fini de choisir dans une liste ou une case d'un
  panneau ouvert (sinon la liste se refermait).
- **Réglages** : afficher/masquer Philibert en haut, vitesse (normale / lente), sons, notifications Windows,
  Discord, mode vacances, recommencer avec un nouvel œuf (double confirmation).

## 14. Données (`data/philibert.json`)

Un seul objet JSON (version `v: 1`), écrit de façon atomique : jauges, corpulence, UV, discipline, position,
lumière, lampe, crottes (+ crottes à venir), mue, maladie (+ causes), vétérinaire, vacances, appel, évènement,
coquillages, inventaire, accessoires, déco, statistiques, moyennes de soins, carnet, cartes, succès, fiches,
réglages, mini-jeu en cours. Le fichier n'est jamais envoyé ailleurs, jamais dans Git.

## 15. API

| Route | Rôle |
|---|---|
| `GET /api/philibert` | État calculé (jauges, humeur, besoins, météo, position…) |
| `GET /api/philibert/catalogue` | Aliments, boutique, succès, nombre de fiches |
| `GET /api/philibert/carnet` | Historique, statistiques, succès, cartes postales, fiches débloquées |
| `POST /api/philibert/action` | `{action, …}` : nourrir, chauffer, lampe, lumiere, bain, nettoyer, soigner, caresser, feliciter, gronder, ramasser, acheter, porter, retirer, evenement, carte_lue, vu, vacances, reglages, recommencer |
| `POST /api/philibert/jeu/debut` | `{jeu}` → jeton, graine, durée (ou première suite) |
| `POST /api/philibert/jeu/coup` | `{jeton, choix}` (gauche/droite) ou `{jeton, reponse}` (hochements) |
| `POST /api/philibert/jeu/fin` | `{jeton, score, insectes}` → récompense calculée par le serveur |

Toutes les valeurs (jauges, coquillages, durées) sont calculées par le serveur : le navigateur n'envoie que des
intentions. Journal d'activité (catégorie « Philibert ») : éclosion, évolutions, départ et retour du
vétérinaire, vacances, nouvel œuf — pas les repas (pas de spam).

## 16. Animations et design (version 2)

Inspirations (principes seulement, rien n'est repris) : cycle de marche des quadrupèdes en 4 temps (pose, appui,
lever, passage) avec des pattes décalées ; posture étalée des lézards (pattes de côté, en deux segments) ; interfaces
« cosy » (icônes plutôt que texte, coins arrondis, couleurs douces, cohérence) ; animations web en transform/opacity,
courbes douces pour les déplacements et à rebond pour ce qui apparaît.

- **Dessin** : ombrage en dégradé, reflets, rangées d'écailles, épines du fanon, yeux plus expressifs (deux
  reflets), pattes en deux segments à cinq doigts, queue en deux parties.
- **Marche** : paires diagonales, genou plié pendant le passage, corps qui ondule, queue en S ; vitesse accordée au
  rythme des pattes (il ne « glisse » plus). Il regarde toujours là où il va : s'il change de sens, il fait d'abord
  demi-tour (0,3 s), puis il part (en haut de la page comme sur l'île). En haut de la page : quelques images par pas seulement (léger).
- **Île** : palmes qui ondulent au vent le jour, écume qui respire autour de l'île, reflets sur la mer, soleil et
  ses rayons qui tournent lentement, étoiles qui scintillent, lucioles la nuit, papillons au printemps et en été,
  crabes qui trottinent ; Philibert respire au repos et se déplace par `transform` (unités de conteneur `cqw`).
- **Effets** : cœurs (caresse), miettes et aliment qui part vers sa bouche (repas), gouttes (bain), étoiles
  (félicitations, guérison, succès), coquillages (gains).
- **Interface** : en-tête avec médaillon, puces météo et saison ; jauges en cartes avec icône colorée (qui pulse
  doucement quand elle est basse) ; bulle de paroles de Philibert ; tuiles d'actions à icônes dessinées
  (`philibert-icones.js`, une seule famille d'icônes au lieu d'émojis) ; **palette de nuit** (bleu nuit) quand il
  fait nuit sur l'île.

### Version 3 : un dessin réaliste (16/11/2026)

Chaque élément a été redessiné d'après des descriptions et des photos réelles (principes seulement, aucun dessin
repris) : fiches d'espèces de l'iguane vert (zoo d'Honolulu, IUCN Iguana Specialist Group, Animal Diversity Web,
université de Floride), du cocotier (Kew, CTAHR Hawaï), du crabe fantôme de l'Atlantique ; descriptions de lagons
et de plages des Caraïbes ; conseils de peintres pour le ciel et les cumulus.

- **Philibert** : silhouette naturaliste de profil — tête haute aux joues fortes, **grande écaille ronde et pâle
  sous l'oreille** (subtympanique), tympan, arcade sourcilière, iris doré à pupille ronde, narine, rangées d'écailles
  des lèvres, œil pariétal ; **fanon** bordé de petites épines ; **crête** d'épines fines penchées vers l'arrière,
  plus hautes sur la nuque, prolongée sur la base de la queue ; **queue** très longue, effilée et **annelée** ;
  pattes musclées (genou vers l'avant, coude vers l'arrière) et longs doigts griffus. Volume par dégradés (dos
  sombre, flancs verts, ventre pâle) et fine texture d'écailles granuleuses (omise sur le petit Philibert du haut).
  Couleurs vraies : le **froid l'assombrit** (un lézard fonce pour capter la chaleur), la maladie le pâlit, le
  vieux sage devient gris-olive, le Royal prend l'**orange de parade** ; les joues roses « dessin animé » ont
  disparu. L'œuf est un œuf de reptile, souple et cabossé, à moitié enfoui dans son nid de sable.
- **Ciel** : dégradé du zénith vers un **horizon clair et voilé** ; soleil sans rayons dessinés, avec son halo ;
  **lune à sa vraie phase** (calculée sur le mois lunaire) avec ses mers sombres ; Voie lactée discrète ;
  **cumulus** au sommet éclairé et à la base plate et grise, plus petits et plus plats vers l'horizon.
- **Mer** : bleu profond voilé à l'horizon, texture de vagues **en perspective** (plus serrées au loin), voile de
  crêtes qui miroite, **colonne de reflets** sous le soleil ou la lune, **lagon** turquoise sur le sable blanc avec
  des reflets de lumière au fond (caustiques), patates de corail, **dentelle d'écume** le long du rivage.
- **Plage** : sable mouillé plus sombre au bord, sable grainé, laisse de mer, coquillages, galets, herbes des dunes à
  épis, **liseron de mer** (feuilles en cœur, fleurs roses) ; **cocotier** au stipe annelé et renflé, aux palmes
  pennées dont les folioles retombent, avec une palme sèche et ses noix ; **rocher** volcanique à facettes
  (éclairé du côté du soleil) avec lichens et air qui tremble au-dessus quand il chauffe ; flaque bordée de galets ;
  **ombres portées** à l'opposé du soleil, plus longues le matin et le soir ; crottes d'iguane avec leur partie
  blanche (comme chez tous les reptiles).
- **Faune** : crabes fantômes (couleur sable, yeux noirs sur pédoncules, pinces blanches inégales, actifs aussi la
  nuit), goélands et frégate qui plane, papillons julia et soufré.
- **Couleurs du moment** : palmes plus chaudes au coucher, ternes sous la pluie (brume au loin), Philibert dans la
  pénombre la nuit (moins quand la lanterne est allumée).
- **Objets et aliments** dessinés comme les vrais (mangue dégradée vert-jaune-rouge, papaye ouverte et ses graines,
  feuille de mûrier dentée, trèfle à chevrons, chou vert nervuré, flacon de remède ambré…), carte postale avec une
  tortue verte à écailles, pancarte en planche de bois.
- **Taille** : fenêtre plus grande (jusqu'à 1600 px de large) et **scène sur toute la largeur** (plus de bandes
  unies sur les côtés) ; si l'écran est bas, seul le haut du ciel est rogné (20 % en général, 25 % au plus) et le
  soleil et la lune passent toujours plus bas que cette marge ; textes, jauges (3 × 2) et tuiles un peu plus grands
  dans une grande fenêtre ; le Philibert qui se promène en haut est 20 % plus grand (115 × 58 px, 86 × 43 sur
  téléphone).
- **Mini-jeux** : mêmes dessins que l'île (palmes au-dessus de la pluie de feuilles, vraies feuilles nervurées,
  hibiscus, scarabée ; cocotiers en parallaxe, crabes, noix qui roulent, rocher, nuages et leurs ombres dans la
  course) ; le fond de plage est peint une seule fois sur un canevas hors écran.

## 17. Performance et accessibilité

- Philibert du haut : un seul élément SVG, déplacé par `transform` (transition CSS), pattes et queue animées en
  CSS ; minuterie d'humeur toutes les quelques secondes, rien quand l'onglet est caché, rien en mode jeu
  (`body.gamemode`) ; immobile avec `prefers-reduced-motion`. Lecture de l'état toutes les 60 s (onglet visible).
- Il marche dans un couloir à lui sous la barre du haut : il ne recouvre jamais un bouton, et seul son corps est
  cliquable (bouton nommé, focus visible, Entrée l'ouvre).
- L'île : animations CSS seulement (vagues, nuages, pluie, crabes, mouettes), coupées en mode jeu et avec
  `prefers-reduced-motion` ; le mini-jeu « Pluie de feuilles » dessine avec `nxImage()` (60 i/s au plus) et
  s'arrête quand l'onglet est caché. Fenêtre `<dialog>` : Échap ferme, boutons nommés, focus visible.
- Version 3 : le décor reste un dessin fixe recalculé seulement quand le ciel change (phase, météo, saison, demi-heure),
  les filtres (flou des ombres et des nuages, caustiques) sont donc calculés une fois ; ce qui bouge reste en
  `transform`/`opacity`. Les dégradés de chaque dessin de Philibert ont un préfixe par endroit de la page (`uid`),
  pour qu'un dessin caché ne prive jamais un autre de ses dégradés.

## 18. Où j'en suis / reste à faire

État au 16/11/2026 (une seule longue session a couvert les deux sessions prévues).

**Fait et vérifié**
- Moteur serveur complet (`philibert.py`) et routes `/api/philibert…` ; 133 tests sans navigateur
  (`outils/tests/test_philibert.py`, inscrit dans `run_all.py`) : temps simulé, nuit ralentie, planchers d'absence,
  chaleur jour/nuit/pluie/lampe, refus des aliments non végétaux, maladie → remède / repos au chaud, vétérinaire
  (gel, retour, carte postale, coût jamais bloquant), aucune mort après 1, 3 et 8 semaines d'absence, pension et
  vacances, vitesse lente, évolution et les 5 variantes, boutique et garde-robe, mini-jeux et anti-triche,
  discipline, réglages, nouvel œuf, routes HTTP.
- Philibert du haut (`philibert.js`) : couloir sous la barre du haut, marche (transition de `transform`),
  regards, clignements, hochements, fanon, bain de soleil à plat ventre, sommeil (Zzz), bulles d'humeur, panneau
  « chez le vétérinaire / en pension », notification Windows facultative ; seul son corps est cliquable.
- Dessin original (`philibert-dessin.js`) : 5 stades, 5 variantes, humeurs (calme, joyeux, dort, malade, froid,
  grognon), mue, ventre rond, 5 accessoires, œuf qui se fend.
- L'île (`philibert-ile.js`) : ciel par phase et météo, soleil/lune qui suivent l'heure, étoiles, nuages,
  mouettes, vagues, crabes, pluie, arc-en-ciel, île voisine avec la cabane de la voisine, barque de la tortue
  vétérinaire, palmier, rocher chaud, flaque, lanterne (lumière), lampe chauffante, déco, crottes cliquables ;
  jauges, « ce qui ne va pas », évènements, tous les soins, panneaux nourrir / bain / jouer / boutique /
  garde-robe / carnet / réglages, carte postale, bandeaux de succès et de fiches.
- Mini-jeux (`philibert-jeux.js`) : Pluie de feuilles (canevas + `nxImage`), Gauche ou droite ?, Le hochement.
- Vérifié dans le navigateur intégré (copie isolée, port 8015) : jour, nuit, coucher + pluie, aube + arc-en-ciel,
  boutique, nourrir, 3 mini-jeux joués jusqu'au bout, téléphone (375 px), Échap (panneau puis île), mode jeu
  (animations coupées), profils Pure, Sakura, Dés du destin, Phosphore, Néon minuit (couloir bien placé).

**Pas pu être vérifié**
- Mesure réelle du coût CPU de l'iguane du haut (le panneau du navigateur était masqué pendant la session : les
  images y sont ralenties). Par construction : aucune boucle d'animation en JavaScript, déplacement par
  `transform` (composité), pattes animées par `steps()` seulement pendant la marche, rien quand l'onglet est caché.
- Les notifications Windows et Discord (code en place, non déclenchées pour de vrai).
- Les profils Ardoise et Pluie d'étoiles en capture (même mécanisme d'en-tête que les autres).

**Version 2 (16/11/2026)** — faites et vérifiées dans la copie isolée : tuile du sommaire (accès direct aux
panneaux), course au rocher chaud jouée jusqu'au bout (arrivée sur le vrai rocher, gain calculé par le serveur),
saisons (jour, nuit, pluie), album après un nouvel œuf, nouvelles animations et nouveau design (jour, nuit,
téléphone). 151 tests serveur.

**Version 3 (16/11/2026)** — dessin réaliste de Philibert, de l'île, des objets et des mini-jeux, vérifié dans la
copie isolée : jour, coucher, nuit (lune à sa phase réelle), pluie, saisons, toutes les décorations, boutique et
nourriture, pluie de feuilles et course jouées jusqu'au bout, pancarte du vétérinaire, téléphone (375 px).
Pas mesuré : le coût réel des nouveaux filtres sur une petite carte graphique (calculés une fois par changement de ciel).

**Idées pour la suite**
- Plus d'évènements de saison (ponte de tortues marines au printemps, grande marée en saison des pluies).
- Une fiche « Le savais-tu ? » illustrée.
- Sons plus riches (toujours synthétisés, pas de fichiers).
