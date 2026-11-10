# Format des profils visuels NEXUS (format 1)

Ce document décrit **exactement** ce qu'un profil peut contenir. Il est écrit pour qu'on puisse dire
à Claude Code : *« crée-moi un profil style X en suivant profils/FORMAT.md »* et obtenir un dossier
directement utilisable.

> **Pour Claude Code — procédure à suivre**
> 1. Choisis un identifiant : minuscules, chiffres et tirets, 40 caractères max, pas `defaut`,
>    ne commençant pas par `_` (ex. `ocean-calme`). Crée `profils/<identifiant>/`.
> 2. Pars de `profils/_modele/` (copie `profil.json` et `style.css`), sans recopier `LISEZMOI.md`.
> 3. Écris `profil.json` (champs ci-dessous) et `style.css` en respectant **toutes** les règles de la
>    section « Interdit ». Préfixe chaque sélecteur par `:root[data-profile]`.
> 4. Les images et polices éventuelles vont dans `assets/`, créées localement (SVG écrit à la main, par
>    exemple). Ne télécharge rien et ne référence aucune adresse Internet.
> 5. Lance `python valider_profil.py profils/<identifiant>` et corrige jusqu'à obtenir `PROFIL VALIDE`.
> 6. Dis à l'utilisateur : menu 🎨 de NEXUS → ⟳ Actualiser → choisir le profil.

---

## 1. Principe

NEXUS a deux **modes** (bouton ◐ en haut) : `terminal` (rouge, style Ultron) et `sentinelle`
(orange et bleu). Un **profil** est une feuille de style chargée **par-dessus** le mode en cours :

- il ne change que l'apparence (couleurs, polices, fond, formes, effets, disposition) ;
- il ne peut ni exécuter de code, ni modifier les données, ni charger quoi que ce soit d'Internet ;
- le profil `Défaut` (intégré, non supprimable) correspond à l'absence de profil.

Quand un profil est actif, la page a l'attribut `data-profile="<identifiant>"` sur `<html>`, en plus de
`data-theme="terminal"` ou `data-theme="sentinelle"`.

## 2. Structure du dossier

```
profils/
  <identifiant>/          ← nom du dossier = identifiant du profil
    profil.json           ← obligatoire
    style.css             ← obligatoire
    assets/               ← facultatif : images et polices
      fond.svg
      police.woff2
    LISEZMOI.md           ← facultatif (*.md, *.txt tolérés à la racine, jamais servis)
```

Aucun autre fichier ni dossier n'est accepté. Les dossiers dont le nom commence par `_` ou `.`
(comme `_modele`) sont ignorés par NEXUS.

## 3. `profil.json`

```json
{
  "format": 1,
  "nom": "Océan calme",
  "auteur": "Claude Code",
  "version": "1.0",
  "modes": ["terminal", "sentinelle"],
  "description": "Bleus profonds, coins arrondis, aucune lueur.",
  "apercu": { "couleurs": ["#0b1b2b", "#3fb6ff", "#7af0d0"], "miniature": "assets/apercu.png" }
}
```

| Champ | Obligatoire | Règle |
|---|---|---|
| `format` | non | `1` (valeur actuelle) |
| `nom` | **oui** | texte, 1 à 40 caractères, sans `<` ni `>`. Sert aussi à fabriquer l'identifiant lors d'un import. |
| `auteur` | non | texte, 40 caractères max |
| `version` | **oui** | texte, 20 caractères max (ex. `"1.0"`) |
| `modes` | **oui** | liste non vide parmi `"terminal"` et `"sentinelle"`. Le menu n'affiche le profil que dans ces modes. |
| `description` | non | texte, 240 caractères max |
| `apercu.couleurs` | conseillé | 1 à 5 couleurs `#rgb` ou `#rrggbb`, affichées comme pastilles dans le menu |
| `apercu.miniature` | non | image du dossier `assets/` (`.png`, `.jpg`, `.webp`, `.gif`, `.svg`, `.avif`), affichée à la place des pastilles (proportions 14:9 environ) |
| `animations` | non | animations de la page de garde, voir § 4.6 : `{"intro_ms": 6000, "transition_ms": 2000, "remplace_transition": true}` |
| `panel_min_version` | non | version minimale de NEXUS demandée, en `"majeur.mineur.correctif"` (ex. `"1.0.0"`). Si NEXUS est plus ancien, le profil est refusé avec un message clair, au lieu de s'afficher de travers. |

