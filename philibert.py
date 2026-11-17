"""Philibert, le petit iguane vert de NEXUS (compagnon « tamagotchi-like », règles dans docs/PHILIBERT.md).

Tout est calculé ici, côté serveur : le temps qui passe (même NEXUS fermé, rejoué par pas de 10 min à partir
des horodatages), les jauges, la chaleur (sang froid), la météo de l'île, la maladie, le vétérinaire, l'évolution,
les coquillages, la boutique et les récompenses des mini-jeux. Le navigateur n'envoie que des intentions.
Deux principes : Philibert ne meurt jamais (au pire il se repose chez la tortue vétérinaire), et c'est un vrai
iguane vert (herbivore, à sang froid).
État dans data/philibert.json (sur ce PC uniquement, hors Git).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import secrets
import threading
import time
from datetime import datetime

import store

FICHIER = store.DATA_DIR / "philibert.json"
VERSION = 1
PAS = 600.0                     # pas de simulation : 10 min
H = 3600.0
JOUR = 86400.0
ABSENCE_S = 8 * H               # au-delà : rythme ralenti et planchers
PENSION_S = 3 * JOUR            # au-delà : la voisine le prend en pension
PLANCHERS = {"faim": 20, "bonheur": 25, "proprete": 20, "chaleur": 20, "energie": 20}
SANTE_MIN = 5
JAUGES = ("faim", "bonheur", "energie", "proprete", "sante", "chaleur")
GAINS_JEUX_JOUR = 120
ENERGIE_JEU = 8                    # énergie prise au lancement d'une partie (perdue si on l'abandonne)

# ---- Mini-jeux : paliers de difficulté. Le serveur fixe les règles (envoyées à la page au lancement) et s'en sert
# pour borner les scores : un score impossible pour la durée réelle de la partie est refusé.
JEU_COMPTE = 3                     # compte à rebours avant le départ (s)
JEU_DUREE_MIN = 10                 # durée réelle minimale d'une partie à score (compte à rebours compris)
FEUILLES = {"duree_max": 180, "palier_s": 20, "palier_max": 9, "vies": 5, "ratees_par_vie": 6,
            "vitesse": [110, 90], "vitesse_pas": .16, "cadence": [.5, .35], "cadence_pas": .14,
            "fleurs": .18, "insectes": .22, "insectes_pas": .03}
COURSE = {"duree_max": 240, "etape_px": 4000, "etapes": 10, "vies": 3, "vitesse": [150, 105], "vitesse_pas": .06,
          "ecart": [380, 420], "ecart_pas": .1, "ecart_min": 250, "rayon_min": 170}
DEVIN = {"manches": 20, "erreurs": 3, "palier_manches": 4, "indice_ms": [900, 650, 460, 330, 240],
         "fiabilite": [.9, .86, .82, .78, .75]}
# « En rythme » : petit hochement, grand hochement, fanon déployé (les trois vrais signaux de l'iguane vert).
# Chaque manche tire une NOUVELLE suite, un geste de plus, et TOUS les gestes vont de plus en plus vite.
GESTES = {"petit": 1.0, "grand": 1.5, "fanon": 1.4}          # durée de chaque geste, en « temps »
RYTHME_MAX = 14
tempo_rythme = lambda manche: max(.3, .78 - .045 * manche)  # noqa: E731  (secondes par temps)


def feuilles_palier(t: float) -> int:
    """Palier de « Pluie de feuilles » après t secondes de jeu (un de plus toutes les 20 s)."""
    return min(FEUILLES["palier_max"], 1 + int(max(0.0, t) // FEUILLES["palier_s"]))


def feuilles_vitesse(p: int) -> float:
    """Facteur de vitesse de chute au palier p."""
    return 1 + FEUILLES["vitesse_pas"] * (p - 1)


def feuilles_cadence(p: int) -> float:
    """Facteur du nombre d'objets qui tombent par seconde au palier p."""
    return 1 + FEUILLES["cadence_pas"] * (p - 1)


def feuilles_objets_max(t: float) -> float:
    """Nombre d'objets au plus qui peuvent tomber en t secondes de jeu (intervalle le plus court à chaque palier)."""
    n, x, pas = 0.0, 0.0, FEUILLES["palier_s"]
    while x < t:
        d = min(pas, t - x)
        n += d * feuilles_cadence(feuilles_palier(x)) / FEUILLES["cadence"][0]
        x += d
    return n


