# Philibert — toutes les règles chiffrées (document pour l'administrateur)

Ce document décrit **exactement** ce que calcule le moteur (`philibert.py`) : de combien chaque jauge monte ou
descend, à quel moment, et pourquoi. Tout est calculé sur le serveur ; la page ne fait qu'afficher. Les valeurs
viennent du code de la version 1.1.0 ; les exemples en fin de document ont été obtenus en faisant tourner le vrai
moteur sur une horloge simulée.

> Conception générale, histoire et dessins : voir `docs/PHILIBERT.md`. Ici, uniquement les chiffres.

## 1. Le temps

| Règle | Valeur |
|---|---|
| Pas de calcul | toutes les **10 minutes** de temps réel (le moteur rattrape les pas manqués, même NEXUS fermé) |
| Vitesse « lente » (réglage) | tout ce qui dépend du temps est **× 0,5** (jauges, âge, chaleur, UV, corpulence) |
| Phases du ciel (heure du PC) | aube 6 h–8 h · jour 8 h–18 h · coucher 18 h–21 h · nuit 21 h–6 h |
| Heures de sommeil | de **21 h à 7 h** (il dort dans son palmier) |
| Absence | plus de **8 h** sans aucune action → les baisses sont **divisées par 2** et des **planchers** s'appliquent (§ 8) |
| Pension automatique | plus de **3 jours** sans action → la voisine le garde (tout est en pause, § 8) |
| Mode vacances | tout est en pause (jauges, âge, maladie) jusqu'au retour |

Dans tout le document, « /h » veut dire « par heure de temps réel », à vitesse normale.

## 2. Les six jauges (0 à 100)

Valeurs à la naissance : faim 80, bonheur 80, énergie 90, propreté 100, santé 100, chaleur 70.
La **santé ne descend jamais sous 5** : Philibert ne meurt jamais.

### 2.1 Évolution toute seule, à chaque heure

| Jauge | Éveillé (jour) | Endormi la nuit | Modificateurs |
|---|---|---|---|
| **Faim** | **−5 /h** | **−1,67 /h** (un tiers) | × 0,5 s'il a froid (chaleur < 35) : un lézard froid digère moins ; × 0,5 en absence |
| **Bonheur** | **−3 /h** | **−1 /h** (un tiers) | × 2/3 s'il a bien chaud (chaleur ≥ 70) ; × 1,5 s'il est malade ; **−0,5 /h** de plus pendant une mue ; **−0,5 /h** de plus s'il dort la nuit **lumière allumée** ; × 0,5 en absence |
| **Énergie** | **−4 /h** | **+14 /h** lumière éteinte · **+7 /h** lumière allumée | éveillé : × 1,3 s'il a froid, × 1,5 s'il est malade, × 0,5 en absence ; **sieste** de jour : **+10 /h** |
| **Propreté** | **−1,5 /h**, **−2 /h de plus par crotte** au sol | idem | × 0,5 en absence |
| **Santé** | voir § 2.2 | idem | — |
| **Chaleur** | se rapproche de la **température de l'endroit** (§ 3) | idem | — |

**Sieste de jour** : il s'endort tout seul si son énergie tombe sous 15, et se réveille à 50. S'il est sur la plage
en plein soleil (jour, soleil ou arc-en-ciel, chaleur < 80), il va faire sa sieste **sur le rocher chaud** et s'y
réchauffe en dormant (cible 95) ; il y reste tant qu'il dort (la limite de 2 h sur le rocher ne compte qu'éveillé),
puis redescend. *Chauffer* pendant une sieste le pose sur le rocher **sans le réveiller**.

### 2.2 Santé (par heure)