Encodage UTF-8, 16 Ko maximum. Les champs inconnus sont ignorés, avec un avertissement.

## 4. `style.css`

### 4.1 Règle de spécificité

Les styles du mode sont écrits avec `:root[data-theme] …`. Pour passer devant, **commence chaque
sélecteur par `:root[data-profile]`**. À spécificité égale, le profil l'emporte car il est chargé en
dernier. Si une règle ne s'applique toujours pas, ajoute `!important`.

```css
:root[data-profile] { --cyan: #3fb6ff; }                        /* variable */
:root[data-profile] .card { border-radius: 12px; }              /* élément */
:root[data-profile][data-theme="sentinelle"] { --cyan: #ff8c1a; } /* un seul mode */
```

### 4.2 Variables disponibles (le plus simple et le plus robuste)

Toutes les couleurs du panel passent par ces variables. Les jauges et les courbes les relisent
quand on change de profil.

| Variable | Rôle |
|---|---|
| `--bg` | fond de la page |
| `--card` | fond des cartes |
| `--text`, `--text-2`, `--muted` | texte principal, secondaire, discret |
| `--cyan` | **couleur principale** (nom historique) : titres, jauge CPU, onglet actif, bordures |
| `--neon-2`, `--neon-3` | variantes claires de la couleur principale |
| `--magenta` | **couleur secondaire** : RAM, accents, carte Média |
| `--yellow` | horloge, réseau (envoi), bouton Profil |
| `--green` | courbe et jauge du GPU |
| `--ok`, `--warn`, `--hot` | états normal / attention / critique (températures, alertes) |
| `--track` | fond des barres et des jauges |
| `--edge`, `--edge-2` | bordures |
| `--deep-1`, `--deep-2`, `--deep-3` | fonds d'encadrés, du plus clair au plus sombre |
| `--neon-rgb`, `--mag-rgb`, `--yel-rgb`, `--ok-rgb` | mêmes couleurs que `--cyan`, `--magenta`, `--yellow`, `--ok`, au format `r, g, b` (pour `rgba(var(--neon-rgb), .3)`) : **à garder cohérentes** |
| `--deep-rgb`, `--glow2-rgb`, `--neon3-rgb` | fond des encadrés, halo du fond, variante claire (format `r, g, b`) |
| `--mono` | police à chasse fixe (texte courant, boutons) |
| `--display` | police des titres et des gros chiffres |
| `--chrome` | dégradé des gros titres (NEXUS, « Bon après-midi », tuiles du sommaire) |
| `--tab-grad` | fond de l'onglet actif |
| `--hex-img` | motif du fond, une valeur `url(…)` ou `none` |
| `--aberr` | ombre « aberration chromatique » des chiffres (une valeur de `text-shadow`) |
| `--note-jaune`, `--note-rose`, `--note-vert`, `--note-bleu`, `--note-violet`, `--note-peche`, `--note-texte` | couleurs pastel des notes façon post-it du mur des Souvenirs (par défaut, tirées de `--yellow`, `--magenta`, `--ok`, `--cyan`, `--warn`) et couleur de leur texte |

**Disposition des blocs :** la place et la taille des blocs que l'utilisateur a déplacés (toutes les
catégories, `.nx-panel`) et des éléments du mur des Souvenirs (`.sv-item`) sont posées par le panel en style
« !important » : un profil peut changer leur apparence (bordure, fond, ombre), **jamais leur place ni leur
taille**. Les dispositions et les notes ne font jamais partie d'un profil ni de son export `.zip`.

### 4.3 Sélecteurs stables

Ces classes et éléments ne changeront pas : base-toi dessus (toujours préfixés `:root[data-profile]`).