def course_etape(dist: float) -> int:
    return min(COURSE["etapes"], 1 + int(max(0.0, dist) // COURSE["etape_px"]))


def course_vitesse(p: int) -> float:
    """Facteur de vitesse de la course à l'étape p."""
    return 1 + COURSE["vitesse_pas"] * (p - 1)


def course_ecart(p: int) -> float:
    """Facteur d'écart entre deux obstacles à l'étape p (plus petit = obstacles plus fréquents)."""
    return 1 / (1 + COURSE["ecart_pas"] * (p - 1))


def devin_palier(manche: int) -> int:
    """Palier de « Gauche ou droite ? » pour la manche n (1, 2…) : un de plus toutes les 4 manches."""
    return min(len(DEVIN["indice_ms"]), 1 + max(0, manche - 1) // DEVIN["palier_manches"])


def recompense_jeu(jeu: str, score: int, palier: int, arrivee: bool = False) -> tuple[int, int]:
    """(coquillages, bonheur) d'une partie : grandit avec le score ET le palier atteint (donc la durée)."""
    p = max(1, palier)
    if jeu == "feuilles":
        return min(30, score // 8 + 2 * (p - 1)), min(25, 5 + score // 6 + p)
    if jeu == "course":
        return min(30, score // 6 + 2 * (p - 1) + (6 if arrivee else 0)), min(25, 6 + score // 5 + p)
    if jeu == "devin":
        return min(20, score + 2 * (p - 1)), min(25, 4 + 2 * score)
    return min(25, 2 * max(0, score - 2) + (p - 1)), min(25, 4 + 2 * score)


def _suite_hochements(n: int) -> list[str]:
    """Suite au hasard (tirage du serveur) : jamais trois fois le même geste d'affilée, et au moins deux gestes différents."""
    while True:
        out: list[str] = []
        for _ in range(n):
            choix = [g for g in GESTES if not (len(out) >= 2 and out[-1] == out[-2] == g)]
            out.append(secrets.choice(choix))
        if len(set(out)) >= 2:
            return out


def _duree_suite(suite: list[str], tempo: float) -> float:
    return sum(GESTES.get(g, 1.0) for g in suite) * tempo
# « Il veut jouer / il réclame de l'attention » (ennui, caprice) : seulement quand son bonheur est à 30 ou moins
SEUIL_ATTENTION = 30
METEO_FORCEE: str | None = None  # tests : "soleil", "nuages", "pluie"
SAISON_FORCEE: str | None = None  # tests : "printemps", "ete", "automne", "hiver"
# Saisons : DEUX systèmes qui cohabitent.
# 1. Les saisons du calendrier (mois réels, comme à l'origine) : printemps, été, saison des pluies, saison fraîche ;
#    probabilités de pluie et de nuages, chaleur en plus ou en moins, produit de saison (1 coquillage de moins).
# 2. Les saisons de l'île (SAISONS_ILE), qui n'ont rien à voir avec le calendrier : chaque île a son roulement (tiré de
#    sa graine), une période de 2 à 7 jours, puis une autre (jamais la même deux fois de suite) ; parfois aucune
#    (« temps ordinaire »). Elles s'AJOUTENT à la saison du calendrier : un peu plus ou moins de pluie et de nuages,
#    de chaleur, un second produit de saison, leur décor.
SAISONS = {
    "printemps": {"nom": "Printemps", "pluie": .15, "nuages": .45, "chaleur": 0, "promo": "fleur_pissenlit",
                  "texte": "Les fleurs de pissenlit et d'hibiscus éclosent partout sur l'île."},
    "ete": {"nom": "Été", "pluie": .08, "nuages": .3, "chaleur": 5, "promo": "mangue",
            "texte": "Saison sèche et chaude : le soleil tape sur le rocher, c'est la saison des mangues."},
    "automne": {"nom": "Saison des pluies", "pluie": .26, "nuages": .58, "chaleur": -2, "promo": "figue",
                "texte": "Les averses sont fréquentes : pense à la lampe chauffante. Les figues sont mûres."},
    "hiver": {"nom": "Saison fraîche", "pluie": .14, "nuages": .55, "chaleur": -6, "promo": "chou_vert",
              "texte": "Les nuits sont plus fraîches : Philibert a besoin de plus de chaleur. Le chou vert est de saison."},
}
SAISONS_ILE = {
    "floraison": {"nom": "Grande floraison", "pluie": -.04, "nuages": -.08, "chaleur": 2, "promo": "hibiscus",
                  "texte": "Toute l'île est en fleurs : hibiscus, liserons et pissenlits. Les papillons sont partout."},
    "tempetes": {"nom": "Saison des tempêtes", "pluie": .14, "nuages": .18, "chaleur": -4, "promo": "feuilles_murier",
                 "texte": "Le vent souffle fort et la mer est agitée : garde-le au chaud, la lampe chauffante est précieuse."},
    "brumes": {"nom": "Saison des brumes", "pluie": 0, "nuages": .22, "chaleur": -3, "promo": "haricots",
               "texte": "Une brume douce enveloppe l'île : le soleil perce par moments, le rocher chauffe moins."},
    "tortues": {"nom": "Ponte des tortues", "pluie": -.04, "nuages": -.06, "chaleur": 3, "promo": "courge",
                "texte": "Les tortues marines viennent pondre la nuit : on voit leurs traces dans le sable au matin."},
}
SAISON_DUREE = (2, 7)            # jours, au hasard entre les deux pour chaque saison de l'île
ROTATION_DEBUT = 1767225600.0    # 1ᵉʳ janvier 2026 : point de départ du roulement (le même pour tous)
SAISON_ILE_FORCEE: str | None = None   # tests : "aucune" ou une clé de SAISONS_ILE


def maintenant() -> float:
    return time.time()


def _alea(*parts) -> float:
    """Nombre « au hasard » mais reproductible (0 ≤ x < 1) : même météo sur le PC et le téléphone, tests stables."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


def _heure(t: float) -> float:
    d = datetime.fromtimestamp(t)
    return d.hour + d.minute / 60


def phase_du_ciel(t: float) -> str:
    h = _heure(t)
    return "aube" if 6 <= h < 8 else "jour" if 8 <= h < 18 else "coucher" if 18 <= h < 21 else "nuit"


def heure_de_dormir(t: float) -> bool:
    h = _heure(t)
    return h >= 21 or h < 7


_ROULEMENTS: dict[str, list[tuple[float, float, str]]] = {}


def periode_saison_ile(t: float, graine: str = "") -> tuple[str | None, float, float]:
    """(saison de l'île ou None, début, fin) au temps t pour l'île de cette graine : roulement de périodes de 2 à 7
    jours, tirées au hasard (reproductible), jamais deux fois la même de suite ; None = temps ordinaire."""
    L = _ROULEMENTS.setdefault(graine, [])
    noms: list = [*SAISONS_ILE, None]

    def suivante(i: int, debut: float, avant: str | None) -> tuple[float, float, str]:
        d = (SAISON_DUREE[0] + (SAISON_DUREE[1] - SAISON_DUREE[0]) * _alea(graine, "saison-duree", i)) * JOUR
        choix = [n for n in noms if n != avant]
        return (debut, debut + d, choix[int(_alea(graine, "saison", i) * len(choix)) % len(choix)])
    if not L:
        L.append(suivante(0, ROTATION_DEBUT, None))
    if t < L[0][0]:
        return L[0][2], L[0][0], L[0][1]
    while L[-1][1] <= t:
        L.append(suivante(len(L), L[-1][1], L[-1][2]))
    lo, hi = 0, len(L) - 1
    while lo < hi:                                       # recherche dichotomique de la période qui contient t
        mid = (lo + hi) // 2
        if L[mid][1] <= t:
            lo = mid + 1
        else:
            hi = mid
    return L[lo][2], L[lo][0], L[lo][1]


def saison(t: float, graine: str = "") -> str:
    """Saison du calendrier (mois réels), comme à l'origine."""
    if SAISON_FORCEE:
        return SAISON_FORCEE
    m = datetime.fromtimestamp(t).month
    return "printemps" if 3 <= m <= 5 else "ete" if 6 <= m <= 8 else "automne" if 9 <= m <= 11 else "hiver"


def saison_ile(t: float, graine: str = "") -> str | None:
    """Saison de l'île en cours (roulement de 2 à 7 jours), ou None (temps ordinaire)."""
    if SAISON_ILE_FORCEE:
        return None if SAISON_ILE_FORCEE == "aucune" else SAISON_ILE_FORCEE
    return periode_saison_ile(t, graine)[0]


def _ciel_brut(graine: str, bloc: int) -> str:
    r = _alea(graine, "meteo", bloc)
    t = bloc * 2 * H
    sa, sp = SAISONS[saison(t, graine)], SAISONS_ILE.get(saison_ile(t, graine) or "", {})
    pluie = min(.6, max(0, sa["pluie"] + sp.get("pluie", 0)))
    nuages = min(.9, max(pluie, sa["nuages"] + sp.get("pluie", 0) + sp.get("nuages", 0)))
    return "pluie" if r < pluie else "nuages" if r < nuages else "soleil"


def meteo(t: float, graine: str) -> str:
    """soleil, nuages, pluie ou arc (arc-en-ciel : la tranche de 2 h qui suit une pluie). Jamais deux pluies de suite."""
    if METEO_FORCEE:
        return METEO_FORCEE
    b = int(t // (2 * H))

    def pluie(x):
        return _ciel_brut(graine, x) == "pluie" and _ciel_brut(graine, x - 1) != "pluie"
    if pluie(b):
        return "pluie"
    c = _ciel_brut(graine, b)
    if c == "pluie":
        c = "nuages"
    return "arc" if c == "soleil" and pluie(b - 1) else c


# --------------------------------------------------------------------------- #
#  Catalogue
# --------------------------------------------------------------------------- #
ALIMENTS = {
    # Repas du quotidien (verdure, légumes)
    "trefle": {"nom": "Trèfle de l'île", "cat": "verdure", "prix": 0, "faim": 15, "bonheur": 1, "sante": 0, "corpulence": 1,
               "texte": "Il pousse partout sur l'île : gratuit, mais un peu léger."},
    "feuilles_pissenlit": {"nom": "Feuilles de pissenlit", "cat": "verdure", "prix": 2, "faim": 28, "bonheur": 3, "sante": 1, "corpulence": 1.5,
                           "texte": "Une base parfaite pour ses repas."},
    "feuilles_murier": {"nom": "Feuilles de mûrier", "cat": "verdure", "prix": 3, "faim": 30, "bonheur": 3, "sante": 1, "corpulence": 1.5,
                        "texte": "Tendres et nourrissantes."},
    "chou_vert": {"nom": "Chou vert", "cat": "verdure", "prix": 2, "faim": 26, "bonheur": 2, "sante": 1, "corpulence": 1.5,
                  "texte": "Bien croquant."},
    "courge": {"nom": "Courge râpée", "cat": "legume", "prix": 3, "faim": 30, "bonheur": 4, "sante": 1, "corpulence": 2,
               "texte": "Un légume doux qu'il apprécie."},
    "haricots": {"nom": "Haricots verts", "cat": "legume", "prix": 3, "faim": 32, "bonheur": 3, "sante": 1, "corpulence": 2,
                 "texte": "Coupés en petits morceaux."},
    # Fleurs
    "hibiscus": {"nom": "Fleur d'hibiscus", "cat": "fleur", "prix": 4, "faim": 12, "bonheur": 12, "sante": 1, "corpulence": 1,
                 "texte": "Une jolie fleur qu'il croque avec plaisir."},
    "fleur_pissenlit": {"nom": "Fleur de pissenlit", "cat": "fleur", "prix": 3, "faim": 8, "bonheur": 15, "sante": 0, "corpulence": 1,
                        "texte": "Il adore ça !"},
    # Friandises (fruits) : à limiter
    "mangue": {"nom": "Mangue", "cat": "friandise", "prix": 5, "faim": 10, "bonheur": 20, "sante": 0, "corpulence": 6,
               "texte": "Friandise sucrée : de temps en temps."},
    "papaye": {"nom": "Papaye", "cat": "friandise", "prix": 5, "faim": 10, "bonheur": 20, "sante": 0, "corpulence": 6,
               "texte": "Friandise sucrée : de temps en temps."},
    "figue": {"nom": "Figue", "cat": "friandise", "prix": 5, "faim": 10, "bonheur": 20, "sante": 0, "corpulence": 6,
              "texte": "Friandise sucrée : de temps en temps."},
    "banane": {"nom": "Banane", "cat": "friandise", "prix": 8, "faim": 10, "bonheur": 22, "sante": 0, "corpulence": 8,
               "texte": "Très sucrée : rarement !"},
}
# Ce qu'un iguane ne mange pas : jamais en boutique, seulement en « piège » (mini-jeu, évènements)
PIEGES = {
    "grillon": {"nom": "Grillon", "astuce": "Les grillons, c'est pour d'autres lézards : l'iguane vert est herbivore."},
    "ver_farine": {"nom": "Ver de farine", "astuce": "Pas d'insectes pour Philibert : il ne mange que des plantes."},
    "croquettes": {"nom": "Croquettes pour chat", "astuce": "Les croquettes sont faites pour les chats : bien trop riches pour un iguane."},
    "jambon": {"nom": "Jambon", "astuce": "Pas de viande : un iguane vert mange des feuilles, des fleurs et un peu de fruits."},
    "poisson": {"nom": "Poisson", "astuce": "Il nage très bien, mais il ne pêche pas : pas de poisson au menu."},
}
# Rareté : « commun », « rare », « tres_rare », « legendaire ». Les pièces rares sont chères parce qu'elles sont rares
# (fabriquées à la main par les artisans de l'île voisine, en un seul exemplaire) ; les soins essentiels (remède,
# nourriture) restent toujours bon marché, et un séjour chez la vétérinaire n'est jamais bloqué faute de coquillages.
# Mutations de couleur : à chaque fin de mue, la nouvelle peau peut prendre une teinte qui raconte sa vie (comme les
# vraies formes de couleur des iguanes : bleues, rouges, orangées, tachetées, leucistiques…). On calcule un score par
# mutation ; la plus forte (≥ 1) l'emporte, avec 3 niveaux d'intensité ; une autre ne la remplace que si elle la
# dépasse nettement (× 1,25). « condition » est le texte montré dans le carnet une fois la mutation découverte.
MUTATIONS = {
    "emeraude": {"nom": "Émeraude", "texte": "Un vert vif et profond, signe d'une santé éclatante.",
                 "condition": "beaucoup de verdure et une santé excellente"},
    "orange": {"nom": "Orangé", "texte": "Des reflets orangés, comme les mâles en parade.",
               "condition": "beaucoup d'aliments orangés (courge, mangue, papaye, fleurs de pissenlit)"},
    "dore": {"nom": "Doré", "texte": "Une peau chaude aux reflets dorés, gorgée de soleil.",
             "condition": "beaucoup de soleil sur le rocher et souvent bien au chaud"},
    "turquoise": {"nom": "Turquoise", "texte": "Des écailles bleu-vert, couleur du lagon.",
                  "condition": "beaucoup de bains de mer"},
    "melanique": {"nom": "Mélanique", "texte": "Une peau très sombre : il a souvent eu froid et a foncé pour capter la chaleur.",
                  "condition": "avoir souvent eu froid"},
    "cendre": {"nom": "Cendré", "texte": "Des taches grises et pâles, souvenirs de maladies soignées trop tard.",
               "condition": "des maladies longues ou soignées trop tard"},
    "arlequin": {"nom": "Arlequin", "texte": "Des taches orange, crème et noires : la peau d'un iguane joueur et heureux.",
                 "condition": "beaucoup de jeux et un grand bonheur"},
    "lunaire": {"nom": "Lunaire", "texte": "Des reflets bleu argent, comme la lune sur la mer.",
                "condition": "souvent réveillé la nuit"},
    "leucique": {"nom": "Leucique", "texte": "Presque blanc, aux reflets nacrés : une mutation très rare.",
                 "condition": "une vie parfaite… et beaucoup de chance (très rare)"},
}
ORANGES = ("courge", "mangue", "papaye", "fleur_pissenlit", "banane")
RARETES = {"commun": "Commun", "rare": "Rare", "tres_rare": "Très rare", "legendaire": "Légendaire"}
OBJETS = {
    "remede": {"nom": "Remède de l'île", "type": "soin", "prix": 8, "texte": "À donner quand il est malade (il agit mieux au chaud)."},
    "lampe": {"nom": "Lampe chauffante", "type": "equipement", "prix": 40, "unique": True,
              "texte": "À céramique : elle chauffe sans éclairer. Pour la nuit et les jours de pluie."},
    # --- tête ---
    "chapeau": {"nom": "Chapeau de paille", "type": "accessoire", "emplacement": "tete", "prix": 25, "unique": True, "texte": "Pour le soleil des tropiques."},
    "couronne": {"nom": "Couronne d'hibiscus", "type": "accessoire", "emplacement": "tete", "prix": 30, "unique": True, "texte": "Très chic."},
    "bob": {"nom": "Bob de pêcheur", "type": "accessoire", "emplacement": "tete", "prix": 35, "unique": True, "texte": "En toile délavée, avec sa petite cordelette."},
    "tricorne": {"nom": "Tricorne de pirate", "type": "accessoire", "emplacement": "tete", "prix": 180, "unique": True, "rarete": "rare",
                 "texte": "Feutre noir et galon doré, retrouvé dans une épave. Il n'en reste que quelques-uns."},
    "couronne_or": {"nom": "Couronne d'or", "type": "accessoire", "emplacement": "tete", "prix": 450, "unique": True, "rarete": "tres_rare",
                    "texte": "Or ciselé, rubis, saphir et émeraude : forgée pour le roi des iguanes."},
    "diademe": {"nom": "Diadème de nacre", "type": "accessoire", "emplacement": "tete", "prix": 800, "unique": True, "rarete": "legendaire",
                "texte": "Nacre irisée et perles fines, une seule pièce au monde. Le trésor des artisans de l'île voisine."},
    # --- yeux ---
    "lunettes": {"nom": "Lunettes de soleil", "type": "accessoire", "emplacement": "yeux", "prix": 20, "unique": True, "texte": "La classe à la plage."},
    "lunettes_coeur": {"nom": "Lunettes en cœur", "type": "accessoire", "emplacement": "yeux", "prix": 45, "unique": True, "texte": "Verres roses en forme de cœur."},
    "monocle": {"nom": "Monocle doré", "type": "accessoire", "emplacement": "yeux", "prix": 150, "unique": True, "rarete": "rare",
                "texte": "Cerclé d'or, avec sa chaînette. Pour un iguane distingué."},
    # --- cou ---
    "collier": {"nom": "Collier de fleurs", "type": "accessoire", "emplacement": "cou", "prix": 18, "unique": True, "texte": "Un collier fleuri, façon île."},
    "foulard": {"nom": "Foulard", "type": "accessoire", "emplacement": "cou", "prix": 15, "unique": True, "texte": "Un petit foulard à pois."},
    "noeud": {"nom": "Nœud papillon", "type": "accessoire", "emplacement": "cou", "prix": 30, "unique": True, "texte": "Rouge, pour les grandes occasions."},
    "perles": {"nom": "Collier de perles", "type": "accessoire", "emplacement": "cou", "prix": 220, "unique": True, "rarete": "rare",
               "texte": "De vraies perles du lagon, patiemment assorties."},
    "medaille": {"nom": "Médaille d'or", "type": "accessoire", "emplacement": "cou", "prix": 400, "unique": True, "rarete": "tres_rare",
                 "texte": "Frappée d'un coquillage, sur une chaîne d'or. Remise aux iguanes les plus choyés."},
    "cape": {"nom": "Cape royale", "type": "accessoire", "emplacement": "cou", "prix": 900, "unique": True, "rarete": "legendaire",
             "texte": "Velours rouge, galon d'or et col d'hermine. Taillée sur mesure, il n'en existe qu'une."},
    # --- déco de l'île ---
    "hamac": {"nom": "Hamac", "type": "deco", "prix": 30, "unique": True, "texte": "Entre le palmier et un piquet."},
    "chateau": {"nom": "Château de sable", "type": "deco", "prix": 12, "unique": True, "texte": "Avec un petit drapeau."},
    "coquillages_deco": {"nom": "Coquillages décoratifs", "type": "deco", "prix": 10, "unique": True, "texte": "Une jolie rangée sur le sable."},
    "parasol": {"nom": "Parasol", "type": "deco", "prix": 20, "unique": True, "texte": "Rayé, pour l'ombre."},
    "bouee": {"nom": "Bouée", "type": "deco", "prix": 15, "unique": True, "texte": "Elle flotte près du bord."},
    "tiki": {"nom": "Statue tiki", "type": "deco", "prix": 120, "unique": True, "rarete": "rare", "texte": "Sculptée dans un tronc de cocotier par un artisan de l'île voisine."},
    "phare": {"nom": "Petit phare", "type": "deco", "prix": 260, "unique": True, "rarete": "rare", "texte": "Sur son rocher, au large. Il s'allume la nuit."},
    "coffre": {"nom": "Coffre au trésor", "type": "deco", "prix": 500, "unique": True, "rarete": "tres_rare", "texte": "À moitié enfoui, plein de pièces d'or qui brillent au soleil."},
    "benitier": {"nom": "Bénitier et sa perle", "type": "deco", "prix": 750, "unique": True, "rarete": "legendaire",
                 "texte": "Un grand coquillage du lagon, avec une perle géante. Une merveille."},
}
for _o in OBJETS.values():
    _o.setdefault("rarete", "commun")
EMPLACEMENTS = ("tete", "yeux", "cou")
VARIANTES = {"insulaire": "l'Insulaire", "royal": "le Royal", "gourmand": "le Gourmand", "nageur": "le Nageur",
             "convalescent": "le Convalescent"}
STADES = {"oeuf": "Œuf", "bebe": "Bébé", "juvenile": "Juvénile", "adulte": "Adulte", "sage": "Vieux sage"}
MALADIES = {"froid": "un rhume", "fruits": "une indigestion", "faim": "une petite faiblesse", "proprete": "une petite infection",
            "soleil": "des os fragiles (manque de soleil)", "fatigue": "un gros coup de fatigue"}
RAISONS = {
    "froid": ("Il avait trop froid, surtout la nuit.",
              "Un iguane a le sang froid : laisse-le se dorer sur le rocher le jour, et pense à la lampe chauffante la nuit ou quand il pleut."),
    "fruits": ("Trop de friandises : son ventre était tout rond.",
               "Les fruits, c'est pour les petites fêtes. La base, c'est la verdure : pissenlit, mûrier, chou vert, trèfle."),
    "faim": ("Il avait le ventre vide depuis trop longtemps.", "Plusieurs petits repas de verdure dans la journée, c'est l'idéal."),
    "proprete": ("Son coin de plage n'était plus très propre.", "Ramasse ses petites crottes et offre-lui un bain tiède de temps en temps."),
    "soleil": ("Il manquait de soleil.", "Le soleil l'aide à avoir des os solides : un moment sur le rocher chaud chaque jour."),
    "fatigue": ("Il était épuisé.", "La nuit, éteins la lumière et laisse-le dormir en haut de son palmier."),
}
FAITS = {
    "herbivore": "L'iguane vert est herbivore : il mange surtout des feuilles, des fleurs et un peu de fruits.",
    "fruits": "Les fruits sont trop sucrés pour faire la base de ses repas : ce sont des friandises.",
    "sang_froid": "C'est un lézard à sang froid : il a besoin de la chaleur du soleil pour bouger et bien digérer.",
    "uv": "La lumière du soleil (les UVB) l'aide à fabriquer de la vitamine D, utile pour avoir des os solides.",
    "couleur": "Il n'est pas toujours du même vert : sa teinte peut foncer ou changer selon la température, l'âge ou la saison.",
    "fanon": "Le fanon, la grande peau sous son menton, l'aide à communiquer et à se réchauffer.",
    "hochement": "Les iguanes « parlent » en hochant la tête : petits hochements rapides ou grands mouvements lents.",
    "oeil": "Il a un « troisième œil » sur le dessus de la tête (l'œil pariétal) qui perçoit la lumière et les ombres.",
    "nage": "C'est un très bon nageur : il replie ses pattes et ondule avec sa longue queue.",
    "mue": "Il mue par petits morceaux, et pas d'un seul coup comme les serpents.",
    "arbres": "Dans la nature, il vit dans les arbres près de l'eau et dort souvent sur une branche.",
    "queue": "Pour échapper à un prédateur, sa queue peut se détacher. Elle repousse, en plus court.",
    "oeufs": "Les bébés iguanes sortent d'œufs enterrés dans le sable chaud, après deux à trois mois d'incubation.",
    "taille": "Un iguane vert adulte peut dépasser 1,5 mètre de long, queue comprise.",
    "dents": "Ses petites dents tranchantes sont faites pour découper les feuilles.",
    "chute": "Il grimpe très haut et peut tomber de plusieurs mètres sans se faire mal.",
    "refus": "Insectes, viande, croquettes : un iguane vert n'en a pas besoin, il ne mange que des plantes.",
    "eau": "Beaucoup d'iguanes aiment faire leurs besoins dans l'eau de leur bain.",
    "ponte": "Dans la nature, les femelles iguanes pondent souvent pendant la saison sèche, dans un terrier creusé dans le sable ou la terre.",
    "formes": "Il existe de vraies « formes de couleur » chez les iguanes : bleues, rouges, orangées, tachetées, presque blanches… Et leur teinte change aussi avec la température.",
    "fraicheur": "Quand il fait plus frais, un iguane bouge moins et mange moins : il a besoin de chaleur pour être actif.",
}
SUCCES = {
    "eclosion": ("Bienvenue, Philibert !", "Voir l'œuf éclore", 5),
    "premier_repas": ("Premier repas", "Lui donner à manger une première fois", 2),
    "gourmet": ("Gourmet de verdure", "Lui faire goûter 6 verdures et légumes différents", 8),
    "fleurs": ("Bouquet gourmand", "Lui offrir 5 fleurs", 5),
    "bronzage": ("Lézard au soleil", "L'envoyer 10 fois se dorer sur le rocher", 8),
    "nageur": ("Petit nageur", "10 bains de mer", 10),
    "premiere_mue": ("Peau neuve", "Vivre sa première mue", 5),
    "bonne_nuit": ("Bonne nuit, Philibert", "Éteindre la lumière 5 nuits", 8),
    "refus": ("Il sait ce qu'il mange", "Voir Philibert refuser un aliment qui n'est pas pour lui", 5),
    "comme_neuf": ("Comme neuf", "Le voir revenir de chez la tortue vétérinaire", 5),
    "gueri": ("Remis sur pattes", "Le soigner à la maison", 8),
    "feuilles": ("Attrape-feuilles", "Atteindre le palier 5 à « Pluie de feuilles »", 10),
    "devin": ("Devin de l'île", "10 bonnes réponses dans une partie de « Gauche ou droite ? »", 10),
    "rythme": ("Dans le rythme", "Répéter une suite de 8 gestes à « En rythme »", 10),
    "juvenile": ("Ça pousse !", "Devenir juvénile", 5),
    "adulte": ("Grand iguane", "Devenir adulte", 10),
    "sage": ("Vieux sage", "Devenir un vieux sage", 20),
    "semaine": ("Une semaine ensemble", "7 jours de vie", 10),
    "coquet": ("Coquet", "Avoir 3 accessoires", 5),
    "decorateur": ("Décorateur", "Installer 3 décorations sur l'île", 5),
    "tresor": ("Trésor de l'île", "Avoir 100 coquillages en poche", 0),
    "coureur": ("Coureur du soleil", "Arriver au rocher chaud (étape 10) avec 60 rayons de soleil ou plus", 10),
    "saisons": ("Les quatre saisons", "Vivre les quatre saisons de l'île", 15),
    "tour_saisons": ("Saisons de l'île", "Vivre les quatre saisons spéciales de l'île (floraison, tempêtes, brumes, ponte des tortues)", 20),
    "mutation": ("Couleurs uniques", "Voir Philibert changer de couleur à une mue", 10),
    "collection": ("Pièce de collection", "Acheter un objet légendaire", 0),
}
EVENEMENTS = {
    "croquettes": {"texte": "Un touriste a oublié des croquettes pour chat sur la plage.", "aliment": "croquettes",
                   "choix": {"proposer": "Les proposer à Philibert", "jeter": "Les jeter à la poubelle"}},
    "poisson": {"texte": "Une mouette a lâché un poisson tout près de Philibert.", "aliment": "poisson",
                "choix": {"proposer": "Le proposer à Philibert", "jeter": "Le rendre à la mer"}},
    "coco": {"texte": "Une noix de coco a roulé jusqu'à la plage… il y a des coquillages dessous !", "choix": {"ramasser": "Ramasser les coquillages"}},
    "bouteille": {"texte": "Une bouteille à la mer s'est échouée. Il y a un message dedans !", "choix": {"lire": "Lire le message"}},
    "crabe": {"texte": "Un petit crabe tourne autour de Philibert : il a l'air de vouloir jouer.", "choix": {"jouer": "Les laisser jouer"}},
}
JEUX = {"feuilles": "Pluie de feuilles", "devin": "Gauche ou droite ?", "rythme": "En rythme", "course": "Course au rocher chaud"}


class PhilibertErreur(Exception):
    """Action impossible (message lisible, affiché tel quel)."""


def _borne(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _jour(t: float) -> str:
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
#  Moteur
# --------------------------------------------------------------------------- #
class Philibert:
    def __init__(self, journal=None, notifier=None) -> None:
        self.journal = journal or (lambda *a, **k: None)          # activite.noter
        self.notifier = notifier or (lambda titre, texte: None)   # Discord (si réglé)
        self._lock = threading.Lock()
        self._sauve_t = float("-inf")         # (pas 0 : time.monotonic() peut valoir moins de 300 s juste après le démarrage de Windows)
        try:
            s = json.loads(FICHIER.read_text(encoding="utf-8"))
            if not isinstance(s, dict) or s.get("v") != VERSION:
                raise ValueError
            self.s = self._completer(s)
        except (OSError, ValueError):
            self.s = self._nouveau(maintenant())
            self._note(self.s["ne"], "naissance", "Un œuf est apparu dans le sable chaud de l'île.")
            self._sauver(force=True)

    # -- données -----------------------------------------------------------------
    @staticmethod
    def _nouveau(now: float, reglages: dict | None = None, album: list | None = None) -> dict:
        return {
            "v": VERSION, "graine": secrets.token_hex(8), "ne": now, "eclos": None, "maj": now, "contact": now,
            "age_s": 0.0, "stade": "oeuf", "variante": None,
            "j": {"faim": 80.0, "bonheur": 80.0, "energie": 90.0, "proprete": 100.0, "sante": 100.0, "chaleur": 70.0},
            "corpulence": 50.0, "uv": 70.0, "discipline": 30.0,
            "position": "plage", "rocher_depuis": None, "lumiere": True,
            "lampe": {"possede": False, "allumee": False},
            "crottes": 0, "crottes_a_venir": [], "mue": None, "prochaine_mue": 2 * JOUR,
            "malade": None, "causes": {}, "plancher_h": 0.0, "veto": None, "vacances": None,
            "appel": None, "appel_pause": 0.0, "evenement": None, "prochain_evenement": now + 3 * H,
            "eveil_nuit": 0.0, "grognon": 0.0, "sieste": False, "nuit_eteinte": "",
            "coquillages": 20, "inventaire": {"feuilles_pissenlit": 3, "hibiscus": 1, "remede": 1},
            "accessoires": [], "portes": {}, "deco": [],
            "stats": {"repas": 0, "verdure": 0, "fleurs": 0, "friandises": 0, "refus": 0, "bains": 0, "bains_mer": 0,
                      "soleil": 0, "jeux": 0, "caresses": 0, "nettoyages": 0, "remedes": 0, "maladies": 0, "gueris": 0,
                      "sejours_veto": 0, "mues": 0, "gronder": 0, "feliciter": 0, "nuits_eteintes": 0,
                      "coquillages_gagnes": 0, "meilleur_feuilles": 0, "meilleur_rythme": 0, "meilleur_devin": 0,
                      "meilleur_course": 0, "courses_gagnees": 0, "oranges": 0, "heures_froid": 0.0, "heures_chaud": 0.0,
                      "heures_malade": 0.0, "nuits_reveille": 0},
            "mutation": None, "mutations_vues": [],
            "gouts": [], "moy": {"sante": 0.0, "bonheur": 0.0, "n": 0.0}, "regime": [], "friandises_t": [],
            "carnet": [], "cartes": [], "succes": {}, "succes_vus": [], "faits": [],
            "reglages": {"visible": True, "vitesse": "normale", "sons": True, "ambiance": True, "theme": "auto", "notif_windows": False, "discord": False,
                         **(reglages or {})},
            "jeu": None, "jeux_jour": {"jour": "", "gagnes": 0}, "ramasse": 0.0, "bonne": None,
            "album": list(album or []), "etapes": [], "saisons_vues": [], "saisons_ile_vues": [],
            "cd": {}, "bain_sante_jour": "", "dernier_froid": False, "nouveau": [],
        }

    def _completer(self, s: dict) -> dict:
        """Ajoute les clés manquantes (fichier d'une version précédente du jeu) sans rien perdre."""
        base = self._nouveau(s.get("ne") or maintenant())
        for k, v in base.items():
            if k not in s:
                s[k] = v
            elif isinstance(v, dict) and isinstance(s[k], dict) and k not in ("inventaire", "portes", "succes", "causes", "cd"):
                for k2, v2 in v.items():
                    s[k].setdefault(k2, v2)
        return s

    def _sauver(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._sauve_t < 300:
            return
        try:
            FICHIER.parent.mkdir(parents=True, exist_ok=True)
            tmp = FICHIER.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.s, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            tmp.replace(FICHIER)
            self._sauve_t = now
        except OSError:
            pass

    def _note(self, t: float, type_: str, texte: str) -> None:
        self._sauve_t = float("-inf")                  # évènement marquant : enregistré à la prochaine occasion
        self.s["carnet"].append({"t": round(t), "type": type_, "texte": texte})
        del self.s["carnet"][:-300]

    def _fait(self, fid: str) -> None:
        if fid in FAITS and fid not in self.s["faits"]:
            self.s["faits"].append(fid)
            self.s["nouveau"].append({"type": "fait", "id": fid})

    def _succes(self, sid: str, t: float) -> None:
        if sid in SUCCES and sid not in self.s["succes"]:
            self.s["succes"][sid] = round(t)
            nom, _, gain = SUCCES[sid]
            self.s["coquillages"] += gain
            self._note(t, "succes", f"Succès : « {nom} »" + (f" (+{gain} coquillages)" if gain else ""))
            self.s["nouveau"].append({"type": "succes", "id": sid})

    def _verifier_succes(self, t: float) -> None:
        s, st = self.s, self.s["stats"]
        conds = {
            "gourmet": len(s["gouts"]) >= 6, "fleurs": st["fleurs"] >= 5, "bronzage": st["soleil"] >= 10,
            "nageur": st["bains_mer"] >= 10, "premiere_mue": st["mues"] >= 1, "bonne_nuit": st["nuits_eteintes"] >= 5,
            "refus": st["refus"] >= 1, "comme_neuf": st["sejours_veto"] >= 1, "gueri": st["gueris"] >= 1,
            "feuilles": st.get("palier_feuilles", 0) >= 5, "devin": st["meilleur_devin"] >= 10, "rythme": st["meilleur_rythme"] >= 8,
            "semaine": s["age_s"] >= 7 * JOUR, "coquet": len(s["accessoires"]) >= 3, "decorateur": len(s["deco"]) >= 3,
            "tresor": s["coquillages"] >= 100,
            "collection": any(OBJETS[x]["rarete"] == "legendaire" for x in s["accessoires"] + s["deco"] if x in OBJETS),
        }
        for k, c in conds.items():
            if c:
                self._succes(k, t)

    # -- temps qui passe -----------------------------------------------------------
    def _vitesse(self) -> float:
        return 0.5 if self.s["reglages"].get("vitesse") == "lente" else 1.0

    def _avancer(self, now: float) -> None:
        s = self.s
        t = s["maj"]
        while t < now:
            if s["vacances"]:
                break
            if s["veto"]:
                if now >= s["veto"]["retour"]:
                    t = max(t, s["veto"]["retour"])
                    self._retour_veto(t)
                    continue
                break
            if t - s["contact"] >= PENSION_S:
                if s["malade"]:                        # malade : la voisine appelle d'abord la tortue vétérinaire
                    self._depart_veto(t)
                    continue
                self._pension(t, auto=True)
                break
            dt = min(PAS, now - t)
            self._pas(t, dt)
            t += dt
        s["maj"] = max(s["maj"], now)

    def _cible_chaleur(self, t: float) -> float:
        s = self.s
        ph, ciel = phase_du_ciel(t), meteo(t, s["graine"])
        pos = s["position"]
        if ph == "nuit":
            c = 30 if pos == "rocher" else 28 if pos == "palmier" else 25
        elif pos == "rocher":
            c = {"soleil": 95, "arc": 95, "nuages": 70, "pluie": 45}[ciel]
            if ph != "jour" and ciel in ("soleil", "arc"):
                c = 65
        elif pos == "eau":
            c = 40
        else:
            c = {"soleil": 62, "arc": 62, "nuages": 52, "pluie": 38}[ciel]
            if ph != "jour":
                c -= 6
        c += SAISONS[saison(t, s["graine"])]["chaleur"] + SAISONS_ILE.get(saison_ile(t, s["graine"]) or "", {}).get("chaleur", 0)
        if s["lampe"]["possede"] and s["lampe"]["allumee"]:
            c = max(c, 72 if ph == "nuit" else 76)
        return c

    def _pas(self, t: float, dt: float) -> None:
        s, j = self.s, self.s["j"]
        f = self._vitesse()
        hh = dt / H * f
        if s["stade"] == "oeuf":
            s["age_s"] += dt * f
            if s["age_s"] >= 600:
                self._eclore(t + dt)
            return
        s["age_s"] += dt * f
        sa = saison(t, s["graine"])
        if sa not in s["saisons_vues"]:
            s["saisons_vues"].append(sa)
            if sa == "ete":
                self._fait("ponte")
            elif sa == "hiver":
                self._fait("fraicheur")
            if len(s["saisons_vues"]) >= 4:
                self._succes("saisons", t)
        sp = saison_ile(t, s["graine"])
        vues_ile = s.setdefault("saisons_ile_vues", [])
        if sp and sp not in vues_ile:
            vues_ile.append(sp)
            if sp == "tortues":
                self._fait("ponte")
            if len(vues_ile) >= len(SAISONS_ILE):
                self._succes("tour_saisons", t)
        nuit = heure_de_dormir(t)
        eveille = s["eveil_nuit"] > t
        absent = t - s["contact"] > ABSENCE_S
        avant = dict(j)
        # où est-il ?
        if nuit and not eveille:
            s["position"] = "palmier"
            s["sieste"] = False
        elif s["position"] in ("palmier", "eau"):
            s["position"] = "plage"
        if not nuit:
            s["lumiere"] = True
        if s["position"] == "rocher" and not s["sieste"] and (j["chaleur"] >= 92 or t - (s["rocher_depuis"] or t) >= 2 * H):
            s["position"] = "plage"
            s["bonne"] = {"t": t, "quoi": "rocher"}
        dort = (nuit and not eveille) or s["sieste"]
        ciel = meteo(t, s["graine"])
        ph = phase_du_ciel(t)
        # chaleur : se rapproche de la température de l'endroit
        cible = self._cible_chaleur(t)
        k = 0.9 if cible > j["chaleur"] else 0.35
        j["chaleur"] += (cible - j["chaleur"]) * (1 - math.exp(-k * hh))
        # soleil (UV)
        if s["position"] == "rocher" and ph != "nuit":
            gain = {"soleil": 25, "arc": 25, "nuages": 10, "pluie": 0}[ciel] * (1 if ph == "jour" else .5)
            s["uv"] += gain * hh
            if gain:
                self._fait("uv")
        s["uv"] = _borne(s["uv"] - 1.2 * hh)
        m = 0.5 if absent else 1.0
        froid, chaud = j["chaleur"] < 35, j["chaleur"] >= 70
        malade = s["malade"] is not None
        st = s["stats"]
        st["heures_froid"] = st.get("heures_froid", 0) + (hh if froid else 0)
        st["heures_chaud"] = st.get("heures_chaud", 0) + (hh if j["chaleur"] >= 75 else 0)
        st["heures_malade"] = st.get("heures_malade", 0) + (hh if malade else 0)
        if froid and not s["dernier_froid"]:
            self._fait("couleur")
        s["dernier_froid"] = froid
        lent_nuit = 1 / 3 if dort and nuit else 1
        j["faim"] -= 5 * (.5 if froid else 1) * lent_nuit * hh * m
        bonheur = 3 * (2 / 3 if chaud else 1) * (1.5 if malade else 1) * lent_nuit
        if s["mue"]:
            bonheur += .5
        if dort and nuit and s["lumiere"]:
            bonheur += .5
        j["bonheur"] -= bonheur * hh * m
        if dort:
            j["energie"] += (10 if s["sieste"] else 7 if s["lumiere"] else 14) * hh
        else:
            j["energie"] -= 4 * (1.3 if froid else 1) * (1.5 if malade else 1) * hh * m
        j["proprete"] -= (1.5 + 2 * s["crottes"]) * hh * m
        s["corpulence"] -= (.2 if dort else .5 * (1 if j["chaleur"] >= 50 else .5)) * hh
        if j["faim"] < 15:
            s["corpulence"] -= .5 * hh
        s["corpulence"] = _borne(s["corpulence"], 10, 100)
        # crottes (environ 3 h après un repas)
        venir = [c for c in s["crottes_a_venir"] if c > t + dt]
        n = len(s["crottes_a_venir"]) - len(venir)
        if n:
            s["crottes"] = min(4, s["crottes"] + n)
            s["crottes_a_venir"] = venir
        # mue
        if s["mue"]:
            if s["age_s"] - s["mue"]["depuis"] >= 30 * H:
                self._fin_mue(t, bain=False)
        elif s["age_s"] >= s["prochaine_mue"] and not malade:
            s["mue"] = {"depuis": s["age_s"], "t": t}
            self._note(t, "mue", "Philibert commence à muer : il pèle par petits morceaux.")
        # santé
        d, causes = 0.0, []
        if j["faim"] < 20:
            d -= 2.5
            causes.append("faim")
        if j["proprete"] < 25:
            d -= 1.5
            causes.append("proprete")
        if j["chaleur"] < 35:
            d -= 2
            causes.append("froid")
        if s["corpulence"] > 78:
            d -= .8
            causes.append("fruits")
        if s["uv"] < 25:
            d -= .6
            causes.append("soleil")
        if j["energie"] < 15:
            d -= 1
            causes.append("fatigue")
        d *= m
        if malade:
            d += 1.2 if j["chaleur"] >= 60 and (dort or j["energie"] >= 40) else -.5
        elif not causes and j["faim"] >= 35 and j["proprete"] >= 35 and j["chaleur"] >= 40:
            d += 1.5
        for c in causes:
            s["causes"][c] = s["causes"].get(c, 0) + hh
        j["sante"] += d * hh
        # bornes et planchers (absence : les jauges ne descendent pas sous leur plancher)
        for g in JAUGES:
            lo = SANTE_MIN if g == "sante" else 0
            if absent and g in PLANCHERS:
                lo = max(lo, min(avant[g], PLANCHERS[g]))
            j[g] = _borne(j[g], lo, 100)
        # sieste de jour
        if not nuit:
            if not s["sieste"] and j["energie"] < 15:
                s["sieste"] = True
                # fatigué en plein soleil : il va faire sa sieste à plat ventre sur le rocher chaud (il s'y réchauffe)
                if ph == "jour" and ciel in ("soleil", "arc") and s["position"] == "plage" and j["chaleur"] < 80:
                    s["position"], s["rocher_depuis"] = "rocher", t
            elif s["sieste"] and j["energie"] >= 50:
                s["sieste"] = False
        # maladie
        s["friandises_t"] = [x for x in s["friandises_t"] if x > t - JOUR]
        if not malade and (j["sante"] < 35 or len(s["friandises_t"]) >= 5):
            cause = "fruits" if len(s["friandises_t"]) >= 5 else max(s["causes"], key=s["causes"].get) if s["causes"] else "fatigue"
            s["malade"] = {"cause": cause, "depuis": t, "cumul": 0.0}
            j["sante"] = min(j["sante"], 34)
            s["stats"]["maladies"] += 1
            self._note(t, "maladie", f"Philibert est malade : {MALADIES[cause]}.")
            if s["reglages"].get("discord"):
                self.notifier("🦎 Philibert est malade", f"Il a {MALADIES[cause]}. Un remède et un peu de chaleur l'aideront.")
        elif malade:
            s["malade"]["cumul"] += hh
            encore = s["malade"]["cause"] == "fruits" and (len(s["friandises_t"]) >= 3 or s["corpulence"] > 75)
            if j["sante"] >= 60 and not encore:
                self._guerir(t, "Il s'est remis tout seul, au chaud et au repos.")
        s["plancher_h"] = s["plancher_h"] + hh if j["sante"] <= SANTE_MIN + 1 else 0.0
        if s["malade"] and (s["malade"]["cumul"] >= 18 or s["plancher_h"] >= 3):
            self._depart_veto(t + dt)
            return
        # appels (vrais besoins ou caprices)
        a = s["appel"]
        if a and a["type"] == "caprice" and j["bonheur"] > SEUIL_ATTENTION:     # il est redevenu content : plus d'appel
            s["appel"], a = None, None
        if a and t >= a["t"] + 2 * H:
            if a["type"] == "besoin":
                j["bonheur"] = max(min(j["bonheur"], PLANCHERS["bonheur"]) if absent else 0, j["bonheur"] - 5)
            else:
                s["discipline"] = _borne(s["discipline"] + 3)
            s["appel"], s["appel_pause"] = None, t + H
        if not s["appel"] and not dort and t >= s["appel_pause"]:
            b = self._besoins(t)
            vrais = [x for x in b if x["id"] not in ("ventre", "lumiere")]
            if vrais:
                s["appel"] = {"t": t, "type": "besoin", "raison": vrais[0]["id"]}
            elif j["bonheur"] <= SEUIL_ATTENTION and _alea(s["graine"], "caprice", int(t // PAS)) < .035 * (1 - s["discipline"] / 130):
                s["appel"] = {"t": t, "type": "caprice", "raison": "caprice"}
        # évènements de l'île (le jour, éveillé)
        e = s["evenement"]
        if e and t >= e["t"] + 6 * H:
            s["evenement"] = None
        if not s["evenement"] and not dort and t >= s["prochain_evenement"]:
            types = list(EVENEMENTS)
            s["evenement"] = {"id": types[int(_alea(s["graine"], "evt", int(t // PAS)) * len(types))], "t": t}
            s["prochain_evenement"] = t + 6 * H + _alea(s["graine"], "evt2", int(t // PAS)) * 4 * H
        # moyennes de soins (pour l'évolution) et stade
        s["moy"]["sante"] += j["sante"] * hh
        s["moy"]["bonheur"] += j["bonheur"] * hh
        s["moy"]["n"] += hh
        self._grandir(t + dt)

    # -- étapes de la vie ----------------------------------------------------------
    def _eclore(self, t: float) -> None:
        s = self.s
        s["stade"], s["eclos"], s["age_s"] = "bebe", t, 0.0
        s["prochaine_mue"] = 2 * JOUR
        self._note(t, "eclosion", "Crac ! L'œuf a éclos : voici Philibert, un tout petit iguane vert.")
        self._etape(t)
        self._fait("oeufs")
        self._succes("eclosion", t)
        self.journal("philibert", "éclosion", "ok", "Philibert est né")

    def _stade_pour_age(self) -> str:
        jours = self.s["age_s"] / JOUR
        return "bebe" if jours < 2 else "juvenile" if jours < 7 else "adulte" if jours < 30 else "sage"

    def _choisir_variante(self) -> str:
        s, st = self.s, self.s["stats"]
        n = max(1e-9, s["moy"]["n"])
        sante, bonheur = s["moy"]["sante"] / n, s["moy"]["bonheur"] / n
        repas = max(1, st["repas"])
        part_fruits = st["friandises"] / repas
        if st["sejours_veto"] >= 2:
            return "convalescent"
        if sante >= 80 and bonheur >= 70 and part_fruits <= .2 and st["sejours_veto"] == 0:
            return "royal"
        if part_fruits >= .3 or s["corpulence"] > 75:
            return "gourmand"
        if st["bains_mer"] >= 8:
            return "nageur"
        return "insulaire"

    def _grandir(self, t: float) -> None:
        s = self.s
        if s["stade"] == "oeuf":
            return
        ordre = ["bebe", "juvenile", "adulte", "sage"]
        cible = self._stade_pour_age()
        while ordre.index(s["stade"]) < ordre.index(cible):
            s["stade"] = ordre[ordre.index(s["stade"]) + 1]
            if s["stade"] == "adulte":
                s["variante"] = self._choisir_variante()
                texte = f"Philibert est adulte : le voici « Philibert {VARIANTES[s['variante']]} » !"
                self._fait("chute")
            elif s["stade"] == "sage":
                texte = "Philibert est devenu un vieux sage de l'île. Il a vu tant de couchers de soleil !"
            else:
                texte = "Philibert est maintenant juvénile : sa crête pousse et il grimpe partout."
                self._fait("taille")
            self._note(t, "evolution", texte)
            self._etape(t)
            self._succes(s["stade"], t)
            self.journal("philibert", f"évolution : {STADES[s['stade']].lower()}", "ok", self.titre())

    def _etape(self, t: float) -> None:
        """Une photo de chaque étape de sa vie (album illustré du carnet)."""
        s = self.s
        s["etapes"].append({"t": round(t), "stade": s["stade"], "variante": s["variante"], "portes": dict(s["portes"]),
                            "mutation": dict(s["mutation"]) if s.get("mutation") else None,
                            "age_jours": round(s["age_s"] / JOUR, 1), "titre": self.titre()})
        del s["etapes"][:-10]

    def _fin_mue(self, t: float, bain: bool) -> None:
        s = self.s
        s["mue"] = None
        s["stats"]["mues"] += 1
        s["prochaine_mue"] = s["age_s"] + {"bebe": 2, "juvenile": 2, "adulte": 5, "sage": 7}.get(s["stade"], 3) * JOUR
        self._note(t, "mue", "Mue terminée grâce au bain : il a une peau toute neuve !" if bain
                   else "Mue terminée toute seule (un bain tiède l'aide à aller plus vite).")
        self._fait("mue")
        self._succes("premiere_mue", t)
        self._muter(t)

    def scores_mutation(self) -> dict:
        """Score de chaque mutation (≥ 1 : possible à la prochaine mue). Lisible pour les tests et le carnet."""
        s, st = self.s, self.s["stats"]
        n = max(1e-9, s["moy"]["n"])
        sante, bonheur = s["moy"]["sante"] / n, s["moy"]["bonheur"] / n
        repas = max(1, st["repas"])
        g = st.get
        return {
            "emeraude": (st["verdure"] / repas / .75) * (sante / 85) if st["verdure"] >= 12 else 0,
            "orange": (g("oranges", 0) / repas / .3) if g("oranges", 0) >= 6 else 0,
            "dore": min(st["soleil"] / 15, g("heures_chaud", 0) / 40) if st["soleil"] >= 8 else 0,
            "turquoise": st["bains_mer"] / 10,
            "melanique": g("heures_froid", 0) / 30,
            "cendre": max(g("heures_malade", 0) / 30, st["sejours_veto"] / 2),
            "arlequin": min(st["jeux"] / 25, bonheur / 75) if st["jeux"] >= 10 else 0,
            "lunaire": g("nuits_reveille", 0) / 6,
            "leucique": 0,
        }

    def _muter(self, t: float) -> None:
        s = self.s
        if s["stade"] == "bebe":                                  # les couleurs se fixent à partir du stade juvénile
            return
        sc = self.scores_mutation()
        n = max(1e-9, s["moy"]["n"])
        if s["moy"]["sante"] / n >= 85 and s["moy"]["bonheur"] / n >= 85 and _alea(s["graine"], "leucique", s["stats"]["mues"]) < .03:
            sc["leucique"] = 3.0
        best = max(sc, key=sc.get)
        if sc[best] < 1:
            return
        niveau = 3 if sc[best] >= 2.4 else 2 if sc[best] >= 1.6 else 1
        cur = s.get("mutation")
        if cur and cur["id"] != best and sc[best] < 1.25 * max(1, sc.get(cur["id"], 0)):
            best, niveau = cur["id"], max(cur["niveau"], 3 if sc[cur["id"]] >= 2.4 else 2 if sc[cur["id"]] >= 1.6 else 1)
        if cur and cur["id"] == best and cur["niveau"] >= niveau:
            return
        nouveau = not cur or cur["id"] != best
        s["mutation"] = {"id": best, "niveau": niveau, "depuis": round(t)}
        if best not in s.setdefault("mutations_vues", []):
            s["mutations_vues"].append(best)
        m = MUTATIONS[best]
        self._note(t, "mutation", (f"Nouvelle peau, nouvelle couleur : Philibert devient « {m['nom']} » ! {m['texte']}" if nouveau
                                   else f"Sa couleur « {m['nom']} » est encore plus marquée après cette mue."))
        self._fait("formes")
        self._succes("mutation", t)

    def _mutation_vue(self) -> dict | None:
        m = self.s.get("mutation")
        if not m or m["id"] not in MUTATIONS:
            return None
        return {"id": m["id"], "niveau": m["niveau"], "nom": MUTATIONS[m["id"]]["nom"], "texte": MUTATIONS[m["id"]]["texte"]}

    def _guerir(self, t: float, comment: str) -> None:
        s = self.s
        s["malade"], s["causes"], s["plancher_h"] = None, {}, 0.0
        s["stats"]["gueris"] += 1
        self._note(t, "guerison", "Philibert est guéri ! " + comment)
        self._succes("gueri", t)

    def _depart_veto(self, t: float) -> None:
        s = self.s
        causes = sorted(s["causes"].items(), key=lambda kv: -kv[1])
        raisons = [c for c, h in causes if h >= 1][:2] or [s["malade"]["cause"] if s["malade"] else "fatigue"]
        importantes = len([c for c, h in causes if h >= 3])
        duree = min(24 * H, 12 * H + 4 * H * importantes)
        s["veto"] = {"depart": t, "retour": t + duree, "raisons": raisons}
        s["position"], s["appel"], s["evenement"], s["jeu"] = "veto", None, None, None
        self._note(t, "veto", "La tortue vétérinaire est venue chercher Philibert en barque pour qu'il se repose.")
        self.journal("philibert", "départ chez le vétérinaire", "ok", ", ".join(raisons))
        if s["reglages"].get("discord"):
            self.notifier("🐢 Philibert se repose chez le vétérinaire", f"Retour dans environ {round(duree / H)} h. Il va bien, il se repose.")

    def _retour_veto(self, t: float) -> None:
        s, j = self.s, self.s["j"]
        v = s["veto"]
        for g, mini in {"faim": 70, "bonheur": 65, "energie": 80, "proprete": 90, "sante": 85, "chaleur": 75}.items():
            j[g] = max(j[g], mini)
        s["corpulence"] = 50 + (s["corpulence"] - 50) * .3
        s["uv"] = max(s["uv"], 70)
        s["crottes"], s["crottes_a_venir"], s["mue"], s["malade"], s["causes"], s["plancher_h"] = 0, [], None, None, {}, 0.0
        s["friandises_t"] = []
        cout = min(15, s["coquillages"])
        s["coquillages"] -= cout
        s["stats"]["sejours_veto"] += 1
        raisons = v["raisons"]
        texte = " ".join(RAISONS[r][0] for r in raisons if r in RAISONS)
        conseil = " ".join(RAISONS[r][1] for r in raisons if r in RAISONS)
        s["cartes"].append({"t": round(t), "texte": texte, "conseil": conseil, "raisons": raisons, "cout": cout,
                            "duree_h": round((v["retour"] - v["depart"]) / H), "lue": False})
        del s["cartes"][:-50]
        s["veto"], s["position"] = None, "plage"
        s["appel_pause"] = t + H
        self._note(t, "retour", "Philibert est rentré de chez la tortue vétérinaire, tout reposé. Elle a laissé une carte postale."
                   + (f" (consultation : {cout} coquillages)" if cout else " (consultation offerte)"))
        self._succes("comme_neuf", t)
        self.journal("philibert", "retour du vétérinaire", "ok", f"séjour n° {s['stats']['sejours_veto']}")
        if s["contact"] < v["depart"]:                 # personne n'est passé entre-temps : la voisine le garde
            self._pension(t, auto=True)

    def _pension(self, t: float, auto: bool) -> None:
        s = self.s
        s["vacances"] = {"depuis": t, "auto": auto}
        s["appel"], s["evenement"], s["jeu"], s["position"] = None, None, None, "pension"
        if auto:                                       # la voisine s'occupe bien de lui : il t'attend en forme
            j = s["j"]
            for g, mini in {"faim": 65, "bonheur": 60, "energie": 75, "proprete": 80, "sante": 70, "chaleur": 70}.items():
                j[g] = max(j[g], mini)
            s["crottes"], s["crottes_a_venir"], s["uv"] = 0, [], max(s["uv"], 60)
        self._note(t, "vacances", "La voisine de l'île a pris Philibert en pension en attendant ton retour." if auto
                   else "Philibert part en vacances chez la voisine de l'île (tout est en pause).")
        self.journal("philibert", "pension chez la voisine" if auto else "vacances activées", "ok", "")

    # -- lecture -------------------------------------------------------------------
    def _besoins(self, t: float) -> list[dict]:
        s, j = self.s, self.s["j"]
        out = []
        if s["stade"] == "oeuf" or s["veto"] or s["vacances"]:
            return out
        if s["malade"]:
            out.append({"id": "malade", "texte": f"Il est malade ({MALADIES[s['malade']['cause']]}) : un remède, du repos et de la chaleur."})
        if j["chaleur"] < 35:
            out.append({"id": "froid", "texte": "Il a froid : au soleil sur le rocher, ou sous la lampe chauffante."})
        if j["faim"] < 30:
            out.append({"id": "faim", "texte": "Il a faim : un repas de verdure."})
        if j["energie"] < 20:
            out.append({"id": "fatigue", "texte": "Il est fatigué : laisse-le se reposer."})
        if j["proprete"] < 30 or s["crottes"] >= 2:
            out.append({"id": "proprete", "texte": "Son coin est sale : nettoie, ou offre-lui un bain."})
        if j["bonheur"] <= SEUIL_ATTENTION:
            out.append({"id": "ennui", "texte": "Il s'ennuie : joue avec lui ou caresse-le."})
        if s["mue"]:
            out.append({"id": "mue", "texte": "Il mue : un bain tiède l'aiderait."})
        if s["uv"] < 25:
            out.append({"id": "soleil", "texte": "Il manque de soleil : un moment sur le rocher chaud."})
        if s["corpulence"] > 75:
            out.append({"id": "ventre", "texte": "Ventre tout rond : moins de fruits, plus de verdure."})
        if heure_de_dormir(t) and s["lumiere"] and s["eveil_nuit"] <= t:
            out.append({"id": "lumiere", "texte": "C'est la nuit : éteins la lumière pour qu'il dorme bien."})
        return out

    def titre(self) -> str:
        s = self.s
        if s["stade"] == "oeuf":
            return "L'œuf de Philibert"
        t = "Philibert " + VARIANTES[s["variante"]] if s["variante"] else "Philibert"
        return t + (", vieux sage" if s["stade"] == "sage" else "")

    def _poids(self) -> int:
        s = self.s
        jours = s["age_s"] / JOUR
        bornes = {"oeuf": (12, 12, 0, 1), "bebe": (15, 60, 0, 2), "juvenile": (60, 500, 2, 7), "adulte": (500, 3500, 7, 30),
                  "sage": (3500, 4200, 30, 90)}
        a, b, d0, d1 = bornes[s["stade"]]
        base = a + (b - a) * _borne((jours - d0) / (d1 - d0), 0, 1)
        return round(base * (.7 + s["corpulence"] / 100 * .6))

    def _vue(self, now: float) -> dict:
        s, j = self.s, self.s["j"]
        nuit = heure_de_dormir(now)
        eveille = s["eveil_nuit"] > now
        dort = s["stade"] != "oeuf" and not s["veto"] and not s["vacances"] and ((nuit and not eveille) or s["sieste"])
        besoins = self._besoins(now)
        grognon = s["grognon"] > now
        if s["veto"]:
            niveau = "veto"
        elif s["vacances"]:
            niveau = "pension"
        elif s["stade"] == "oeuf":
            niveau = "oeuf"
        elif s["malade"]:
            niveau = "malade"
        elif grognon or j["energie"] < 20 or any(b["id"] not in ("lumiere", "ventre") for b in besoins):
            niveau = "fatigue"
        else:
            niveau = "en_forme"
        if niveau in ("veto", "pension", "oeuf"):
            humeur = niveau
        elif dort:
            humeur = "dort"
        elif s["malade"]:
            humeur = "malade"
        elif grognon:
            humeur = "grognon"
        elif s["appel"] and (s["appel"]["type"] != "caprice" or j["bonheur"] <= SEUIL_ATTENTION):
            humeur = "appel"
        elif j["chaleur"] < 35:
            humeur = "froid"
        elif j["bonheur"] >= 75 and niveau == "en_forme":
            humeur = "joyeux"
        else:
            humeur = "calme"
        jeux = s["jeux_jour"]
        sa_now = saison(now, s["graine"])
        sp_now, _, sp_fin = periode_saison_ile(now, s["graine"]) if not SAISON_ILE_FORCEE else (saison_ile(now), 0, 0)
        a = s["appel"]
        if a and a["type"] == "caprice" and j["bonheur"] > SEUIL_ATTENTION:
            s["appel"] = a = None
        return {
            "nom": "Philibert", "titre": self.titre(), "stade": s["stade"], "stade_nom": STADES[s["stade"]], "variante": s["variante"],
            "age_jours": round(s["age_s"] / JOUR, 2), "ne": s["ne"], "eclos": s["eclos"],
            "jauges": {g: round(j[g]) for g in JAUGES}, "corpulence": round(s["corpulence"]), "poids_g": self._poids(),
            "ventre_rond": s["corpulence"] > 75, "discipline": round(s["discipline"]), "uv": round(s["uv"]),
            "niveau": niveau, "humeur": humeur, "besoins": besoins, "dort": dort, "sieste": s["sieste"] and not nuit, "grognon": grognon,
            "position": s["position"], "lumiere": s["lumiere"], "lampe": dict(s["lampe"]),
            "ciel": {"phase": phase_du_ciel(now), "meteo": meteo(now, s["graine"]), "heure": round(_heure(now), 2),
                     "saison": sa_now, "saison_nom": SAISONS[sa_now]["nom"], "saison_texte": SAISONS[sa_now]["texte"],
                     "saison_ile": ({"id": sp_now, "nom": SAISONS_ILE[sp_now]["nom"], "texte": SAISONS_ILE[sp_now]["texte"],
                                     "reste_s": max(0, round(sp_fin - now)) if not SAISON_ILE_FORCEE else None} if sp_now else None)},
            "promo": SAISONS[sa_now]["promo"],
            "promo_ile": SAISONS_ILE[sp_now]["promo"] if sp_now else None,
            "mutation": self._mutation_vue(),
            "crottes": s["crottes"], "mue": bool(s["mue"]),
            "malade": {"cause": s["malade"]["cause"], "texte": MALADIES[s["malade"]["cause"]], "depuis": s["malade"]["depuis"]} if s["malade"] else None,
            "veto": {"retour": s["veto"]["retour"], "reste_s": max(0, round(s["veto"]["retour"] - now)), "raisons": s["veto"]["raisons"],
                     "depart": s["veto"]["depart"]} if s["veto"] else None,
            "vacances": dict(s["vacances"]) if s["vacances"] else None,
            "appel": {"type": a["type"], "raison": a["raison"], "t": a["t"]} if a else None,
            "evenement": ({"id": s["evenement"]["id"], "texte": EVENEMENTS[s["evenement"]["id"]]["texte"],
                           "choix": EVENEMENTS[s["evenement"]["id"]]["choix"]} if s["evenement"] else None),
            "coquillages": s["coquillages"], "inventaire": {k: v for k, v in s["inventaire"].items() if v > 0},
            "accessoires": list(s["accessoires"]), "portes": dict(s["portes"]), "deco": list(s["deco"]),
            "reglages": dict(s["reglages"]),
            "ramasser_dans_s": max(0, round(s["ramasse"] + 3 * H - now)),
            "jeux_restants": GAINS_JEUX_JOUR - (jeux["gagnes"] if jeux["jour"] == _jour(now) else 0),
            "carte": next(({**c, "index": i} for i, c in enumerate(s["cartes"]) if not c["lue"]), None),
            "nouveau": [{**n, "nom": (SUCCES[n["id"]][0] if n["type"] == "succes" else None),
                         "texte": (FAITS[n["id"]] if n["type"] == "fait" else SUCCES[n["id"]][1])} for n in s["nouveau"]][-6:],
            "maintenant": now,
        }

    def etat(self) -> dict:
        now = maintenant()
        with self._lock:
            self._avancer(now)
            self._verifier_succes(now)
            self._sauver()
            return self._vue(now)

    def catalogue(self) -> dict:
        return {
            "aliments": ALIMENTS, "pieges": {k: v["nom"] for k, v in PIEGES.items()}, "objets": OBJETS,
            "succes": {k: {"nom": v[0], "texte": v[1], "gain": v[2]} for k, v in SUCCES.items()},
            "faits_total": len(FAITS), "variantes": VARIANTES, "raretes": RARETES,
            "mutations": {k: {"nom": v["nom"], "texte": v["texte"], "condition": v["condition"]} for k, v in MUTATIONS.items()},
            "saisons": {k: {"nom": v["nom"], "texte": v["texte"], "promo": v["promo"]} for k, v in SAISONS.items()},
            "saisons_ile": {k: {"nom": v["nom"], "texte": v["texte"], "promo": v["promo"]} for k, v in SAISONS_ILE.items()}, "stades": STADES, "jeux": JEUX,
        }

    def carnet(self) -> dict:
        now = maintenant()
        with self._lock:
            self._avancer(now)
            s = self.s
            return {
                "titre": self.titre(), "age_jours": round(s["age_s"] / JOUR, 2), "ne": s["ne"], "eclos": s["eclos"],
                "stade": s["stade"], "variante": s["variante"], "historique": list(reversed(s["carnet"])),
                "stats": dict(s["stats"]), "gouts": list(s["gouts"]),
                "succes": {k: {"nom": v[0], "texte": v[1], "gain": v[2], "quand": s["succes"].get(k)} for k, v in SUCCES.items()},
                "cartes": list(reversed(s["cartes"])),
                "faits": [{"id": f, "texte": FAITS[f]} for f in s["faits"]], "faits_total": len(FAITS),
                "etapes": list(s["etapes"]), "album": list(reversed(s["album"])), "saisons_vues": list(s["saisons_vues"]), "saisons_ile_vues": list(s.get("saisons_ile_vues") or []),
                "mutations_vues": list(s.get("mutations_vues") or []), "mutation": self._mutation_vue(),
            }

    # -- actions -------------------------------------------------------------------
    def action(self, nom: str, p: dict | None = None) -> dict:
        p = p or {}
        fn = getattr(self, "_a_" + str(nom), None)
        if not fn or not str(nom).isidentifier():
            raise PhilibertErreur("action inconnue")
        now = maintenant()
        with self._lock:
            self._avancer(now)
            libre = nom in ("reglages", "vacances", "recommencer", "vu", "carte_lue", "acheter", "porter", "retirer")
            if not libre:
                self._present(now)
            res = fn(now, p) or {}
            self.s["contact"] = max(self.s["contact"], now)
            self._verifier_succes(now)
            self._sauver(force=True)
            return {"ok": True, "message": res.get("message", ""), "reaction": res.get("reaction", ""),
                    **{k: v for k, v in res.items() if k not in ("message", "reaction")}, "etat": self._vue(now)}

    def _present(self, now: float) -> None:
        s = self.s
        if s["veto"]:
            raise PhilibertErreur("Philibert se repose chez la tortue vétérinaire : il revient bientôt.")
        if s["vacances"]:
            raise PhilibertErreur("Philibert est en pension chez la voisine : fais-le revenir d'abord.")
        if s["stade"] == "oeuf":
            raise PhilibertErreur("Ce n'est encore qu'un œuf, bien au chaud dans le sable. Patience !")

    def _reveiller(self, now: float) -> str:
        """Une action la nuit le réveille : il est grognon une heure."""
        s = self.s
        if heure_de_dormir(now) and s["eveil_nuit"] <= now:
            s["eveil_nuit"], s["grognon"] = now + 30 * 60, now + H
            s["stats"]["nuits_reveille"] = s["stats"].get("nuits_reveille", 0) + 1
            s["j"]["bonheur"] = _borne(s["j"]["bonheur"] - 8)
            s["position"] = "plage"
            return "Tu l'as réveillé en pleine nuit : il est un peu grognon. "
        if s["sieste"]:
            s["sieste"] = False
            return "Il sort de sa sieste. "
        return ""

    def _cooldown(self, cle: str, now: float, duree: float) -> bool:
        """True si l'effet est disponible (et le réarme)."""
        if now - self.s["cd"].get(cle, 0) < duree:
            return False
        self.s["cd"][cle] = now
        return True

    def _fin_appel(self, *raisons: str) -> None:
        a = self.s["appel"]
        if a and a["type"] == "besoin" and (not raisons or a["raison"] in raisons):
            self.s["appel"], self.s["appel_pause"] = None, maintenant() + 30 * 60

    def _a_nourrir(self, now: float, p: dict) -> dict:
        s, j = self.s, self.s["j"]
        aid = str(p.get("aliment") or "")
        if aid in PIEGES:
            e = s["evenement"]
            if not e or EVENEMENTS[e["id"]].get("aliment") != aid:
                raise PhilibertErreur("Ça ne se trouve pas sur l'île.")
            return self._refus(now, aid)
        a = ALIMENTS.get(aid)
        if not a:
            raise PhilibertErreur("Aliment inconnu.")
        if a["prix"] and s["inventaire"].get(aid, 0) < 1:
            raise PhilibertErreur(f"Plus de « {a['nom']} » : passe à la boutique (ou donne-lui du trèfle de l'île, gratuit).")
        pre = self._reveiller(now)
        if j["faim"] >= 95:
            return {"message": pre + "Il n'a plus faim : il détourne la tête.", "reaction": "repu"}
        if a["prix"]:
            s["inventaire"][aid] -= 1
        froid = j["chaleur"] < 35
        k = .6 if froid else 1
        j["faim"] = _borne(j["faim"] + a["faim"] * k)
        j["bonheur"] = _borne(j["bonheur"] + a["bonheur"])
        j["sante"] = _borne(j["sante"] + a["sante"], SANTE_MIN)
        s["corpulence"] = _borne(s["corpulence"] + a["corpulence"] * k, 10, 100)
        st = s["stats"]
        st["repas"] += 1
        s["regime"] = (s["regime"] + [aid])[-10:]
        msg = pre
        if aid in ORANGES:
            st["oranges"] = st.get("oranges", 0) + 1
        if a["cat"] in ("verdure", "legume"):
            st["verdure"] += 1
            if aid not in s["gouts"]:
                s["gouts"].append(aid)
            s["bonne"] = {"t": now, "quoi": "repas"}
            derniers = [x for x in s["regime"][-6:] if ALIMENTS[x]["cat"] in ("verdure", "legume")]
            if len(set(derniers)) >= 3:
                j["sante"] = _borne(j["sante"] + 3)
                msg += "Quelle belle variété de verdure ! "
            if st["verdure"] >= 5:
                self._fait("dents")
        elif a["cat"] == "fleur":
            st["fleurs"] += 1
        else:
            st["friandises"] += 1
            s["friandises_t"].append(now)
            self._fait("fruits")
            n24 = len([x for x in s["friandises_t"] if x > now - JOUR])
            if n24 >= 3:
                msg += "Attention, beaucoup de fruits aujourd'hui : son ventre s'arrondit. "
        if len(s["crottes_a_venir"]) < 3:
            s["crottes_a_venir"].append(now + 3 * H)
        self._fait("herbivore")
        self._succes("premier_repas", now)
        self._fin_appel("faim")
        if froid:
            msg += "Il a froid, il n'a pas très faim : réchauffe-le pour qu'il digère bien. "
        msg += {"verdure": "Miam, de la verdure !", "legume": "Il croque son légume avec appétit.",
                "fleur": "Il adore les fleurs !", "friandise": "Une friandise : il est ravi."}[a["cat"]]
        return {"message": msg.strip(), "reaction": "mange_" + a["cat"]}

    def _refus(self, now: float, aid: str) -> dict:
        s = self.s
        s["stats"]["refus"] += 1
        self._fait("refus")
        self._succes("refus", now)
        s["evenement"] = None
        s["coquillages"] += 2
        s["stats"]["coquillages_gagnes"] += 2
        self._note(now, "refus", f"Philibert a refusé : {PIEGES[aid]['nom'].lower()}.")
        return {"message": f"Philibert refuse ({PIEGES[aid]['nom'].lower()}) et fait la moue. Astuce : {PIEGES[aid]['astuce']} (+2 coquillages pour la leçon)",
                "reaction": "refus", "astuce": PIEGES[aid]["astuce"]}

    def _a_chauffer(self, now: float, p: dict) -> dict:
        s = self.s
        if s["sieste"] and not heure_de_dormir(now):           # il dort : on le pose sur le rocher sans le réveiller
            s["position"], s["rocher_depuis"] = "rocher", now
            s["stats"]["soleil"] += 1
            self._fin_appel("froid", "soleil")
            return {"message": "Tu le poses tout doucement sur le rocher chaud : il continue sa sieste en se réchauffant.", "reaction": "rocher"}
        if heure_de_dormir(now):
            if s["lampe"]["possede"]:
                s["lampe"]["allumee"] = True
                return {"message": "La nuit, pas de soleil : tu allumes la lampe chauffante près de son palmier.", "reaction": "lampe"}
            return {"message": "La nuit, le rocher refroidit. Une lampe chauffante (boutique) le garderait au chaud.", "reaction": "non"}
        pre = self._reveiller(now)
        s["position"], s["rocher_depuis"] = "rocher", now
        s["stats"]["soleil"] += 1
        self._fait("sang_froid")
        self._fin_appel("froid", "soleil")
        ciel = meteo(now, s["graine"])
        msg = {"soleil": "Il s'installe à plat ventre sur le rocher chaud et se dore au soleil.",
               "arc": "Il se dore au soleil sous l'arc-en-ciel.",
               "nuages": "Il s'installe sur le rocher. Avec les nuages, ça chauffe moins vite.",
               "pluie": "Il pleut : le rocher ne chauffe presque pas. La lampe chauffante serait mieux aujourd'hui."}[ciel]
        return {"message": pre + msg, "reaction": "rocher"}

    def _a_lampe(self, now: float, p: dict) -> dict:
        s = self.s
        if not s["lampe"]["possede"]:
            raise PhilibertErreur("Il n'y a pas encore de lampe chauffante : elle est à la boutique.")
        s["lampe"]["allumee"] = bool(p.get("on", not s["lampe"]["allumee"]))
        if s["lampe"]["allumee"]:
            self._fin_appel("froid")
        return {"message": "Lampe chauffante allumée : douce chaleur sans lumière." if s["lampe"]["allumee"] else "Lampe chauffante éteinte.",
                "reaction": "lampe"}

    def _a_lumiere(self, now: float, p: dict) -> dict:
        s = self.s
        on = bool(p.get("on", not s["lumiere"]))
        if on == s["lumiere"]:
            return {"message": "La lumière est déjà " + ("allumée." if on else "éteinte.")}
        if not heure_de_dormir(now):
            if not on:
                return {"message": "Il fait jour : pas besoin d'éteindre, le soleil éclaire l'île."}
        s["lumiere"] = on
        if not on:
            if s["nuit_eteinte"] != _jour(now - 7 * H):
                s["nuit_eteinte"] = _jour(now - 7 * H)
                s["stats"]["nuits_eteintes"] += 1
            self._fait("arbres")
            return {"message": "Lumière éteinte. Bonne nuit, Philibert, là-haut dans ton palmier.", "reaction": "dodo"}
        return {"message": "Lumière rallumée." + (" Il cligne des yeux, ébloui." if heure_de_dormir(now) else ""), "reaction": "lumiere"}

    def _a_bain(self, now: float, p: dict) -> dict:
        s, j = self.s, self.s["j"]
        lieu = "mer" if p.get("lieu") == "mer" else "flaque"
        if not self._cooldown("bain", now, 20 * 60):
            return {"message": "Il sort à peine de l'eau : laisse-le sécher un peu (20 min entre deux bains).", "reaction": "non"}
        pre = self._reveiller(now)
        s["stats"]["bains"] += 1
        msg = pre
        if lieu == "flaque":
            j["proprete"] = _borne(j["proprete"] + 35)
            if s["bain_sante_jour"] != _jour(now):
                s["bain_sante_jour"] = _jour(now)
                j["sante"] = _borne(j["sante"] + 2)
            msg += "Bain tiède dans la flaque : il ferme les yeux de plaisir."
        else:
            s["stats"]["bains_mer"] += 1
            j["proprete"] = _borne(j["proprete"] + 25)
            j["bonheur"] = _borne(j["bonheur"] + 10)
            j["energie"] = _borne(j["energie"] - 10)
            j["chaleur"] = _borne(j["chaleur"] - 15)
            s["corpulence"] = _borne(s["corpulence"] - 3, 10, 100)
            self._fait("nage")
            msg += "Il nage dans l'eau turquoise en ondulant de la queue ! (l'eau de mer le rafraîchit)"
        s["position"] = "plage"
        bientot = [c for c in s["crottes_a_venir"] if c <= now + 2 * H]
        if bientot:
            s["crottes_a_venir"] = [c for c in s["crottes_a_venir"] if c > now + 2 * H]
            self._fait("eau")
            msg += " Oups, il a fait sa crotte dans l'eau… on change l'eau, rien à ramasser !"
        if s["mue"]:
            self._fin_mue(now, bain=True)
            msg += " Le bain l'aide à finir sa mue."
        s["bonne"] = {"t": now, "quoi": "bain"}
        self._fin_appel("proprete", "mue")
        return {"message": msg, "reaction": "bain_" + lieu}

    def _a_nettoyer(self, now: float, p: dict) -> dict:
        s, j = self.s, self.s["j"]
        n = s["crottes"]
        s["crottes"] = 0
        j["proprete"] = _borne(j["proprete"] + (30 if n else 8))
        s["stats"]["nettoyages"] += 1
        self._fin_appel("proprete")
        return {"message": f"Tu ramasses {n} petite{'s' if n > 1 else ''} crotte{'s' if n > 1 else ''} et ratisses le sable." if n
                else "Tu ratisses le sable : tout est propre.", "reaction": "nettoyer"}

    def _a_soigner(self, now: float, p: dict) -> dict:
        s, j = self.s, self.s["j"]
        if not s["malade"]:
            return {"message": "Il n'est pas malade : garde le remède pour plus tard.", "reaction": "non"}
        if s["inventaire"].get("remede", 0) < 1:
            raise PhilibertErreur("Plus de remède : il y en a à la boutique (8 coquillages). Le repos au chaud aide aussi.")
        s["inventaire"]["remede"] -= 1
        s["stats"]["remedes"] += 1
        pre = self._reveiller(now) if not heure_de_dormir(now) else ""
        if j["chaleur"] >= 50:
            j["sante"] = _borne(j["sante"] + 25)
            if j["sante"] >= 45:
                self._guerir(now, "Le remède a bien agi.")
                self._fin_appel("malade")
                return {"message": pre + "Il avale le remède… et le voilà guéri ! Laisse-le au chaud se reposer.", "reaction": "gueri"}
            return {"message": pre + "Le remède agit. Encore un peu de repos au chaud.", "reaction": "soin"}
        j["sante"] = _borne(j["sante"] + 10)
        return {"message": pre + "Il a trop froid pour bien guérir : le remède agit à moitié. Réchauffe-le d'abord !", "reaction": "soin"}

    def _a_caresser(self, now: float, p: dict) -> dict:
        s = self.s
        pre = self._reveiller(now)
        s["stats"]["caresses"] += 1
        self._fait("fanon")
        if self._cooldown("caresse", now, 120):
            s["j"]["bonheur"] = _borne(s["j"]["bonheur"] + 4)
            self._fin_appel("ennui")
        return {"message": pre + "Il ferme à moitié les yeux et agite son fanon.", "reaction": "caresse"}

    def _a_feliciter(self, now: float, p: dict) -> dict:
        s = self.s
        s["stats"]["feliciter"] += 1
        b = s["bonne"]
        if not self._cooldown("feliciter", now, 300):
            return {"message": "Il est déjà tout fier !", "reaction": "fier"}
        if b and now - b["t"] <= 10 * 60:
            s["discipline"] = _borne(s["discipline"] + 4)
            s["j"]["bonheur"] = _borne(s["j"]["bonheur"] + 6)
            s["bonne"] = None
            return {"message": "Bravo Philibert ! Il hoche la tête, tout fier.", "reaction": "fier"}
        s["j"]["bonheur"] = _borne(s["j"]["bonheur"] + 3)
        return {"message": "Il aime qu'on lui parle gentiment.", "reaction": "fier"}

    def _a_gronder(self, now: float, p: dict) -> dict:
        s = self.s
        s["stats"]["gronder"] += 1
        a = s["appel"]
        if a and a["type"] == "caprice":
            s["discipline"] = _borne(s["discipline"] + 10)
            s["j"]["bonheur"] = _borne(s["j"]["bonheur"] - 2)
            s["appel"], s["appel_pause"] = None, now + H
            return {"message": "Il voulait juste qu'on s'occupe de lui. Il a compris et se calme.", "reaction": "calme"}
        if a and a["type"] == "besoin":
            s["j"]["bonheur"] = _borne(s["j"]["bonheur"] - 6)
            b = next((x for x in self._besoins(now) if x["id"] == a["raison"]), None)
            return {"message": "Il avait vraiment besoin de quelque chose. " + (b["texte"] if b else "Regarde ses jauges."), "reaction": "triste"}
        s["j"]["bonheur"] = _borne(s["j"]["bonheur"] - 4)
        return {"message": "Il ne voit pas ce qu'il a fait… il n'avait rien demandé.", "reaction": "triste"}

    def _a_ramasser(self, now: float, p: dict) -> dict:
        s = self.s
        if now - s["ramasse"] < 3 * H:
            m = math.ceil((s["ramasse"] + 3 * H - now) / 60)
            return {"message": f"Tu as déjà ramassé les coquillages de la plage. La mer en rapporte d'autres dans {m // 60} h {m % 60:02d}.", "reaction": "non"}
        s["ramasse"] = now
        n = 1 + int(_alea(s["graine"], "ramasser", int(now // 60)) * 3)
        s["coquillages"] += n
        s["stats"]["coquillages_gagnes"] += n
        return {"message": f"Tu trouves {n} coquillage{'s' if n > 1 else ''} sur la plage.", "reaction": "coquillage", "gain": n}

    def _a_acheter(self, now: float, p: dict) -> dict:
        s = self.s
        art = str(p.get("article") or "")
        try:
            qte = max(1, min(10, int(p.get("quantite") or 1)))
        except (TypeError, ValueError):
            qte = 1
        if art in ALIMENTS:
            prix, nom = ALIMENTS[art]["prix"], ALIMENTS[art]["nom"]
            sp = saison_ile(now, s["graine"])
            if prix and (art == SAISONS[saison(now, s["graine"])]["promo"] or (sp and art == SAISONS_ILE[sp]["promo"])):
                prix = max(1, prix - 1)                        # de saison : un coquillage de moins
            if not prix:
                raise PhilibertErreur("Le trèfle pousse sur l'île : il est gratuit.")
        elif art in OBJETS:
            o = OBJETS[art]
            prix, nom = o["prix"], o["nom"]
            if o.get("unique"):
                qte = 1
                possede = (s["lampe"]["possede"] if art == "lampe" else art in s["accessoires"] or art in s["deco"])
                if possede:
                    raise PhilibertErreur(f"Tu as déjà « {nom} ».")
        else:
            raise PhilibertErreur("Cet article n'existe pas à la boutique.")
        total = prix * qte
        if s["coquillages"] < total:
            raise PhilibertErreur(f"Il te faut {total} coquillages (tu en as {s['coquillages']}). Joue avec Philibert ou ramasse-en sur la plage !")
        s["coquillages"] -= total
        if art in ALIMENTS or art == "remede":
            s["inventaire"][art] = s["inventaire"].get(art, 0) + qte
        elif art == "lampe":
            s["lampe"] = {"possede": True, "allumee": True}
        elif OBJETS[art]["type"] == "accessoire":
            s["accessoires"].append(art)
        else:
            s["deco"].append(art)
        return {"message": f"Acheté : {nom}" + (f" ×{qte}" if qte > 1 else "") + f" (−{total} coquillages).", "reaction": "achat"}

    def _a_porter(self, now: float, p: dict) -> dict:
        s = self.s
        art = str(p.get("article") or "")
        if art not in s["accessoires"]:
            raise PhilibertErreur("Cet accessoire n'est pas dans sa garde-robe.")
        s["portes"][OBJETS[art]["emplacement"]] = art
        return {"message": f"Il porte maintenant : {OBJETS[art]['nom'].lower()}.", "reaction": "fier"}

    def _a_retirer(self, now: float, p: dict) -> dict:
        slot = str(p.get("emplacement") or "")
        if slot not in EMPLACEMENTS:
            raise PhilibertErreur("Emplacement inconnu.")
        self.s["portes"].pop(slot, None)
        return {"message": "Accessoire retiré."}

    def _a_evenement(self, now: float, p: dict) -> dict:
        s = self.s
        e = s["evenement"]
        if not e:
            raise PhilibertErreur("Il ne se passe rien de spécial sur l'île en ce moment.")
        d = EVENEMENTS[e["id"]]
        choix = str(p.get("choix") or "")
        if choix not in d["choix"]:
            raise PhilibertErreur("Choix inconnu.")
        if choix == "proposer":
            return self._refus(now, d["aliment"])
        s["evenement"] = None
        if choix == "jeter":
            s["coquillages"] += 3
            s["stats"]["coquillages_gagnes"] += 3
            return {"message": "Bien vu : ce n'est pas pour lui. La plage est propre (+3 coquillages).", "reaction": "coquillage"}
        if choix == "ramasser":
            s["coquillages"] += 4
            s["stats"]["coquillages_gagnes"] += 4
            return {"message": "Tu trouves 4 coquillages sous la noix de coco !", "reaction": "coquillage"}
        if choix == "lire":
            restants = [f for f in FAITS if f not in s["faits"]] or list(FAITS)
            f = restants[int(_alea(s["graine"], "bouteille", int(now)) * len(restants))]
            self._fait(f)
            if f == "queue":
                pass
            return {"message": "Le message dit : « Le savais-tu ? " + FAITS[f] + " »", "reaction": "lire"}
        s["j"]["bonheur"] = _borne(s["j"]["bonheur"] + 8)
        return {"message": "Philibert et le crabe se courent après sur le sable. Il est ravi !", "reaction": "joue"}

    def _a_carte_lue(self, now: float, p: dict) -> dict:
        for c in self.s["cartes"]:
            c["lue"] = True
        return {}

    def _a_vu(self, now: float, p: dict) -> dict:
        self.s["nouveau"] = []
        return {}

    def _a_vacances(self, now: float, p: dict) -> dict:
        s = self.s
        on = bool(p.get("on"))
        if s["veto"]:
            raise PhilibertErreur("Il se repose chez le vétérinaire : il rentrera tout seul.")
        if on and not s["vacances"]:
            if s["stade"] == "oeuf":
                raise PhilibertErreur("L'œuf reste au chaud dans le sable.")
            self._pension(now, auto=False)
            return {"message": "Philibert part en pension chez la voisine. Tout est en pause jusqu'à son retour.", "reaction": "vacances"}
        if not on and s["vacances"]:
            jours = (now - s["vacances"]["depuis"]) / JOUR
            s["vacances"], s["position"], s["maj"] = None, "plage", now
            s["appel_pause"] = now + H
            s["prochain_evenement"] = max(s["prochain_evenement"], now + 2 * H)
            self._note(now, "vacances", "Philibert est rentré de chez la voisine, content de te revoir.")
            self.journal("philibert", "retour de pension", "ok", f"{jours:.1f} j")
            return {"message": "Philibert est de retour ! Il hoche la tête pour te dire bonjour.", "reaction": "bonjour"}
        return {"message": ""}

    def _a_reglages(self, now: float, p: dict) -> dict:
        r = self.s["reglages"]
        for k in ("visible", "sons", "ambiance", "notif_windows", "discord"):
            if k in p:
                r[k] = bool(p[k])
        if p.get("vitesse") in ("normale", "lente"):
            r["vitesse"] = p["vitesse"]
        if p.get("theme") in ("auto", "clair", "sombre"):            # couleurs de l'interface de l'île
            r["theme"] = p["theme"]
        return {"message": "Réglages enregistrés."}

    def _a_recommencer(self, now: float, p: dict) -> dict:
        if p.get("confirmer") != "NOUVEL OEUF":
            raise PhilibertErreur("Confirmation manquante.")
        ancien = self.titre()
        reglages = dict(self.s["reglages"])
        o = self.s
        album = list(o.get("album") or [])
        if o["stade"] != "oeuf":                     # un œuf qui n'a pas éclos n'entre pas dans l'album
            album.append({"titre": ancien, "stade": o["stade"], "variante": o["variante"], "portes": dict(o["portes"]),
                          "mutation": dict(o["mutation"]) if o.get("mutation") else None,
                          "ne": round(o["ne"]), "eclos": o["eclos"] and round(o["eclos"]), "fin": round(now),
                          "age_jours": round(o["age_s"] / JOUR, 1), "succes": len(o["succes"]), "faits": len(o["faits"]),
                          "repas": o["stats"]["repas"], "jeux": o["stats"]["jeux"], "mues": o["stats"]["mues"],
                          "sejours_veto": o["stats"]["sejours_veto"], "coquillages_gagnes": o["stats"]["coquillages_gagnes"]})
        self.s = self._nouveau(now, reglages, album[-30:])
        self._note(now, "naissance", f"Nouveau départ : {ancien} est parti vivre sur une île voisine, et un nouvel œuf est apparu dans le sable.")
        self.journal("philibert", "nouvel œuf", "ok", f"après {ancien}")
        return {"message": "Un nouvel œuf est apparu dans le sable chaud.", "reaction": "oeuf"}

    # -- mini-jeux -----------------------------------------------------------------
    def jeu_debut(self, jeu: str) -> dict:
        now = maintenant()
        with self._lock:
            self._avancer(now)
            self._present(now)
            s, j = self.s, self.s["j"]
            if jeu not in JEUX:
                raise PhilibertErreur("Jeu inconnu.")
            if heure_de_dormir(now) and s["eveil_nuit"] <= now:
                raise PhilibertErreur("Il dort : on jouera demain matin.")
            if s["malade"]:
                raise PhilibertErreur("Il est malade : il a besoin de repos et de chaleur, pas de jeux.")
            if j["energie"] < 15:
                raise PhilibertErreur("Il est trop fatigué pour jouer : laisse-le se reposer.")
            j["energie"] = _borne(j["energie"] - ENERGIE_JEU)            # pris au départ : perdu si on abandonne
            jeton = secrets.token_urlsafe(12)
            s["jeu"] = {"jeton": jeton, "jeu": jeu, "debut": now, "score": 0, "manche": 0, "fini": False, "graine": secrets.randbelow(2 ** 31)}
            out = {"jeton": jeton, "jeu": jeu, "graine": s["jeu"]["graine"], "compte": JEU_COMPTE}
            if jeu == "feuilles":
                out.update(duree=FEUILLES["duree_max"], regles=FEUILLES)
            elif jeu == "course":
                out.update(duree=COURSE["duree_max"], regles=COURSE)
            elif jeu == "devin":
                out.update(manches=DEVIN["manches"], erreurs=DEVIN["erreurs"], **self._devin_manche(s["jeu"], now))
            else:
                s["jeu"].update(suite=_suite_hochements(3), montre=now, tempo=tempo_rythme(0))
                out.update(suite=list(s["jeu"]["suite"]), tempo=s["jeu"]["tempo"], palier=1, max=RYTHME_MAX)
            self._fait("hochement" if jeu == "rythme" else "oeil" if jeu == "devin" else "herbivore")
            s["contact"] = now
            self._sauver(force=True)
            return out

    @staticmethod
    def _devin_manche(g: dict, now: float) -> dict:
        """Tire le côté de la manche suivante (avant le choix) et l'indice : un coup d'œil de Philibert, vrai le plus
        souvent, de plus en plus bref et un peu moins fiable à chaque palier."""
        p = devin_palier(g["manche"] + 1)
        cote = secrets.choice(("gauche", "droite"))
        vrai = secrets.randbelow(1000) < DEVIN["fiabilite"][p - 1] * 1000
        g.update(cote=cote, montre=now)
        return {"palier": p, "indice": cote if vrai else ("droite" if cote == "gauche" else "gauche"), "indice_ms": DEVIN["indice_ms"][p - 1]}

    def _jeu_courant(self, jeton: str, now: float) -> dict:
        g = self.s["jeu"]
        if not g or not secrets.compare_digest(str(jeton or ""), g["jeton"]):
            raise PhilibertErreur("Cette partie n'existe plus : recommence une partie.")
        if now - g["debut"] > 10 * 60:
            self.s["jeu"] = None
            raise PhilibertErreur("Partie trop ancienne : recommence une partie.")
        return g

    def jeu_coup(self, jeton: str, choix=None, reponse=None) -> dict:
        now = maintenant()
        with self._lock:
            g = self._jeu_courant(jeton, now)
            if g["fini"]:
                return {"fini": True, "score": g["score"]}
            if g["jeu"] == "devin":
                if choix not in ("gauche", "droite"):
                    raise PhilibertErreur("Choisis gauche ou droite.")
                if now - g.get("montre", 0) < .25:
                    raise PhilibertErreur("Trop rapide : regarde d'abord Philibert.")
                cote = g.get("cote") or secrets.choice(("gauche", "droite"))
                g["manche"] += 1
                bon = cote == choix
                g["score"] += bon
                g["erreurs"] = g.get("erreurs", 0) + (not bon)
                g["fini"] = g["manche"] >= DEVIN["manches"] or g["erreurs"] >= DEVIN["erreurs"]
                out = {"cote": cote, "bon": bon, "manche": g["manche"], "score": g["score"], "erreurs": g["erreurs"],
                       "palier": devin_palier(g["manche"]), "fini": g["fini"]}
                if not g["fini"]:
                    out["suivante"] = self._devin_manche(g, now)
                return out
            if g["jeu"] == "rythme":
                if not isinstance(reponse, list) or len(reponse) > RYTHME_MAX + 2:
                    raise PhilibertErreur("Réponse invalide.")
                if now - g["montre"] < .8 * _duree_suite(g["suite"], g.get("tempo", .78)):   # pas avant d'avoir vu la suite
                    raise PhilibertErreur("Trop rapide : regarde d'abord Philibert hocher la tête.")
                if [str(x) for x in reponse] == g["suite"]:
                    g["score"] = len(g["suite"])
                    g["manche"] += 1
                    if len(g["suite"]) >= RYTHME_MAX:
                        g["fini"] = True
                        return {"bon": True, "score": g["score"], "fini": True}
                    g.update(suite=_suite_hochements(len(g["suite"]) + 1), montre=now, tempo=tempo_rythme(g["manche"]))
                    return {"bon": True, "score": g["score"], "suite": list(g["suite"]), "tempo": g["tempo"], "palier": g["manche"] + 1, "fini": False}
                g["fini"] = True
                return {"bon": False, "score": g["score"], "attendu": list(g["suite"]), "fini": True}
            raise PhilibertErreur("Ce jeu ne se joue pas coup par coup.")

    def _refuser(self, msg: str):
        """Score impossible : la partie est close (jeton consommé), rien n'est gagné."""
        self.s["jeu"] = None
        self.s["stats"]["refus_jeux"] = self.s["stats"].get("refus_jeux", 0) + 1
        self._sauver(force=True)
        raise PhilibertErreur(msg)

    def jeu_fin(self, jeton: str, score=None, insectes=None, arrivee=None, palier=None, distance=None) -> dict:
        now = maintenant()
        with self._lock:
            self._avancer(now)
            g = self._jeu_courant(jeton, now)
            s, j = self.s, self.s["j"]
            duree = now - g["debut"]                      # durée réelle (compte à rebours compris)
            jeu_t = max(0.0, duree - JEU_COMPTE)          # temps de jeu au plus
            try:
                sc = int(score or 0)
                ins = int(insectes or 0)
                pc = int(palier or 1)
                dist = float(distance or 0)
            except (TypeError, ValueError):
                self._refuser("Partie refusée : résultat illisible.")
            if sc < 0 or ins < 0 or pc < 1 or dist < 0:
                self._refuser("Partie refusée : résultat impossible.")
            if g["jeu"] in ("feuilles", "course") and duree < JEU_DUREE_MIN:
                self._refuser("Partie trop courte : elle n'est pas comptée.")
            if g["jeu"] == "course":
                vmax = sum(COURSE["vitesse"]) * course_vitesse(COURSE["etapes"])
                if dist > vmax * min(jeu_t, COURSE["duree_max"]) * 1.05 + 100:
                    self._refuser("Partie refusée : distance impossible pour la durée de la course.")
                arrive = bool(arrivee)
                but = COURSE["etape_px"] * COURSE["etapes"]
                if arrive and dist < but:
                    self._refuser("Partie refusée : le rocher chaud n'était pas encore atteint.")
                if sc > dist / COURSE["rayon_min"] + 2:
                    self._refuser("Partie refusée : plus de rayons de soleil qu'il n'y en avait sur le parcours.")
                pal = course_etape(dist)
                if pc > pal:
                    self._refuser("Partie refusée : étape impossible pour la distance parcourue.")
                gain, bonheur = recompense_jeu("course", sc, pal, arrive)
                s["stats"]["meilleur_course"] = max(s["stats"]["meilleur_course"], sc if arrive else 0)
                s["stats"]["etape_course"] = max(s["stats"].get("etape_course", 0), pal)
                if arrive:
                    s["stats"]["courses_gagnees"] += 1
                    j["chaleur"] = _borne(j["chaleur"] + 10)
                    if not heure_de_dormir(now):
                        s["position"], s["rocher_depuis"] = "rocher", now
                    if sc >= 60:
                        self._succes("coureur", now)
                self._fait("sang_froid")
                txt = f"étape {pal}, {sc} rayon{'s' if sc > 1 else ''} de soleil" + (", arrivé sur le rocher chaud" if arrive else "")
            elif g["jeu"] == "feuilles":
                t = min(jeu_t, FEUILLES["duree_max"])
                pal = feuilles_palier(t + 1)
                objets = feuilles_objets_max(t + 1)
                if pc > pal:
                    self._refuser("Partie refusée : palier impossible pour la durée de la partie.")
                if sc > 1.3 * objets + 4 or ins > objets + 2:
                    self._refuser("Partie refusée : score impossible pour la durée de la partie.")
                pal = pc
                gain, bonheur = recompense_jeu("feuilles", sc, pal)
                s["stats"]["meilleur_feuilles"] = max(s["stats"]["meilleur_feuilles"], sc)
                s["stats"]["palier_feuilles"] = max(s["stats"].get("palier_feuilles", 0), pal)
                if ins:
                    self._fait("refus")
                txt = f"palier {pal}, {sc} point{'s' if sc > 1 else ''}"
            elif g["jeu"] == "devin":
                sc, pal = g["score"], devin_palier(max(1, g["manche"]))
                gain, bonheur = recompense_jeu("devin", sc, pal)
                s["stats"]["meilleur_devin"] = max(s["stats"]["meilleur_devin"], sc)
                txt = f"{sc} bonne{'s' if sc > 1 else ''} réponse{'s' if sc > 1 else ''} sur {max(g['manche'], 1)}, palier {pal}"
            else:
                sc, pal = g["score"], min(g["manche"] + 1, RYTHME_MAX - 2)   # palier = manche jouée (12 au plus)
                gain, bonheur = recompense_jeu("rythme", sc, pal)
                s["stats"]["meilleur_rythme"] = max(s["stats"]["meilleur_rythme"], sc)
                txt = f"palier {pal}, suite de {sc} gestes"
            if j["chaleur"] >= 70:
                gain = round(gain * 1.25)
            jj = s["jeux_jour"]
            if jj["jour"] != _jour(now):
                jj.update(jour=_jour(now), gagnes=0)
            gain = max(0, min(gain, GAINS_JEUX_JOUR - jj["gagnes"]))
            jj["gagnes"] += gain
            s["coquillages"] += gain
            s["stats"]["coquillages_gagnes"] += gain
            s["stats"]["jeux"] += 1
            j["bonheur"] = _borne(j["bonheur"] + bonheur)
            s["corpulence"] = _borne(s["corpulence"] - 2, 10, 100)
            s["jeu"], s["contact"] = None, now
            self._fin_appel("ennui")
            self._verifier_succes(now)
            self._sauver(force=True)
            plafond = jj["gagnes"] >= GAINS_JEUX_JOUR
            return {"ok": True, "score": sc, "palier": pal, "gain": gain, "bonheur": bonheur, "duree_s": round(duree),
                    "message": f"{JEUX[g['jeu']]} : {txt} ! +{gain} coquillage{'s' if gain > 1 else ''}, bonheur +{bonheur}."
                    + (" (Plafond de coquillages des jeux atteint pour aujourd'hui.)" if plafond else ""),
                    "etat": self._vue(now)}

    def jeu_annuler(self, jeton: str) -> dict:
        """Abandonner la partie en cours : ni coquillages ni bonheur, et l'énergie prise au départ ne revient pas."""
        now = maintenant()
        with self._lock:
            self._avancer(now)
            g = self.s["jeu"]
            if not g or not secrets.compare_digest(str(jeton or ""), g["jeton"]):
                raise PhilibertErreur("Il n'y a pas de partie en cours.")
            self.s["jeu"] = None
            self.s["stats"]["abandons"] = self.s["stats"].get("abandons", 0) + 1
            self._sauver(force=True)
            return {"ok": True, "message": f"Partie abandonnée. L'énergie dépensée pour la lancer (−{ENERGIE_JEU}) ne revient pas.",
                    "etat": self._vue(now)}

    # -- outils de test --------------------------------------------------------------
    def instantane(self) -> dict:
        with self._lock:
            return copy.deepcopy(self.s)