La santé baisse pour chaque problème en cours (les pertes s'additionnent) :

| Problème | Perte /h | Cause notée (carte postale) |
|---|---|---|
| Faim < 20 | −2,5 | faim |
| Propreté < 25 | −1,5 | propreté |
| Chaleur < 35 | −2 | froid |
| Corpulence > 78 | −0,8 | fruits |
| UV < 25 (manque de soleil) | −0,6 | soleil |
| Énergie < 15 | −1 | fatigue |

Ces pertes sont × 0,5 en absence. Ensuite :
- **en bonne santé**, s'il n'a aucun problème et que faim ≥ 35, propreté ≥ 35, chaleur ≥ 40 : **+1,5 /h** ;
- **malade** : **+1,2 /h** s'il est au chaud (chaleur ≥ 60) et qu'il dort ou a de l'énergie (≥ 40), sinon **−0,5 /h**.

### 2.3 Maladie, guérison, vétérinaire

| Règle | Valeur |
|---|---|
| Tombe malade | santé < 35, **ou** 5 friandises (fruits) en 24 h (indigestion) ; la santé est alors ramenée à 34 au plus |
| Remède (8 coquillages) | **+25 santé** s'il a chaud (chaleur ≥ 50), guéri si la santé atteint 45 ; sinon seulement **+10** |
| Guérit tout seul | santé ≥ 60 (indigestion : il faut aussi moins de 3 fruits en 24 h et une corpulence ≤ 75) |
| Départ chez la tortue vétérinaire | malade depuis **18 h**, ou santé au plus bas (≤ 6) pendant **3 h** |
| Durée du séjour | **12 h + 4 h** par cause importante (≥ 3 h cumulées), **24 h au plus** ; jauges figées |
| Retour | faim ≥ 70, bonheur ≥ 65, énergie ≥ 80, propreté ≥ 90, santé ≥ 85, chaleur ≥ 75, UV ≥ 70 ; corpulence ramenée vers 50 ; carte postale (ce qui lui a manqué + un conseil) |
| Prix de la consultation | **15 coquillages au plus**, jamais plus que ce que l'on a (jamais bloquant) |

## 3. La chaleur (sang froid)

Philibert n'a pas de chaleur propre : sa jauge **se rapproche de la température de l'endroit où il est**. Il se
réchauffe vite et se refroidit lentement :
- **en se réchauffant**, il comble **59 % de l'écart par heure** (la moitié en ≈ 46 min) ;
- **en se refroidissant**, il comble **30 % de l'écart par heure** (la moitié en ≈ 2 h).

### 3.1 Température de l'endroit (« cible »)

| Où | Soleil / arc-en-ciel | Nuages | Pluie |
|---|---|---|---|
| **Sur le rocher**, le jour (8 h–18 h) | **95** | 70 | 45 |
| Sur le rocher, à l'aube ou au coucher | 65 | 70 | 45 |
| **Sur la plage**, le jour | 62 | 52 | 38 |
| Sur la plage, à l'aube ou au coucher | 56 | 46 | 32 |
| Dans l'eau (bain) | 40 | 40 | 40 |
| **La nuit** (21 h–6 h) | plage 25 · palmier 28 · rocher 30 | idem | idem |

Puis on ajoute la **saison du calendrier** : printemps 0 · été **+5** · saison des pluies **−2** · saison fraîche
**−6** ; et, s'il y en a une, la **saison de l'île** : grande floraison +2 · tempêtes −4 · brumes −3 · ponte des
tortues +3 (les deux s'additionnent : une saison des tempêtes en saison fraîche, c'est −10).

### 3.2 Soleil ou lampe : qui chauffe ?

- **Le soleil** chauffe par le **rocher** : l'action *Chauffer* (le jour) l'installe sur le rocher. Il y reste
  jusqu'à atteindre une chaleur de **92**, ou **2 h** au plus, puis redescend sur la plage. Le rocher chauffe très
  bien au soleil (cible 95), moins sous les nuages (70) et presque pas sous la pluie (45). La nuit, *Chauffer*
  allume la lampe chauffante si on en a une (sinon : « le rocher refroidit »).
- **La lampe chauffante** (40 coquillages, achetée une fois) **remplace la cible quand elle est plus chaude** :
  cible = au moins **76 le jour, 72 la nuit**, où qu'il soit. Elle chauffe sans éclairer (il dort aussi bien).
  C'est la solution pour la nuit, les jours de pluie et la saison fraîche.
- **Le soleil donne aussi des UV** (la lampe, non) : sur le rocher, **+25 UV /h** au soleil ou sous l'arc-en-ciel,
  **+10 /h** sous les nuages, **0** sous la pluie, moitié moins à l'aube et au coucher. Les UV baissent toujours de
  **−1,2 /h**. Sous 25 UV : « il manque de soleil » et la santé baisse (−0,6 /h).
- **Bain de mer** : chaleur **−15** tout de suite (l'eau rafraîchit). **Course au rocher chaud** réussie : **+10**.

### 3.3 Effets de la chaleur

| Chaleur | Effet |
|---|---|
| < 35 | « il a froid » : faim × 0,5, énergie × 1,3, santé −2 /h, repas moins nourrissants (× 0,6), il frissonne et fonce |
| ≥ 50 | le remède agit pleinement |
| ≥ 60 | un Philibert malade guérit (+1,2 santé /h) |
| ≥ 70 | « bien au chaud » : bonheur baisse moins vite (× 2/3), **+25 % de coquillages** aux mini-jeux |

## 4. La météo et les saisons

La météo est tirée **par tranches de 2 heures** (la même sur le PC et le téléphone). Jamais deux pluies de suite ;
la tranche qui suit une pluie, s'il fait beau, c'est l'**arc-en-ciel**.

Deux systèmes de saisons **cohabitent** :

**1. Les saisons du calendrier** (mois réels, les mêmes pour toutes les îles) — la base de la météo :

| Saison (mois réels) | Pluie | Nuages | Soleil | Chaleur | Produit de saison (−1 coquillage) | Décor |
|---|---|---|---|---|---|---|
| Printemps (mars–mai) | 15 % | 30 % | 55 % | 0 | fleur de pissenlit | buisson d'hibiscus, fleurs, papillons |
| Été (juin–août) | 8 % | 22 % | 70 % | **+5** | mangue | étoiles de mer, mer plus vive, papillons |
| Saison des pluies (sept.–nov.) | 26 % | 32 % | 42 % | −2 | figue | noix de coco tombées, flaque plus grande, tonnerre lointain |
| Saison fraîche (déc.–févr.) | 14 % | 41 % | 45 % | **−6** | chou vert | bois flotté, ciel plus pâle, pas de lucioles |

**2. Les saisons de l'île**, qui n'ont rien à voir avec le calendrier. Chaque île a son propre **roulement** (tiré
de sa graine, depuis le 1ᵉʳ janvier 2026) : une période dure **entre 2 et 7 jours** (au hasard), puis une autre lui
succède, jamais la même deux fois de suite ; une période peut aussi être du **temps ordinaire** (aucune saison de
l'île). Elles **s'ajoutent** à la saison du calendrier (points de pourcentage en plus ou en moins) ; l'en-tête de
l'île montre les deux puces, et combien de temps il reste à la saison de l'île.

| Saison de l'île | Pluie | Nuages | Soleil | Chaleur | 2ᵉ produit de saison (−1) | Décor |
|---|---|---|---|---|---|---|
| Grande floraison | −4 | −8 | +12 | +2 | fleur d'hibiscus | tapis de fleurs sur toute la plage, papillons |
| Saison des tempêtes | **+14** | +18 | −32 | −4 | feuilles de mûrier | ciel et mer sombres, palmes secouées par le vent, algues, tonnerre |
| Saison des brumes | 0 | **+22** | −22 | −3 | haricots verts | brume douce sur l'île |
| Ponte des tortues | −4 | −6 | +10 | +3 | courge | traces de tortue et nid dans le sable, une tortue la nuit |

Exemple : saison des tempêtes en été → pluie 22 %, nuages 40 %, soleil 38 %. (Les pourcentages sont ceux du
tirage ; « jamais deux pluies de suite » en retire un peu au profit des nuages.) Succès « Les quatre saisons » (les
4 du calendrier) et « Saisons de l'île » (les 4 de l'île).

## 5. Les soins (effet immédiat)

| Action | Effet |
|---|---|
| **Nourrir** | voir le tableau § 5.1 ; refusé s'il a déjà faim ≥ 95 ; une crotte arrive **3 h après** chaque repas (3 en attente au plus, 4 au sol au plus) |
| **Chauffer** | le jour : sur le rocher (§ 3.2) ; la nuit : allume la lampe |
| **Lampe** | allumer / éteindre (§ 3.2) |
| **Lumière** (la nuit) | éteinte : il dort mieux (énergie +14 /h au lieu de +7, bonheur −1 /h au lieu de −1,5) |
| **Bain tiède (flaque)** | propreté **+35**, santé **+2** (une fois par jour) ; finit une mue ; 20 min entre deux bains |
| **Bain de mer** | propreté **+25**, bonheur **+10**, énergie **−10**, chaleur **−15**, corpulence **−3** ; finit une mue |
| **Nettoyer** | propreté **+30** s'il y avait des crottes, sinon **+8** |
| **Soigner** | remède : § 2.3 |
| **Caresser** | bonheur **+4** (une fois toutes les 2 min) |
| **Féliciter** | juste après une bonne action (repas de verdure, bain, rocher… dans les 10 min) : bonheur **+6**, discipline **+4** ; sinon bonheur **+3** (une fois toutes les 5 min) |
| **Gronder** | un caprice : discipline **+10**, bonheur **−2** ; un vrai besoin : bonheur **−6** ; rien : bonheur **−4** |
| **Le réveiller la nuit** (n'importe quelle action) | bonheur **−8**, grognon **1 h**, reste éveillé **30 min** |
| **Ramasser** | 1 à 3 coquillages, toutes les **3 h** |

### 5.1 Aliments

Faim et corpulence sont × 0,6 s'il a froid. **Bonus variété** : 3 verdures ou légumes différents parmi les 6 derniers
repas → santé **+3**.

| Aliment | Catégorie | Prix | Faim | Bonheur | Santé | Corpulence |
|---|---|---|---|---|---|---|
| Trèfle de l'île | verdure | gratuit | +15 | +1 | 0 | +1 |
| Feuilles de pissenlit | verdure | 2 | +28 | +3 | +1 | +1,5 |
| Feuilles de mûrier | verdure | 3 | +30 | +3 | +1 | +1,5 |
| Chou vert | verdure | 2 | +26 | +2 | +1 | +1,5 |
| Courge râpée | légume | 3 | +30 | +4 | +1 | +2 |
| Haricots verts | légume | 3 | +32 | +3 | +1 | +2 |
| Fleur d'hibiscus | fleur | 4 | +12 | +12 | +1 | +1 |
| Fleur de pissenlit | fleur | 3 | +8 | +15 | 0 | +1 |
| Mangue, papaye, figue | friandise | 5 | +10 | +20 | 0 | +6 |
| Banane | friandise | 8 | +10 | +22 | 0 | +8 |

Insectes, viande, poisson, croquettes : **toujours refusés** (il est herbivore) ; ils n'apparaissent que comme
pièges (évènements) — les refuser rapporte +2 coquillages, les jeter +3.

## 6. Corpulence et poids

| Règle | Valeur |
|---|---|
| Baisse | **−0,5 /h** éveillé et au chaud (chaleur ≥ 50), **−0,25 /h** éveillé et frais, **−0,2 /h** endormi, **−0,5 /h** de plus s'il a faim (< 15) |
| Hausse | les repas (§ 5.1) |
| Autres | mini-jeu **−2**, bain de mer **−3** |
| Seuils | > 75 : « ventre tout rond » ; > 78 : la santé baisse (−0,8 /h) |
| Poids affiché | suit l'âge (bébé 15→60 g, juvénile 60→500 g, adulte 0,5→3,5 kg, vieux sage 3,5→4,2 kg) × (0,7 + corpulence × 0,006) |

## 7. Bonheur, attention et discipline

| Règle | Valeur |
|---|---|
| « Il s'ennuie : joue avec lui » | seulement si le **bonheur est à 30 ou moins** |
| Caprice (« il réclame de l'attention ») | seulement si le **bonheur est à 30 ou moins** ; tiré à chaque pas de 10 min avec une probabilité de **3,5 % × (1 − discipline / 130)** ; un caprice en cours disparaît dès que le bonheur repasse au-dessus de 30 |
| Appel pour un vrai besoin (faim, froid, malade, sale, mue…) | aussitôt qu'un besoin apparaît, éveillé |
| Appel ignoré 2 h | vrai besoin : bonheur **−5** ; caprice : discipline **+3** ; puis 1 h sans appel |
| Fin d'un appel | dès que le besoin est réglé (après un repas, un bain, du chaud…) ; 30 min de pause |

## 8. Absences

| Durée sans action | Ce qui se passe |
|---|---|
| < 8 h | normal |
| > 8 h | baisses **× 0,5** (faim, bonheur, énergie, propreté, pertes de santé) et **planchers** : faim, propreté, chaleur et énergie ne descendent pas sous **20**, bonheur sous **25** (une jauge déjà plus basse ne remonte pas, mais ne descend plus) |
| > 3 jours | **pension chez la voisine** : faim ≥ 65, bonheur ≥ 60, énergie ≥ 75, propreté ≥ 80, santé ≥ 70, chaleur ≥ 70, UV ≥ 60, plus de crottes ; puis tout est en pause jusqu'au retour (s'il était malade, il passe d'abord chez la vétérinaire) |

## 9 bis. Mutations de couleur

À **chaque fin de mue** (à partir du stade juvénile), la nouvelle peau peut changer de couleur selon sa vie. Le
moteur calcule un **score** par mutation ; la plus forte, si elle atteint **1**, l'emporte, avec une **intensité**
1 (score ≥ 1), 2 (≥ 1,6) ou 3 (≥ 2,4). Une autre mutation ne remplace la sienne que si son score la dépasse de 25 %.

| Mutation | Score (≥ 1 pour l'obtenir) |
|---|---|
| Émeraude | part de verdure dans les repas ÷ 75 % × santé moyenne ÷ 85 (au moins 12 repas de verdure) |
| Orangé | part d'aliments orangés (courge, mangue, papaye, fleur de pissenlit, banane) ÷ 30 % (au moins 6) |
| Doré | le plus petit de : séances au soleil ÷ 15 et heures bien au chaud (≥ 75) ÷ 40 (au moins 8 séances) |
| Turquoise | bains de mer ÷ 10 |
| Mélanique | heures passées à avoir froid (< 35) ÷ 30 |
| Cendré | le plus grand de : heures malade ÷ 30 et séjours chez la vétérinaire ÷ 2 |
| Arlequin | le plus petit de : parties jouées ÷ 25 et bonheur moyen ÷ 75 (au moins 10 parties) |
| Lunaire | fois où on l'a réveillé la nuit ÷ 6 |
| Leucique | 3 % de chance à une mue, si santé moyenne ≥ 85 et bonheur moyen ≥ 85 (très rare) |

La couleur se voit partout (île, en haut de la page, médaillon, garde-robe, album) ; le froid et la maladie
passent par-dessus tant qu'ils durent. Le carnet a un onglet **Couleurs** (découvertes et indices). Succès
« Couleurs uniques » ; fiche « Le savais-tu ? » sur les formes de couleur des iguanes.

## 9. Croissance et mue

| Stade | Âge |
|---|---|
| Œuf | éclot après **10 min** |
| Bébé | 0 à 2 jours |
| Juvénile | 2 à 7 jours |
| Adulte | 7 à 30 jours (la variante est choisie à ce moment) |
| Vieux sage | après 30 jours |

**Variante adulte** (selon les moyennes de soins) : le *Convalescent* après 2 séjours chez la vétérinaire ; le
*Royal* si santé moyenne ≥ 80, bonheur moyen ≥ 70, ≤ 20 % de friandises et aucun séjour ; le *Gourmand* si ≥ 30 %
de friandises ou corpulence > 75 ; le *Nageur* après 8 bains de mer ; sinon l'*Insulaire*.

**Mue** : la première vers 2 jours, puis tous les 2 jours (bébé, juvénile), 5 jours (adulte), 7 jours (vieux sage).
Elle dure **30 h** ou se termine avec un bain ; pendant la mue, bonheur −0,5 /h de plus.

## 10. Mini-jeux et coquillages

| Règle | Valeur |
|---|---|
| Pour jouer | éveillé, pas malade, énergie ≥ 15 |
| **Coût** | **−8 énergie au lancement**. **Abandonner** une partie : aucun gain, et ces 8 points ne reviennent pas |
| Plafond | **120 coquillages par jour** aux jeux ; par partie : 20 à 30 coquillages et +25 de bonheur au plus |
| Bien au chaud (chaleur ≥ 70) | gains × 1,25 |
| Pluie de feuilles (3 min au plus) | **palier** + 1 toutes les 20 s (9 au plus) : vitesse de chute × (1 + 0,16 × (palier − 1)), objets par seconde × (1 + 0,14 × (palier − 1)), insectes 22 % + 3 % par palier (46 % au palier 9), fleurs 18 % ; **5 vies** (insecte attrapé, ou 6 feuilles ratées = −1 vie) ; gain min(30, score ÷ 8 + 2 × (palier − 1)) ; bonheur min(25, 5 + score ÷ 6 + palier) |
| Course au rocher chaud (4 min au plus) | **10 étapes** de 4 000 px jusqu'au rocher ; vitesse × (1 + 0,06 × (étape − 1)) ; écart entre obstacles ÷ (1 + 0,1 × (étape − 1)), jamais moins de 250 px ; **3 vies** (un choc = −1) ; gain min(30, rayons ÷ 6 + 2 × (étape − 1) + 6 si arrivé) ; bonheur min(25, 6 + rayons ÷ 5 + étape) ; arrivé : chaleur +10 et il s'étale sur le rocher |
| Gauche ou droite ? (20 manches) | côté tiré **avant** le choix ; un **coup d'œil** (indice) le montre, vrai 90 % du temps au palier 1 puis 86, 82, 78, 75 %, et de plus en plus bref (900, 650, 460, 330, 240 ms) ; un palier toutes les 4 manches ; **fin à la 3ᵉ erreur** ; gain min(20, bonnes réponses + 2 × (palier − 1)) ; bonheur min(25, 4 + 2 × bonnes réponses) |
| En rythme | suites de 3 à **14** gestes (petit hochement, grand hochement, fanon) à reproduire **en entier**, **nouvelle suite à chaque manche** (palier = manche), jamais 3 fois le même geste d'affilée ; vitesse de **tous** les gestes : un temps = max(0,30 s ; 0,78 s − 0,045 s × manche) ; gain min(25, 2 × (longueur − 2) + palier − 1) ; bonheur min(25, 4 + 2 × longueur) |
| **Anti-triche** | jeton à usage unique ; Pluie de feuilles et Course : partie de moins de 10 s refusée ; score, palier, distance et rayons bornés par la **durée réelle** de la partie (nombre d'objets qui ont pu tomber, vitesse maximale, écart minimal des rayons) : un résultat impossible est **refusé** (partie close, rien gagné) ; Gauche ou droite et En rythme sont comptés par le serveur, coup par coup (réponse trop rapide refusée) |
| Autres gains | ramasser 1 à 3 (toutes les 3 h), noix de coco +4, piège jeté +3 ou refusé +2, succès (0 à 20) |
| Départ | 20 coquillages |

## 11. Exemples (vrai moteur, horloge simulée, printemps)

**Une heure de jour**, éveillé sur la plage au soleil (chaleur 70) : faim −5, bonheur −3, énergie −4,
propreté −1,5, santé 0, chaleur −2,4 (elle descend vers 62).

**Une heure de nuit**, endormi dans le palmier : faim −1,7, propreté −1,5 ; lumière éteinte : bonheur −1,
énergie +14 ; lumière allumée : bonheur −1,5, énergie +7. Chaleur 70 → 58 (cible 28 : la nuit refroidit).

**Se réchauffer depuis 40** (après 30 min · 1 h · 1 h 30 · 2 h) :

| Situation | Cible | Chaleur |
|---|---|---|
| Rocher, soleil, en journée | 95 | 60 · 73 · 81 · 86 |
| Rocher, nuages | 70 | 51 · 58 · 62 · 65 |
| Rocher, pluie | 45 | 42 · 43 · 44 · 44 |
| Plage, soleil | 62 | 48 · 53 · 56 · 58 |
| Plage, pluie | 38 | 40 · 39 · 39 · 39 |
| Plage, pluie, **lampe allumée** | 76 | 53 · 61 · 67 · 70 |
| La nuit dans le palmier, sans lampe | 28 | 38 · 36 · 35 · 34 |
| La nuit dans le palmier, **lampe allumée** | 72 | 52 · 59 · 64 · 67 |

**Se refroidir depuis 90**, la nuit sans lampe (après 1 · 2 · 3 · 4 h) : 72 · 59 · 50 · 43.

**Douze heures de jour sans aucun soin** (de 7 h à 19 h, en partant de faim 80, bonheur 80, énergie 80) :
présent devant l'écran → faim 20, bonheur 44, énergie 32, propreté 82 ; parti de chez soi (au-delà de 8 h, tout
ralentit) → faim 30, bonheur 50, énergie 40, propreté 85. La santé reste à 100 tant qu'aucun seuil n'est franchi.