| Sélecteur | Élément |
|---|---|
| `body` | fond de la page (`background`) |
| `body::before` | sol en perspective (grille en bas de l'écran) |
| `body::after` | lignes de balayage et vignette, par-dessus tout |
| `header`, `header::after` | barre du haut, ligne lumineuse sous la barre |
| `h1`, `h1 .home-link span`, `h1 em`, `.hdr-logo` | titre NEXUS, sa barre oblique, son logo |
| `h1.glitch .t::before`, `h1.glitch .t::after` | copies décalées de l'effet glitch du titre |
| `.status`, `.dot`, `#clock` | voyants API / GPU / LHM, horloge |
| `.btn` | tous les boutons |
| `.tabs a`, `.tabs a[aria-selected="true"]`, `.tabs a::before`, `.tabs a::after` | onglets, onglet actif, décorations |
| `.card`, `.card h2`, `.card h2::before`, `.card::before`, `.card::after` | cartes, leurs titres, leur numérotation, leurs décorations |
| `.gauge .val` | chiffre au centre des jauges |
| `.bar`, `.bar i` | barres de progression (fond, remplissage) |
| `.temp`, `.rate`, `.facts` | encadrés de température, de débit, listes de valeurs |
| `.home-hello`, `.home-time`, `.home-tile`, `.home-ico`, `.home-title`, `.home-live`, `.home-parts a` | sommaire : salutation, heure, tuiles, icônes, titres, aperçus, raccourcis |
| `.section-title`, `.tbl`, `.in`, `.alert` | intertitres, tableaux, champs de saisie, bandeaux d'alerte |
| `.dk-btn`, `.game`, `.cover`, `.mx-row` | boutons du deck, jeux, pochette, mélangeur |
| `.sv-photo`, `.sv-drop`, `.sv-date`, `.sv-clock` | Souvenirs : photos du mur, zone d'ajout, jour en grand, heure |
| `.st-donut`, `.st-track i`, `.st-col i` | Statistiques : camembert, barres des jeux, colonnes d'activité |
| `.jn-mood`, `.jn-act`, `.jn-text`, `.jn-mday` | Journal : humeurs, activités, zone de texte, jours de la vue mois |
| `.ver-dlg` | fenêtre des notes de version |
| `body.gamemode` | présent pendant une partie : les animations y sont coupées automatiquement |

Les découpes en biseau utilisent `clip-path` : `clip-path: none` les retire. Pour la disposition
(ex. `.home-grid`, `gap`, `padding`), évite de masquer des informations (`display: none` sur des
données) : un profil change l'apparence, pas le contenu.

### 4.4 Fichiers locaux

```css
:root[data-profile] body { background: url("assets/fond.svg") center / cover no-repeat, var(--bg); }

@font-face { font-family: "MaPolice"; src: url("assets/police.woff2") format("woff2"); }
:root[data-profile] { --display: "MaPolice", var(--mono); }
```

- `url()` doit désigner un fichier existant de **`assets/`**, en chemin relatif (`assets/…`), avec
  uniquement lettres, chiffres, `_`, `-`, `.`, `/` et espaces dans le nom.
- `local("Nom de police")` est permis pour une police déjà installée sur le PC (ex. `local("Segoe UI")`).

### 4.6 Page de garde : états et animations (sans JavaScript)

Un profil ne contient jamais de JavaScript. Pour animer la page de garde, il cible en CSS l'attribut
**`data-etat`** que le panel pose sur `<body>` :

| `body[data-etat=…]` | Moment |
|---|---|
| `intro` | démarrage complet de la page de garde (une fois par session, au premier affichage) |
| `reconnexion` | retour rapide à la page de garde par le logo de l'en-tête |
| `pret` | la page de garde attend le clic sur le bouton NEXUS |
| `veille` | écran éteint après 45 s sans activité |
| `transition` | juste après le clic sur NEXUS, jusqu'à l'arrivée sur le sommaire |
| `arrivee` | fin de la transition d'un profil (`remplace_transition`) : vers 60 % de `transition_ms`, la page de garde s'efface en fondu pendant que le sommaire apparaît dessous ; l'état dure encore ~1,1 s après la fermeture, pour prolonger l'effet du profil sur le sommaire |
| `panel` | la page de garde est fermée (navigation normale) |

**Arrivée sur le sommaire, sans coupure :** le panel fait CHEVAUCHER la fin de l'animation et l'apparition
du sommaire. Au début de `arrivee`, `#splash` reçoit la classe `sp-fondu` (fondu d'opacité, courbe douce)
et les tuiles du sommaire apparaissent en cascade ; la page de garde n'est retirée qu'une fois invisible.
Le sommaire est préparé à l'avance (dès l'affichage de la page de garde et au survol du bouton NEXUS).
Pour prolonger l'effet par-dessus le sommaire, un profil utilise un calque qui n'est PAS dans `#splash`,
pendant `arrivee`, sans gêner les clics (`pointer-events: none`) :

```css
/* des feuilles passent encore au premier plan (profils/sakura) */
:root[data-profile]:has(> body[data-etat="arrivee"])::after { content: ""; position: fixed; inset: 0; z-index: 95;
  pointer-events: none; background: url("assets/feuilles.svg"); animation: mes-feuilles 1.9s ease-in-out forwards; }
/* un souffle chaud qui se dissipe (profils/des-du-destin) */
:root[data-profile] body[data-etat="arrivee"]::after { … mix-blend-mode: screen; animation: souffle 1.5s forwards; }
```

**Changement de profil (menu 🎨) :** le panel affiche un écran NEXUS neutre (« Chargement du profil … »,
version de `profil.json`, barre), précharge la feuille du profil ET tous les fichiers qu'elle cite (images,
polices), puis applique le profil et l'écran s'efface. Deux états, sur un attribut à part (ils peuvent
arriver pendant l'intro, sans toucher `data-etat`) :

| `body[data-profil-etat=…]` | Moment |
|---|---|
| `changement` | l'écran de transition couvre l'interface ; l'ancien profil est encore appliqué |
| `pret` | le nouveau profil est appliqué ; l'écran s'efface (~0,4 s), puis l'attribut disparaît |

```css
/* apparition personnalisée des cartes quand mon profil arrive */
:root[data-profile] body[data-profil-etat="pret"] .card { animation: mon-apparition .6s ease-out both; }
```

**Couleur d'accent du profil : `--accent-profil`.** Utilisée par l'écran de transition (logo, nom, barre)
dès que la feuille du profil est appliquée. Par défaut : `--cyan`. Un profil peut la fixer :
`:root[data-profile] { --accent-profil: #ff4a5c; }` (une couleur ; `--accent` reste réservée aux cartes).

```css
:root[data-profile] body[data-etat="intro"] #splash .sp-enter { animation: mon-entree 1.2s 4s both; }
:root[data-profile] body[data-etat="transition"] #splash .sp-screen { animation: mon-envol 2s forwards; }
```

Dans `profil.json`, le champ facultatif **`animations`** règle les durées. **Le panel garde toujours la
main** sur les minuteries et la navigation : une animation lente ou une image qui tarde ne bloque jamais rien.

| Clé | Effet |
|---|---|
| `intro_ms` (0 à 10000) | durée minimale de l'état `intro` avant `pret`. Un clic ou une touche passe l'intro (état `pret` aussitôt) |
| `remplace_transition` (`true`/`false`) | `true` : la « pluie de code » du panel est remplacée par l'animation du profil (état `transition`) |
| `transition_ms` (300 à 5000) | durée de l'état `transition` ; le sommaire s'affiche à la fin (tuiles en cascade vers 70 %) |
| `ouverture` (`"fondu"`, `"cercle"`, `"tele"`) | comment la page de garde laisse place au sommaire, à partir de 60 % de `transition_ms` : `fondu` (par défaut) = elle s'efface ; `cercle` = un trou aux bords doux part du logo et s'agrandit jusqu'aux coins, bordé d'un anneau lumineux (comme la fin de la pluie de code du thème par défaut) ; `tele` = vieille télé qui s'allume (noir, ligne lumineuse, l'image s'ouvre verticalement dans un éclair). L'utilisateur peut imposer l'un des trois (⚙ Réglages) ; en mode jeu, c'est toujours `fondu` |

**Ouverture en rond ou télé :** la couleur de l'anneau et de la ligne se règle avec la variable `--sp-anneau`
posée sur `#splash` (ex. `:root[data-profile] #splash { --sp-anneau: rgba(255, 192, 216, .95); }`). Pour un
anneau plus travaillé, redéfinis le fond de `#splash .sp-anneau` : `--sp-r` (rayon actuel), `--sp-ix` et
`--sp-iy` (centre) y sont disponibles (exemple : l'anneau de feu de `profils/des-du-destin`). Avec `cercle`,
garde le décor du profil visible pendant la transition (n'efface que le logo et les textes) : l'ouverture
traverse alors le décor, qui continue d'animer autour.

**Sans coupure avec le cercle :** l'ouverture en rond commence à 45 % de `transition_ms` (60 % pour `fondu`
et `tele`) et dure jusqu'à la fin, soit environ `transition_ms × 0,55 + 650 ms`. À ce moment, la page passe
de l'état `transition` à l'état `arrivee` : une animation liée seulement à `[data-etat="transition"]` s'arrête
NET. Écris donc les règles de la transition pour les deux états, avec des durées qui couvrent toute
l'ouverture (`transition_ms` + 650 ms) :
`:root[data-profile] body:is([data-etat="transition"], [data-etat="arrivee"]) #splash .sp-screen { animation: … }`.
Pendant l'ouverture, le panel **disperse** la scène : `.sp-screen`, `#splash::before` et `#splash::after`
grossissent depuis le logo (propriété `scale`, qui s'ajoute à tes animations de `transform`). La force se
règle avec `--sp-disperse` sur `#splash` (1,45 par défaut ; 1 = aucune dispersion).

Éléments de la page de garde utilisables (toujours avec `:root[data-profile]` et `#splash` devant,
car les règles de la page de garde utilisent des `#id`) : `#splash`, `#splash::before`, `#splash::after`,
`.sp-screen` (tout l'écran, et son `::after`), `.sp-grid`, `.sp-glow`, `.sp-sweep` (décors réutilisables),
`.sp-center` (bloc central, `::before`), `.sp-enter` (bouton NEXUS : logo + titre, `::after`), `.sp-logo` (logo,
avec `stop:first-child` / `stop:last-child`, `.sp-traces`, `.sp-nodes`), `.sp-title`, `.sp-tag`, `.sp-bar` et
`.sp-bar i`, `.sp-granted`, `.sp-prompt`, `.sp-log`, `.sp-skip` (bouton « passer »), `.sp-standby` (veille).

**Alertes (tout le panel, pas seulement la page de garde)** : deux attributs de plus sur `<body>`, mis à jour
à chaque relevé des alertes.

| Attribut | Valeurs | Moment |
|---|---|---|
| `body[data-alerte=…]` | `aucune`, `normale`, `critique` | état courant : aucune alerte, au moins une alerte, au moins une alerte critique |
| `body[data-focus=…]` | `travail`, `pause`, `longue` | une session de focus (Pomodoro) est en cours, et sa phase |
| `body[data-alerte-evenement=…]` | `nouvelle-critique`, `resolue` | posé **3 s** puis retiré : une alerte critique vient d'apparaître / toutes les alertes viennent de disparaître |

```css
:root[data-profile] body[data-alerte="critique"] header { box-shadow: 0 0 20px rgba(255, 40, 60, .4); }
:root[data-profile] body[data-alerte-evenement="resolue"]::after { display: block; animation: mon-clin 2.8s forwards; }
```

Une alerte que l'utilisateur a ignorée (bouton `.alert-x`) ne compte plus dans ces états jusqu'au prochain démarrage.
Chaque alerte reste aussi un `.alert` (ou `.alert.crit`) dans `#alerts`. Exemple complet :
`profils/des-du-destin` (un 20 doré quand tout est résolu, un 1 rouge à une nouvelle alerte critique).

**Intro désactivée par l'utilisateur** (⚙ Réglages → « Jouer l'intro animée des profils visuels », par
appareil) : la page de garde démarre directement en état `reconnexion` au lieu de `intro`, sans attendre
`intro_ms`. Un profil n'a rien à faire : il suffit qu'il n'anime son intro que sous `body[data-etat="intro"]`.

**Sans animation** (`prefers-reduced-motion: reduce`) : le panel n'attend pas `intro_ms` et remplace la
transition par un simple fondu. Le profil doit aussi tout afficher directement dans ce cas (bloc
`@media (prefers-reduced-motion: reduce)`).

**Performances :** n'animer que `transform` et `opacity`, et limiter les éléments qui bougent, surtout
sur téléphone (`@media (max-width: 700px)`). Quelques règles de plus :
- `filter`, `box-shadow`, `backdrop-filter` : fixes seulement (une ombre qui « pulse » se fait avec un
  pseudo-élément qui porte l'ombre et dont on anime l'`opacity`) ;
- `will-change` : seulement pendant l'animation (ex. sous `body[data-etat="intro"]`), jamais en permanence ;
- un SVG animé posé en fond plein écran est redessiné **à chaque changement** : pour un scintillement
  lent, préfère `animation-timing-function: steps(4, jump-none)` avec une même durée et des délais
  multiples de 0,5 s (l'image change alors 2 à 4 fois par seconde au lieu de 60, sans différence visible) ;
- motifs répétés dans un SVG : un `<symbol>` / `<g id>` réutilisé par `<use>`, sans métadonnées d'éditeur ;
- **grande image SVG lourde avec filtres** (`feTurbulence`, `feDiffuseLighting`…) qui est agrandie ou animée
  pendant une transition : le navigateur la recalcule à chaque changement d'échelle (jusqu'à ~1 s de gel à
  l'écran sur un grand écran). Rends-la plutôt en image **WebP transparente** (même aspect, ex. 2800 px de
  large) : une image se redessine instantanément, à toute taille (exemple : `profils/sakura`, arbre et fleurs) ;
- plusieurs **SVG animés en interne** (flammes, braises) superposés en grand : chacun est redessiné à chaque
  image, et le cumul fait tomber l'écran à ~50 images/s. Mieux : une image fixe (WebP) animée **en bloc** par
  `opacity` ou `transform` (calculés par la carte graphique, sans redessin) — ex. `profils/des-du-destin` :
  torches qui vacillent (`opacity`), braises qui montent (calque plus haut d'une tuile, `translateY` en boucle) ;
- même un petit SVG animé **répété sur chaque carte** (une frise de runes qui s'allume) fait redessiner toutes
  les cartes à chaque image : préfère une version fixe ;
- **animation image par image** (un dé qui roule, un feu) : une planche de N images côte à côte en WebP, posée
  sur un élément de la taille d'UNE image (`background-size: N×100% 100%`), animée par `background-position`
  de `0 0` à `100% 0` avec `steps(N, jump-none)` (N positions, pas N - 1) — ex. `profils/des-du-destin` :
  `de-roule.webp` (30 images) et `brasero.webp` (16 images en boucle) ;
- quand l'onglet est caché, le panel met toutes les animations CSS en pause (`html.nx-pause`) : rien à faire.

**Mise en cache :** les fichiers du profil sont servis avec une adresse versionnée (`?v=<signature>`,
ajoutée automatiquement aux `url(assets/…)` du CSS) et gardés en cache par le navigateur ; la signature
change dès qu'un fichier du dossier change. Il n'y a donc rien à faire après une modification, sinon
recharger la page.

**Mode jeu (économie) :** quand un jeu tourne, le panel pose `body.gamemode` et coupe **toutes** les
animations CSS (et le calque `body::before`) : l'intro s'affiche alors directement, comme sans animation.
Les animations **internes aux images SVG** continuent, elles : pour un vrai mode économie, remplace-les par
une version fixe sous `body.gamemode` (exemple : `profils/des-du-destin`, fichiers `*-fixe.svg`).

**SVG animés :** un SVG de `assets/` peut contenir un bloc `<style>` avec des `@keyframes`. Les animations
s'y jouent comme dans une image animée, et les scripts n'y sont de toute façon jamais exécutés. Exemple :
`profils/sakura/assets/arbre-pousse.svg`, l'arbre qui pousse pendant l'intro.

### 4.7 Interdit (refusé à l'import et par le validateur, retiré au chargement)

- `@import`
- `url()` vers Internet (`http:`, `https:`, `//…`), `data:`, un chemin absolu (`/…`, `C:\…`) ou contenant `..`
- toute chaîne contenant une adresse (`"https://…"`, `"//…"`)
- `expression()`, `javascript:`, `vbscript:`, `behavior:`, `-moz-binding`, `image-set()`
- toute balise HTML (`<script>`, `</style>`, `<iframe>`, …)
- les échappements CSS qui cacheraient l'un de ces mots (`\75 rl(` = `url(`) : ils sont décodés avant
  la vérification
- tout JavaScript ou HTML : un profil n'en contient jamais
- `zoom` et les variables `--nx-…` : réservés aux réglages de l'utilisateur (tailles du menu ⚙ Réglages).
  La position et la taille des fenêtres de l'agenda sont posées directement sur les éléments : un profil
  peut changer leur apparence (`.ag-panel`, `.nx-rs` = poignée), pas leur place ni leur taille.

### 4.8 Valeur des jauges : `--valeur` et `data-niveau`

Pour qu'un profil dessine ses propres jauges en CSS seul, le panel pose la valeur sur l'élément :
**`--valeur`** (nombre de 0 à 100, sans unité) et **`data-niveau`** (`bas`, `moyen`, `haut`, `critique`).

| Élément | `--valeur` | `data-niveau` |
|---|---|---|
| `.gauge` (CPU `#g-cpu`, RAM `#g-ram`, GPU `#g-gpu`, parent du canevas) | charge en % | `moyen` dès 50, `haut` dès 75, `critique` dès 90 |
| `.temp` (températures CPU / GPU) | °C (bornée à 100) | selon les seuils d'alerte de la température |
| `.disk` (un par disque) | % utilisé | comme les jauges |
| `#m-bar` (progression de la musique) | % de la piste | toujours `bas` |
| `.mx-range` (curseurs de volume ; aussi `--pct` en %) et `.mx-meter` (vumètre, mis à jour 10 fois par seconde ; l'affichage de la barre est lissé par le panel) | % | toujours `bas` |

```css
:root[data-profile] .gauge::before { content: ""; position: absolute; left: 0; bottom: 0; height: 20px;
  width: calc(100% * var(--valeur, 0) / 100); background: var(--cyan); }
:root[data-profile] .gauge[data-niveau="critique"]::before { background: var(--hot); }
:root[data-profile] .gauge canvas { visibility: hidden; }   /* masque l'arc d'origine */
```

**Animation qui ne saute pas :** le panel met les jauges à jour toutes les 2 s, et certaines barres (les
disques) sont reconstruites à chaque fois, ce qui relance une animation CSS posée sur elles. Pour un
remplissage animé continu, mets l'animation **à l'intérieur d'une image SVG** (`<style>` et `@keyframes`
dans le fichier) utilisée en fond : son animation continue d'une mise à jour à l'autre. Exemple :
`profils/des-du-destin/assets/trait-*.svg`.

## 5. `assets/` (voir aussi § 4.6 pour les SVG animés)

**Polices :** uniquement sous licence libre (OFL…), en `.woff2` dans `assets/`, déclarées par `@font-face`
avec un nom propre au profil (ex. `"NX Etoiles Titre"`). Le texte de la licence se met **à la racine du
profil** (ex. `OFL-Cinzel.txt`) : les fichiers `.txt` et `.md` de la racine sont inclus dans l'export `.zip`
et réinstallés à l'import, mais jamais servis au navigateur. Exemple : `profils/pluie-d-etoiles/`.

Types autorisés : `.png` `.jpg` `.jpeg` `.gif` `.webp` `.avif` `.svg` (images), `.woff2` `.woff` `.ttf`
`.otf` (polices). Les SVG ne doivent contenir ni `<script>`, ni `<foreignObject>`, ni attribut `on…=`,
ni `javascript:`, ni lien `href`/`src` vers Internet. Tous les fichiers sont servis avec une politique
de sécurité qui empêche toute exécution de script.

**Fichier manquant :** si `style.css` désigne un fichier absent de `assets/` (ex. une image supprimée par
erreur), le profil devient invalide : il n'est plus proposé (rubrique « profil(s) ignoré(s) » du menu) et
le panel revient tout seul au profil Défaut. Remets le fichier puis 🎨 → ⟳ Actualiser.

## 6. Limites

| Limite | Valeur |
|---|---|
| Taille totale du profil | 5 Mo |
| `style.css` | 256 Ko |
| `profil.json` | 16 Ko |
| Nombre de fichiers | 60 |

## 7. Vérifier, installer, partager

- Vérifier : `python valider_profil.py profils/<identifiant>` (ou `.venv\Scripts\python.exe valider_profil.py …`).
  Code de sortie 0 = valide, 1 = invalide, avec la liste des erreurs.
- Installer à la main : déposer le dossier dans `profils/`, puis menu 🎨 → ⟳ Actualiser.
- Partager : menu 🎨 → ⤓ sur le profil → `profil-<identifiant>.zip`. L'autre personne fait menu 🎨 →
  ⤒ Importer… (ou dépose le .zip ou le dossier sur le menu). Si un profil du même identifiant existe,
  NEXUS demande s'il faut le remplacer ou garder les deux (suffixe `-2`).
- Un profil cassé n'empêche jamais le panel de fonctionner : il est listé dans « profil(s) ignoré(s) »
  avec ses erreurs, et le profil Défaut est utilisé à sa place.
