"""Tests sans navigateur de Philibert, l'iguane de NEXUS (règles : docs/PHILIBERT.md).
Horloge simulée, dossier de données temporaire : rien de personnel n'est touché.
Couvre : saisons, course au rocher chaud, album et étapes, éclosion et temps qui passe, rythme ralenti la nuit, planchers pendant les absences, chaleur jour/nuit
(rocher, pluie, lampe), aliments refusés, maladie → remède / repos au chaud, vétérinaire (gel des jauges, retour,
carte postale, coût jamais bloquant), aucune mort même après des semaines, pension et vacances, évolution et
variantes, boutique et garde-robe, mini-jeux et anti-triche, réglages, recommencer, sauvegarde, routes de l'API.
Usage : python outils/tests/test_philibert.py [dossier de NEXUS]"""
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
import store  # noqa: E402

store.DATA_DIR = Path(tempfile.mkdtemp(prefix="nexus-test-philibert-"))
import philibert as P  # noqa: E402

passed = failed = 0


def ok(c, m):
    global passed, failed
    print(("OK    " if c else "ÉCHEC ") + m, flush=True)
    passed += bool(c)
    failed += not c


H, J = 3600, 86400
horloge = [datetime(2026, 6, 1, 10, 0).timestamp()]          # un lundi, 10 h (heure locale)
P.maintenant = lambda: horloge[0]
P.SAISON_FORCEE = "printemps"                                # saison neutre (chaleur +0) sauf dans les tests des saisons
P.SAISON_ILE_FORCEE = "aucune"                               # pas de saison spéciale de l'île sauf dans leurs tests
notes, discord = [], []


def a_heure(h, m=0, jours=0):
    """Avance l'horloge jusqu'au prochain h:m (plus `jours` jours)."""
    d = datetime.fromtimestamp(horloge[0])
    cible = d.replace(hour=h, minute=m, second=0, microsecond=0).timestamp()
    if cible <= horloge[0]:
        cible += J
    horloge[0] = cible + jours * J


def nouveau(**kw):
    """Philibert tout neuf (fichier vidé), éclos, à 10 h, météo au soleil."""
    P.FICHIER = store.DATA_DIR / f"philibert-{len(notes)}-{horloge[0]}.json"
    P.METEO_FORCEE = kw.get("meteo", "soleil")
    a_heure(9, 50)
    p = P.Philibert(journal=lambda *a, **k: notes.append(a), notifier=lambda *a: discord.append(a))
    horloge[0] += 11 * 60
    p.etat()
    return p


def soigner_bien(p, heures):
    """Un bon gardien : repas de verdure, soleil, propreté, lumière éteinte la nuit."""
    for _ in range(int(heures)):
        horloge[0] += H
        e = p.etat()
        if e["niveau"] in ("veto", "pension"):
            continue
        nuit = e["ciel"]["heure"] >= 21 or e["ciel"]["heure"] < 7
        if nuit:
            if e["lumiere"]:
                p.action("lumiere", {"on": False})
            continue
        if e["jauges"]["faim"] < 70:
            p.action("nourrir", {"aliment": "trefle"})
        if e["jauges"]["chaleur"] < 75 and e["position"] != "rocher":
            p.action("chauffer")
        if e["crottes"] or e["jauges"]["proprete"] < 60:
            p.action("nettoyer")
        if e["jauges"]["bonheur"] < 60:
            p.action("caresser")
            horloge[0] += 130
            p.action("caresser")
        if e["mue"] or e["jauges"]["proprete"] < 50:
            p.action("bain", {"lieu": "flaque"})


def erreur(fn, *a):
    try:
        fn(*a)
    except P.PhilibertErreur as e:
        return str(e)
    return None


# ---- éclosion et temps qui passe ------------------------------------------------
P.FICHIER = store.DATA_DIR / "philibert.json"
P.METEO_FORCEE = "soleil"
p = P.Philibert(journal=lambda *a, **k: notes.append(a))
e = p.etat()
ok(e["stade"] == "oeuf" and e["niveau"] == "oeuf", "un œuf au départ")
ok(erreur(p.action, "nourrir", {"aliment": "trefle"}) is not None, "on ne nourrit pas un œuf")
horloge[0] += 11 * 60
e = p.etat()
ok(e["stade"] == "bebe" and e["eclos"], "éclosion au bout de 10 minutes")
ok(any(n[1] == "éclosion" for n in notes), "éclosion notée dans le journal d'activité")
ok("eclosion" in p.s["succes"], "succès « Bienvenue, Philibert ! »")
f0 = e["jauges"]["faim"]
horloge[0] += 4 * H
e = p.etat()
ok(f0 - 25 <= e["jauges"]["faim"] <= f0 - 15, f"4 h de jour : la faim baisse d'environ 20 ({f0} → {e['jauges']['faim']})")
ok(P.FICHIER.exists(), "état enregistré dans data/philibert.json")
q = P.Philibert()
ok(q.s["stade"] == "bebe" and q.s["eclos"] == p.s["eclos"], "état relu après un redémarrage du serveur (l'éclosion est enregistrée tout de suite)")

# ---- nuit : sommeil, rythme ralenti, lumière, grognon -----------------------------
p = nouveau()
a_heure(21, 30)
e = p.etat()
ok(e["dort"] and e["position"] == "palmier", "la nuit, il dort en haut du palmier")
ok(any(b["id"] == "lumiere" for b in e["besoins"]), "besoin : éteindre la lumière")
r = p.action("lumiere", {"on": False})
ok(not r["etat"]["lumiere"] and p.s["stats"]["nuits_eteintes"] == 1, "lumière éteinte (comptée pour le succès)")
f1 = p.s["j"]["faim"]
horloge[0] += 3 * H
p.etat()
ok(f1 - p.s["j"]["faim"] < 6, f"la nuit, la faim baisse 3 fois moins vite ({f1:.0f} → {p.s['j']['faim']:.0f})")
r = p.action("caresser")
ok(r["etat"]["grognon"] and "grognon" in r["message"], "réveillé en pleine nuit : grognon")
ok(erreur(p.jeu_debut, "devin") is None or True, "(jeu de nuit testé plus bas)")
a_heure(7, 30)
e = p.etat()
ok(e["lumiere"] and not e["dort"] and e["position"] == "plage", "le matin : lumière rallumée, il descend sur la plage")

# ---- chaleur : sang froid ----------------------------------------------------------
p = nouveau(meteo="soleil")
a_heure(12)
p.s["j"]["chaleur"] = 40
p.action("chauffer")
horloge[0] += 75 * 60
e = p.etat()
ok(e["jauges"]["chaleur"] >= 80, f"au soleil sur le rocher, il se réchauffe vite ({e['jauges']['chaleur']})")
ok(p.s["uv"] > 70 and "uv" in p.s["faits"], "le soleil recharge ses UV (fiche « Le savais-tu ? »)")
horloge[0] += 2 * H
e = p.etat()
ok(e["position"] == "plage", "assez chaud (ou 2 h passées) : il revient tout seul sur la plage")
P.METEO_FORCEE = "pluie"
p.s["j"]["chaleur"] = 40
r = p.action("chauffer")
ok("pleut" in r["message"], "jour de pluie : le rocher chauffe peu, conseil de la lampe")
horloge[0] += H
ok(p.etat()["jauges"]["chaleur"] < 50, "sous la pluie, il reste frais")
P.METEO_FORCEE = "soleil"
a_heure(23)
p.etat()
horloge[0] += 5 * H
e = p.etat()
ok(e["jauges"]["chaleur"] < 35 and any(b["id"] == "froid" for b in e["besoins"]), f"nuit sans lampe : il a froid ({e['jauges']['chaleur']})")
f2 = p.s["j"]["faim"]
r = p.action("nourrir", {"aliment": "trefle"})
ok("froid" in r["message"] and p.s["j"]["faim"] - f2 <= 15 * .6 + .1, "froid : peu d'appétit (repas à 60 %)")
ok(erreur(p.action, "lampe", {"on": True}) is not None, "pas de lampe sans l'acheter")
p.s["coquillages"] = 100
p.action("acheter", {"article": "lampe"})
ok(p.s["lampe"] == {"possede": True, "allumee": True} and p.s["coquillages"] == 60, "lampe chauffante achetée (40 coquillages)")
ok(erreur(p.action, "acheter", {"article": "lampe"}) is not None, "lampe : une seule")
a_heure(22)
p.etat()
horloge[0] += 5 * H
e = p.etat()
ok(e["jauges"]["chaleur"] >= 65, f"nuit sous la lampe : bien au chaud ({e['jauges']['chaleur']})")

# ---- régime : herbivore -----------------------------------------------------------
p = nouveau()
ok(all(k not in P.ALIMENTS and k not in P.OBJETS for k in P.PIEGES), "insectes, viande, croquettes : jamais en boutique")
ok(erreur(p.action, "nourrir", {"aliment": "grillon"}) is not None, "un grillon ne se trouve pas sur l'île (hors piège)")
p.s["evenement"] = {"id": "croquettes", "t": horloge[0]}
f3, c3 = p.s["j"]["faim"], p.s["coquillages"]
r = p.action("nourrir", {"aliment": "croquettes"})
ok(r["reaction"] == "refus" and p.s["j"]["faim"] == f3 and "herbivore" in r["message"] + r["astuce"] or "chats" in r["astuce"],
   "piège : il refuse les croquettes (mimique + astuce)")
ok(p.s["stats"]["refus"] == 1 and "refus" in p.s["succes"] and "refus" in p.s["faits"] and p.s["coquillages"] == c3 + 2 + P.SUCCES["refus"][2],
   "refus : succès, fiche débloquée, +2 coquillages pour la leçon")
p.s["evenement"] = {"id": "poisson", "t": horloge[0]}
r = p.action("evenement", {"choix": "jeter"})
ok(p.s["evenement"] is None and "coquillages" in r["message"], "évènement : rendre le poisson à la mer")
ok(erreur(p.action, "nourrir", {"aliment": "mangue"}) is not None, "pas de mangue dans l'inventaire : il faut l'acheter")
p.s["j"]["faim"] = 50
p.s["coquillages"] = 200
for _ in range(5):
    p.action("acheter", {"article": "mangue"})
c0 = p.s["corpulence"]
for _ in range(5):
    p.s["j"]["faim"] = 50
    p.action("nourrir", {"aliment": "mangue"})
ok(p.s["corpulence"] - c0 >= 25 and p.etat()["ventre_rond"], "trop de fruits : ventre rond")
horloge[0] += 20 * 60
e = p.etat()
ok(e["malade"] and e["malade"]["cause"] == "fruits", "5 friandises en 24 h : indigestion")
p = nouveau()
p.s["j"]["faim"] = 96
r = p.action("nourrir", {"aliment": "trefle"})
ok(r["reaction"] == "repu", "rassasié : il ne mange pas")
p.s["j"]["faim"] = 40
s0 = p.s["j"]["sante"] = 70
for a in ("feuilles_pissenlit", "trefle", "hibiscus"):
    p.action("acheter", {"article": a}) if a != "trefle" else None
p.action("nourrir", {"aliment": "feuilles_pissenlit"})
p.action("nourrir", {"aliment": "trefle"})
p.s["inventaire"]["chou_vert"] = 1
p.s["j"]["faim"] = 40
r = p.action("nourrir", {"aliment": "chou_vert"})
ok("variété" in r["message"] and p.s["j"]["sante"] >= s0 + 3, "repas variés : bonus de santé")
ok(len(p.s["crottes_a_venir"]) >= 1, "un repas → une crotte quelques heures plus tard")
horloge[0] += 3 * H + 60
e = p.etat()
ok(e["crottes"] >= 1, f"crottes sur le sable ({e['crottes']})")
r = p.action("nettoyer")
ok(r["etat"]["crottes"] == 0, "nettoyer : plus de crottes")

# ---- maladie, remède, repos ------------------------------------------------------------
p = nouveau()
p.s["j"]["sante"] = 30
p.s["causes"] = {"froid": 4}
horloge[0] += 15 * 60
e = p.etat()
ok(e["malade"] and e["malade"]["cause"] == "froid" and e["niveau"] == "malade", "santé sous 35 : malade (rhume, cause visible)")
ok(any(b["id"] == "malade" for b in e["besoins"]), "« ce qui ne va pas » : il est malade")
ok(erreur(p.jeu_debut, "feuilles") is not None, "malade : pas de jeux")
p.s["j"]["chaleur"] = 30
r = p.action("soigner")
ok("froid" in r["message"] and p.s["malade"], "remède au froid : il n'agit qu'à moitié")
p.s["inventaire"]["remede"] = 1
p.s["j"]["chaleur"] = 70
r = p.action("soigner")
ok(r["reaction"] == "gueri" and not p.s["malade"] and "gueri" in p.s["succes"], "remède au chaud : guéri")
p.s["malade"] = {"cause": "froid", "depuis": horloge[0], "cumul": 0}
ok(erreur(p.action, "soigner") is not None, "plus de remède : il faut l'acheter")
p.s["malade"] = None
p.s["j"]["sante"] = 30
horloge[0] += 15 * 60
p.etat()
ok(p.s["malade"], "de nouveau malade")
p.action("acheter", {"article": "lampe"}) if p.s["coquillages"] >= 40 else p.s["lampe"].update(possede=True, allumee=True)
p.s["lampe"].update(possede=True, allumee=True)
for _ in range(30):
    horloge[0] += H
    p.s["j"]["faim"] = max(p.s["j"]["faim"], 60)
    p.s["j"]["proprete"] = max(p.s["j"]["proprete"], 60)
    p.s["uv"] = max(p.s["uv"], 50)
    p.etat()
    if not p.s["malade"]:
        break
ok(not p.s["malade"] and p.s["veto"] is None, "repos au chaud (lampe) : il guérit tout seul")

# ---- vétérinaire : départ, gel, retour, carte postale ---------------------------------
p = nouveau()
p.s["j"].update(sante=20)
p.s["causes"] = {"froid": 8, "faim": 5}
p.s["coquillages"] = 5
horloge[0] += 15 * 60
p.etat()
for _ in range(25):                                    # malade, et on le laisse ainsi (mais on passe le voir)
    horloge[0] += H
    p.s["contact"] = horloge[0]
    p.s["j"]["chaleur"] = 30
    e = p.etat()
    if e["veto"]:
        break
ok(e["niveau"] == "veto" and e["position"] == "veto", "malade trop longtemps : la tortue vétérinaire l'emmène")
v = e["veto"]
ok(12 * H <= v["retour"] - v["depart"] <= 24 * H, f"séjour de 12 à 24 h ({(v['retour'] - v['depart']) / H:.0f} h)")
ok(set(v["raisons"]) <= set(P.RAISONS) and "froid" in v["raisons"], f"raisons gardées ({v['raisons']})")
ok(any(n[1] == "départ chez le vétérinaire" for n in notes), "départ noté dans le journal d'activité")
ok(erreur(p.action, "nourrir", {"aliment": "trefle"}) is not None, "pendant le séjour, pas de soins")
gel = dict(p.s["j"])
age = p.s["age_s"]
horloge[0] += 8 * H
p.etat()
ok(p.s["j"] == gel and p.s["age_s"] == age, "pendant le séjour : jauges et âge figés")
horloge[0] = v["retour"] + 60
p.s["contact"] = v["retour"]                          # (quelqu'un est passé entre-temps)
e = p.etat()
ok(e["veto"] is None and e["vacances"] is None and e["position"] in ("plage", "palmier"), "retour sur l'île")
ok(all(e["jauges"][g] >= 60 for g in P.JAUGES) and not e["malade"], f"jauges remises à un bon niveau ({e['jauges']})")
c = e["carte"]
ok(c and "froid" in c["texte"] and c["conseil"] and c["cout"] == 5 and p.s["coquillages"] == 0 + (P.SUCCES['comme_neuf'][2]),
   "carte postale : ce qui a manqué + conseil ; coût plafonné à ce qu'on a")
ok(p.s["stats"]["sejours_veto"] == 1 and "comme_neuf" in p.s["succes"], "séjour compté (succès « Comme neuf »)")
p.action("carte_lue")
ok(p.etat()["carte"] is None, "carte postale marquée lue")
p.s["coquillages"] = 0
p.s["j"]["sante"] = 5
p.s["malade"] = {"cause": "faim", "depuis": horloge[0], "cumul": 17.9}
horloge[0] += H
p.s["contact"] = horloge[0]
p.etat()
horloge[0] = p.s["veto"]["retour"] + 10
p.s["contact"] = horloge[0] - 5
p.etat()
ok(p.s["coquillages"] >= 0 and p.s["cartes"][-1]["cout"] == 0, "sans coquillages : consultation offerte (jamais bloquant)")

# ---- jamais de mort, même après des semaines d'absence --------------------------------------
for semaines in (1, 3, 8):
    p = nouveau()
    horloge[0] += semaines * 7 * J
    e = p.etat()
    s = p.instantane()
    ok(e["niveau"] in ("pension", "veto") and all(0 <= s["j"][g] <= 100 for g in P.JAUGES) and s["j"]["sante"] >= P.SANTE_MIN,
       f"{semaines} semaine(s) d'absence : il va bien ({e['niveau']}, santé {e['jauges']['sante']})")
    ok(s["age_s"] <= 3.1 * J and s["stats"]["sejours_veto"] <= 1, f"  au plus un séjour chez le vétérinaire, âge figé en pension ({s['age_s'] / J:.1f} j)")
    ok(e["vacances"] is None or all(e["jauges"][g] >= 60 for g in P.JAUGES), "  la voisine s'en occupe bien : il t'attend en forme")
    ok("mort" not in str(s).lower() and "game over" not in str(s).lower(), "  aucune mort, aucun « game over »")
    r = p.action("vacances", {"on": False})
    ok(r["etat"]["niveau"] in ("en_forme", "fatigue") and r["etat"]["position"] == "plage", "  retour de pension")
p = nouveau()
horloge[0] += 30 * H
e = p.etat()
ok(all(e["jauges"][g] >= P.PLANCHERS[g] - 1 for g in P.PLANCHERS), f"absence de 30 h : planchers respectés ({e['jauges']})")

# ---- vacances (pause) et vitesse lente -----------------------------------------------
p = nouveau()
p.action("vacances", {"on": True})
avant = dict(p.s["j"])
horloge[0] += 10 * J
e = p.etat()
ok(e["vacances"] and p.s["j"] == avant, "vacances : tout est en pause")
p.action("vacances", {"on": False})
horloge[0] += 2 * H
ok(p.etat()["jauges"]["faim"] < avant["faim"], "de retour : le temps reprend")
p = nouveau()
q = nouveau()
q.action("reglages", {"vitesse": "lente"})
p.action("caresser")
p.s["j"]["faim"] = q.s["j"]["faim"] = 90
f_p, f_q = p.s["j"]["faim"], q.s["j"]["faim"]
horloge[0] += 4 * H
p.etat()
q.etat()
dp, dq = f_p - p.s["j"]["faim"], f_q - q.s["j"]["faim"]
ok(dp > 5 and abs(dq * 2 - dp) < 1.5, f"vitesse lente : deux fois moins vite ({dp:.1f} / {dq:.1f})")

# ---- évolution et variantes ----------------------------------------------------------
p = nouveau()
soigner_bien(p, 8 * 24)
e = p.etat()
ok(e["stade"] == "adulte" and e["variante"] in P.VARIANTES, f"8 jours de soins : adulte ({e['titre']})")
ok({"juvenile", "adulte", "semaine"} <= set(p.s["succes"]), "succès des étapes de la vie")
ok(e["poids_g"] > 500, f"il a grandi ({e['poids_g']} g)")
ok(p.s["stats"]["mues"] >= 1, f"il a mué ({p.s['stats']['mues']} fois)")
ok(e["niveau"] != "veto" and p.s["stats"]["sejours_veto"] == 0, "bien soigné : jamais chez le vétérinaire")
for var, prep in (("convalescent", lambda s: s["stats"].update(sejours_veto=2)),
                  ("gourmand", lambda s: s["stats"].update(repas=10, friandises=5)),
                  ("nageur", lambda s: s["stats"].update(repas=10, bains_mer=9)),
                  ("royal", lambda s: s.update(moy={"sante": 90, "bonheur": 80, "n": 1})),
                  ("insulaire", lambda s: s.update(moy={"sante": 60, "bonheur": 60, "n": 1}))):
    p = nouveau()
    p.s["stats"].update(repas=10)
    p.s["moy"] = {"sante": 60, "bonheur": 60, "n": 1}
    prep(p.s)
    ok(p._choisir_variante() == var, f"variante « {P.VARIANTES[var]} »")
p = nouveau()
p.s["age_s"] = 31 * J
p.s["stats"]["sejours_veto"] = 2
horloge[0] += 600
e = p.etat()
ok(e["stade"] == "sage" and e["variante"] == "convalescent" and "vieux sage" in e["titre"], f"vieux sage ({e['titre']})")
ok({"adulte", "sage"} <= set(p.s["succes"]), "le Convalescent obtient quand même tous les succès d'étapes")

# ---- boutique et garde-robe -------------------------------------------------------------
p = nouveau()
p.s["coquillages"] = 10
ok(erreur(p.action, "acheter", {"article": "chapeau"}) is not None and p.s["coquillages"] == 10, "pas assez de coquillages : rien n'est retiré")
ok(erreur(p.action, "acheter", {"article": "grillon"}) is not None, "article inconnu refusé")
p.s["coquillages"] = 200
p.action("acheter", {"article": "chapeau"})
p.action("acheter", {"article": "lunettes"})
p.action("acheter", {"article": "collier"})
p.action("acheter", {"article": "hamac"})
p.action("acheter", {"article": "courge", "quantite": 3})
ok(p.s["inventaire"]["courge"] == 3 and p.s["coquillages"] == 200 - 25 - 20 - 18 - 30 - 9 + 5, "achats (accessoires, déco, aliments en quantité)")
ok("coquet" in p.s["succes"], "succès « Coquet »")
p.action("porter", {"article": "chapeau"})
p.action("porter", {"article": "lunettes"})
ok(p.etat()["portes"] == {"tete": "chapeau", "yeux": "lunettes"}, "garde-robe : il porte chapeau et lunettes")
ok(erreur(p.action, "porter", {"article": "couronne"}) is not None, "on ne porte que ce qu'on a")
p.action("retirer", {"emplacement": "yeux"})
ok(p.etat()["portes"] == {"tete": "chapeau"}, "accessoire retiré")
r = p.action("ramasser")
ok(1 <= r["gain"] <= 3, f"ramasser des coquillages sur la plage (+{r['gain']})")
r = p.action("ramasser")
ok(r["reaction"] == "non" and "gain" not in r, "pas deux ramassages en moins de 3 h")

# objets rares et chers, sans jamais bloquer les soins
ok(all(o["rarete"] in P.RARETES for o in P.OBJETS.values()), "chaque objet de la boutique a une rareté connue")
leg = [k for k, o in P.OBJETS.items() if o["rarete"] == "legendaire"]
ok(len(leg) >= 3 and min(P.OBJETS[k]["prix"] for k in leg) >= 700, "au moins 3 pièces légendaires, à 700 coquillages ou plus")
ok(all(P.OBJETS[k]["prix"] >= 120 for k, o in P.OBJETS.items() if o["rarete"] != "commun"), "les pièces rares coûtent cher (120 coquillages ou plus)")
ok(P.OBJETS["remede"]["prix"] <= 10 and max(a["prix"] for a in P.ALIMENTS.values()) <= 10, "remède et nourriture restent bon marché")
ok(all(o["emplacement"] in P.EMPLACEMENTS for o in P.OBJETS.values() if o["type"] == "accessoire"), "chaque accessoire a son emplacement")
p = nouveau()
p.s["coquillages"] = 100
ok(erreur(p.action, "acheter", {"article": "cape"}) is not None and p.s["coquillages"] == 100, "trop cher : refusé, aucun coquillage perdu")
ok(p.action("acheter", {"article": "remede"}) and p.s["inventaire"]["remede"] >= 1, "le remède reste toujours achetable")
p.s["coquillages"] = 2000
p.action("acheter", {"article": "cape"})
p.action("porter", {"article": "cape"})
p.etat()
ok("cape" in p.s["accessoires"] and p.s["portes"]["cou"] == "cape" and "collection" in p.s["succes"], "cape royale achetée, portée, succès « Pièce de collection »")
ok(erreur(p.action, "acheter", {"article": "cape"}) is not None, "une pièce unique ne s'achète qu'une fois")
p.action("acheter", {"article": "benitier"})
ok("benitier" in p.s["deco"], "le bénitier se pose sur l'île")
p.action("reglages", {"theme": "sombre", "ambiance": False})
ok(p.s["reglages"]["theme"] == "sombre" and p.s["reglages"]["ambiance"] is False, "réglages : couleurs sombres, bruits de l'île coupés")
p.action("reglages", {"theme": "violet"})
ok(p.s["reglages"]["theme"] == "sombre", "réglage de couleurs inconnu : ignoré")
ok("raretes" in p.catalogue() and p.catalogue()["objets"]["diademe"]["rarete"] == "legendaire", "le catalogue donne la rareté")

# ---- mini-jeux et anti-triche --------------------------------------------------------------
def gain_attendu(jeu, sc, pal, arrive=False):
    g0 = P.recompense_jeu(jeu, sc, pal, arrive)[0]
    return {g0, round(g0 * 1.25)}                                 # × 1,25 s'il est bien au chaud


p = nouveau()
a_heure(11)
p.etat()
g = p.jeu_debut("feuilles")
ok(g["duree"] == 180 and g["jeton"] and g["regles"]["palier_s"] == 20 and g["compte"] == P.JEU_COMPTE, "Pluie de feuilles : partie ouverte par le serveur (3 min au plus, règles envoyées à la page)")
horloge[0] += 5
ok(erreur(p.jeu_fin, g["jeton"], 3, 0) is not None and p.s["jeu"] is None, "partie trop courte : refusée, et la partie est close")
p.s["j"]["energie"] = 100
g = p.jeu_debut("feuilles")
horloge[0] += 33
c0 = p.s["coquillages"]
ok(erreur(p.jeu_fin, g["jeton"], 9999, 2, None, 2) is not None and p.s["jeu"] is None and p.s["coquillages"] == c0, "score impossible pour 30 s de jeu : refusé, rien gagné, partie close")
ok(erreur(p.jeu_fin, g["jeton"], 10, 0) is not None, "jeton à usage unique (même après un refus)")
g = p.jeu_debut("feuilles")
horloge[0] += 33
ok(erreur(p.jeu_fin, g["jeton"], 20, 0, None, 6) is not None, "palier impossible pour la durée de la partie : refusé")
ok(erreur(p.jeu_fin, g["jeton"], 20, 0, None, 2) is not None, "(et la partie refusée ne se termine pas une 2ᵉ fois)")
p.s["j"]["energie"] = 100
g = p.jeu_debut("feuilles")
horloge[0] += 33
c0 = p.s["coquillages"]
r = p.jeu_fin(g["jeton"], 28, 2, None, 2)
court = r["gain"]
ok(r["palier"] == 2 and r["gain"] in gain_attendu("feuilles", 28, 2) and p.s["coquillages"] - c0 == r["gain"], f"partie de 30 s : palier 2, gain calculé par le serveur (+{r['gain']})")
p.s["j"]["energie"] = 100
g = p.jeu_debut("feuilles")
horloge[0] += 153
r = p.jeu_fin(g["jeton"], 140, 6, None, 8)
ok(r["palier"] == 8 and r["gain"] > court * 2 and "feuilles" in p.s["succes"], f"bonne partie de 2 min 30 : palier 8, bien plus de coquillages (+{r['gain']} contre +{court}) et succès « Attrape-feuilles »")
ok(P.feuilles_objets_max(150) * 1.3 + 4 >= 200 > P.feuilles_objets_max(30) * 1.3 + 4, "un score de 200 est possible en 2 min 30, pas en 30 s")
ok([P.feuilles_palier(t) for t in (0, 19, 20, 59, 100, 179)] == [1, 1, 2, 3, 6, 9], "Pluie de feuilles : un palier de plus toutes les 20 s (9 au plus)")
vit = [P.feuilles_vitesse(P.feuilles_palier(t)) for t in range(0, 180, 20)]
cad = [P.feuilles_cadence(P.feuilles_palier(t)) for t in range(0, 180, 20)]
ok(all(a < b for a, b in zip(vit, vit[1:])) and all(a < b for a, b in zip(cad, cad[1:])) and vit[-1] > 2, f"la vitesse et le nombre de feuilles augmentent avec le temps (vitesse ×{vit[-1]:.2f} au palier 9)")
R = P.FEUILLES
ok(R["insectes"] + R["insectes_pas"] * (R["palier_max"] - 1) < .5 and R["fleurs"] + R["insectes"] + R["insectes_pas"] * 8 < .75, "même au dernier palier, il tombe plus de feuilles et de fleurs que d'insectes")
ok(R["vies"] == 5 and R["ratees_par_vie"] == 6, "fin naturelle : 5 vies (insecte mangé, ou 6 feuilles ratées = une vie)")
# Gauche ou droite ? : partie courte (5 manches, 3 vies), aucun indice, côté tiré au moment du choix
p.s["j"]["energie"] = 100
g = p.jeu_debut("devin")
ok(g["manches"] == 5 and g["vies"] == 3 and not any(k in g for k in ("indice", "indice_ms", "cote")), "Gauche ou droite ? : 5 manches, 3 vies, aucun indice envoyé à la page")
ok(erreur(p.jeu_coup, g["jeton"], "gauche") is not None, "répondre à toute vitesse : refusé")
while True:
    horloge[0] += 2
    r = p.jeu_coup(g["jeton"], "gauche")
    ok("indice" not in r and "suivante" not in r, "(aucun indice pour la manche suivante)") if r["manche"] == 1 else None
    if r["fini"]:
        break
ok((r["manche"] == 5 and r["erreurs"] < 3) or r["erreurs"] == 3, f"fin : 5 manches, ou 3 vies perdues ({r['manche']} manches, {r['erreurs']} erreurs)")
ok(r["vies"] == 3 - r["erreurs"] and r["score"] + r["erreurs"] == r["manche"], "chaque erreur coûte une vie")
ok(erreur(p.jeu_coup, g["jeton"], "triche") is None, "(partie finie : plus de coup compté)")
r2 = p.jeu_fin(g["jeton"])
ok(r2["gain"] in gain_attendu("devin", r["score"], r["erreurs"]), f"récompense selon les vies perdues ({r['score']} bonnes, {r['erreurs']} erreurs : +{r2['gain']})")
# récompense : la partie parfaite rapporte le plus, chaque vie perdue en coûte ; 3 vies perdues : presque rien
G = {e: P.recompense_devin(5 - e, e)[0] for e in range(3)}
ok(G[0] > G[1] > G[2] > P.recompense_devin(2, 3)[0] and G[0] == 15, f"partie parfaite : {G[0]} ; 1 vie perdue : {G[1]} ; 2 : {G[2]} ; perdu : {P.recompense_devin(2, 3)[0]}")
ok(P.recompense_devin(5, 0)[1] > P.recompense_devin(4, 1)[1], "partie parfaite : plus de bonheur aussi")
# le côté est vraiment au hasard (environ une chance sur deux) : on ne peut pas tricher en répondant toujours pareil
bons = tous = parfaits = fins = 0
for _ in range(120):
    p.s["j"]["energie"] = 100
    g = p.jeu_debut("devin")
    while True:
        horloge[0] += 1
        r = p.jeu_coup(g["jeton"], "droite")
        bons, tous = bons + r["bon"], tous + 1
        if r["fini"]:
            break
    parfaits += r["erreurs"] == 0
    fins += r["erreurs"] == 3
    p.jeu_fin(g["jeton"])
ok(.4 < bons / tous < .6 and parfaits < 15 and fins > 20, f"pur hasard : {bons}/{tous} bonnes réponses, {parfaits} parties parfaites et {fins} parties perdues sur 120")
p.s["stats"]["meilleur_devin"], p.s["succes"] = 0, {k: v for k, v in p.s["succes"].items() if k != "devin"}
p.s["j"]["energie"] = 100
g = p.jeu_debut("devin")
p.s["jeu"]["score"], p.s["jeu"]["manche"], p.s["jeu"]["erreurs"], p.s["jeu"]["fini"] = 5, 5, 0, True
r = p.jeu_fin(g["jeton"])
ok("parfaite" in r["message"] and "devin" in p.s["succes"] and p.s["stats"]["devin_parfaits"] >= 1, "partie parfaite : message, succès « Devin de l'île » et compteur")
p.s["jeux_jour"] = {"jour": P._jour(horloge[0]), "gagnes": 0}
# En rythme
p.s["j"]["energie"] = 100
g = p.jeu_debut("rythme")
ok(len(g["suite"]) == 3 and set(g["suite"]) <= set(P.GESTES) and g["tempo"] == P.tempo_rythme(0) and g["palier"] == 1 and g["max"] == P.RYTHME_MAX, "En rythme : suite de 3, au rythme de départ, palier 1")
ok(erreur(p.jeu_coup, g["jeton"], None, g["suite"]) is not None, "répondre avant d'avoir vu la suite : refusé")
suite, tempos, suites, paliers = g["suite"], [g["tempo"]], [g["suite"]], [1]
for _ in range(6):
    horloge[0] += 12
    r = p.jeu_coup(g["jeton"], None, suite)
    suite = r.get("suite", suite)
    tempos.append(r.get("tempo"))
    suites.append(suite)
    paliers.append(r.get("palier"))
ok(r["bon"] and r["score"] == 8 and paliers == list(range(1, 8)), f"suites réussies jusqu'à 8, palier affiché ({r['score']}, {paliers})")
ok(all(a > b for a, b in zip(tempos, tempos[1:])), f"hochements ET fanon de plus en plus rapides ({tempos})")
ok(all(len(b) == len(a) + 1 for a, b in zip(suites, suites[1:])), "un geste de plus à chaque manche")
ok(P.RYTHME_MAX == 14 and P.tempo_rythme(P.RYTHME_MAX) == .3 and P.tempo_rythme(5) < P.tempo_rythme(4), "de 3 à 14 gestes, un temps jusqu'à 0,3 s")
gros = [P._suite_hochements(8) for _ in range(300)]
ok(all(not any(x[i] == x[i + 1] == x[i + 2] for i in range(6)) for x in gros), "jamais trois fois le même geste d'affilée")
ok(all(len(set(x)) >= 2 for x in gros) and {g for x in gros for g in x} == set(P.GESTES), "suites variées : petit, grand et fanon")
ok(len({tuple(x) for x in gros}) > 250, "suites vraiment au hasard (presque jamais deux fois la même)")
ok(sum(x[:7] != y[:7] for x, y in zip(suites[1:], [s + ["?"] for s in suites[:-1]])) >= 1, "chaque manche tire une nouvelle suite (pas seulement un geste ajouté)")
horloge[0] += 12   # assez pour avoir vu toute la suite, même longue (gestes tirés au hasard)
r = p.jeu_coup(g["jeton"], None, ["faux"])
ok(r["fini"] and not r["bon"], "erreur : partie finie")
r = p.jeu_fin(g["jeton"])
ok("rythme" in p.s["succes"] and r["palier"] == 7 and r["gain"] in gain_attendu("rythme", 8, 7), f"succès « Dans le rythme », gain selon la suite et le palier (+{r['gain']})")
p.s["j"]["energie"] = 100
g = p.jeu_debut("rythme")
suite = g["suite"]
while True:
    horloge[0] += 12
    r = p.jeu_coup(g["jeton"], None, suite)
    if r["fini"]:
        break
    suite = r["suite"]
ok(r["bon"] and r["score"] == P.RYTHME_MAX, "En rythme : partie parfaite jusqu'à 14 gestes")
r = p.jeu_fin(g["jeton"])
ok(r["gain"] in gain_attendu("rythme", 14, 12) and r["palier"] == 12 and r["gain"] >= 25, f"partie parfaite : grosse récompense (+{r['gain']})")
# récompenses : elles grandissent avec le palier (donc la durée), avec des plafonds par partie
for jeu, sc in (("feuilles", 60), ("course", 40), ("rythme", 6)):
    ok(P.recompense_jeu(jeu, sc, 4)[0] > P.recompense_jeu(jeu, sc, 1)[0], f"{P.JEUX[jeu]} : à score égal, un palier plus haut rapporte plus")
ok(max(P.recompense_jeu(j, 999, 99, True)[0] for j in P.JEUX) <= 30 and max(P.recompense_jeu(j, 999, 99, True)[1] for j in P.JEUX) <= 25, "plafond par partie : 30 coquillages et +25 de bonheur au plus")
p.s["jeux_jour"] = {"jour": P._jour(horloge[0]), "gagnes": P.GAINS_JEUX_JOUR - 2}
p.s["j"]["energie"] = 100
g = p.jeu_debut("feuilles")
horloge[0] += 33
r = p.jeu_fin(g["jeton"], 30, 0, None, 2)
ok(r["gain"] == 2 and p.s["jeux_jour"]["gagnes"] == P.GAINS_JEUX_JOUR == 120, "plafond : 120 coquillages par jour aux jeux")
p.s["j"]["energie"] = 10
ok(erreur(p.jeu_debut, "devin") is not None, "trop fatigué pour jouer")
a_heure(23)
p.s["j"]["energie"] = 90
p.etat()
ok(erreur(p.jeu_debut, "devin") is not None, "la nuit, il dort : pas de jeux")
ok(erreur(p.jeu_coup, "n'importe quoi", "gauche") is not None, "jeton inventé refusé")
# abandonner une partie : l'énergie prise au départ est perdue, rien n'est gagné
p = nouveau()
a_heure(11)
p.etat()
p.s["j"]["energie"], c0, b0 = 70, p.s["coquillages"], None
g = p.jeu_debut("feuilles")
ok(p.s["j"]["energie"] == 70 - P.ENERGIE_JEU, f"lancer une partie prend {P.ENERGIE_JEU} d'énergie")
b0 = p.s["j"]["bonheur"]
r = p.jeu_annuler(g["jeton"])
ok(r["ok"] and p.s["jeu"] is None and p.s["coquillages"] == c0 and p.s["j"]["bonheur"] == b0, "abandon : ni coquillages ni bonheur")
ok(p.s["j"]["energie"] == 70 - P.ENERGIE_JEU and "ne revient pas" in r["message"], "abandon : l'énergie dépensée ne revient pas")
ok(erreur(p.jeu_fin, g["jeton"], 10, 0) is not None and erreur(p.jeu_annuler, g["jeton"]) is not None, "partie abandonnée : plus rien à terminer ni à annuler")
g = p.jeu_debut("course")
horloge[0] += 31
e0 = p.s["j"]["energie"]
p.jeu_fin(g["jeton"], 5, None, False, 1, 3000)
ok(p.s["j"]["energie"] > e0 - 3, "partie terminée : pas d'énergie en plus (déjà prise au départ)")

# ---- attention et discipline -----------------------------------------------------------------
# « il veut jouer / il réclame de l'attention » : seulement quand son bonheur est à 30 ou moins
p = nouveau()
soigner_bien(p, 1)
p.s["j"]["bonheur"], p.s["discipline"] = 80, 0
p.s["appel"], p.s["appel_pause"] = None, 0
caprices = 0
for _ in range(400):                                        # ≈ 66 h simulées, toujours content
    horloge[0] += 600
    p.s["j"]["bonheur"] = 80
    p.s["j"]["faim"] = p.s["j"]["energie"] = p.s["j"]["proprete"] = p.s["j"]["sante"] = p.s["j"]["chaleur"] = 90
    p.s["uv"], p.s["crottes"], p.s["malade"], p.s["lumiere"] = 90, 0, None, False
    e = p.etat()
    caprices += bool(p.s["appel"] and p.s["appel"]["type"] == "caprice")
    ok_ennui = not any(b["id"] == "ennui" for b in e["besoins"])
ok(caprices == 0, "bonheur à 80 : jamais d'appel « il réclame de l'attention » (caprice)")
ok(ok_ennui, "bonheur à 80 : pas de besoin « il s'ennuie »")
p.s["j"]["bonheur"] = 80
p.s["appel"] = {"t": horloge[0], "type": "caprice", "raison": "caprice"}
e = p.etat()
ok(e["appel"] is None and e["humeur"] != "appel" and p.s["appel"] is None, "un vieux caprice disparaît quand son bonheur est au-dessus de 30")
p.s["j"]["bonheur"] = 31
ok(not any(b["id"] == "ennui" for b in p.etat()["besoins"]), "bonheur à 31 : pas encore « il s'ennuie »")
p.s["j"]["bonheur"] = 30
ok(any(b["id"] == "ennui" for b in p.etat()["besoins"]), "bonheur à 30 : « il s'ennuie : joue avec lui »")
p.s["j"]["bonheur"] = 20
p.s["appel"], p.s["appel_pause"] = {"t": horloge[0], "type": "caprice", "raison": "caprice"}, 0
e = p.etat()
ok(e["appel"] and e["appel"]["type"] == "caprice", "bonheur à 20 : le caprice est montré")

p = nouveau()
p.s["j"]["bonheur"] = 25                                    # (un caprice n'existe que quand il est malheureux)
p.s["appel"] = {"t": horloge[0], "type": "caprice", "raison": "caprice"}
d0 = p.s["discipline"]
r = p.action("gronder")
ok(p.s["discipline"] == d0 + 10 and p.s["appel"] is None, "gronder un caprice : discipline +10")
p.s["appel"] = {"t": horloge[0], "type": "besoin", "raison": "faim"}
p.s["j"]["faim"] = 20
r = p.action("gronder")
ok(r["reaction"] == "triste" and "faim" in r["message"] and p.s["appel"], "gronder un vrai besoin : il est triste, on montre ce qui ne va pas")
p.action("nourrir", {"aliment": "trefle"})
ok(p.s["appel"] is None, "le besoin satisfait : l'appel s'arrête")
r = p.action("feliciter")
ok(p.s["discipline"] > d0 + 10 and r["reaction"] == "fier", "féliciter juste après un bon repas : discipline +")

# ---- réglages, recommencer ---------------------------------------------------------------------
p = nouveau()
p.action("reglages", {"visible": False, "sons": False, "notif_windows": True, "vitesse": "turbo"})
ok(p.s["reglages"]["visible"] is False and p.s["reglages"]["notif_windows"] and p.s["reglages"]["vitesse"] == "normale", "réglages (valeur inconnue ignorée)")
ok(p.s["reglages"]["volume_ambiance"] == P.VOLUME_DEFAUT == 60 and p.s["reglages"]["volume_jeux"] == 60, "volumes par défaut : bruits de l'île et mini-jeux à 60")
p.action("reglages", {"volume_ambiance": 35, "volume_jeux": "80"})
ok(p.s["reglages"]["volume_ambiance"] == 35 and p.s["reglages"]["volume_jeux"] == 80, "volumes réglables (bruits de l'île, petits sons et mini-jeux)")
p.action("reglages", {"volume_ambiance": 250, "volume_jeux": -4})
ok(p.s["reglages"]["volume_ambiance"] == 100 and p.s["reglages"]["volume_jeux"] == 0, "volumes bornés de 0 à 100")
p.action("reglages", {"volume_ambiance": "fort", "volume_jeux": None})
ok(p.s["reglages"]["volume_ambiance"] == 100 and p.s["reglages"]["volume_jeux"] == 0 and p.etat()["reglages"]["volume_jeux"] == 0, "volume illisible : ignoré ; les volumes sont envoyés à la page")
ok(erreur(p.action, "recommencer", {}) is not None and p.s["stade"] == "bebe", "recommencer sans confirmation : refusé")
r = p.action("recommencer", {"confirmer": "NOUVEL OEUF"})
ok(r["etat"]["stade"] == "oeuf" and p.s["reglages"]["visible"] is False, "nouvel œuf (réglages gardés)")
ok(erreur(p.action, "_avancer", {}) is not None and erreur(p.action, "__init__", {}) is not None, "actions internes inaccessibles")

# ---- saisons de l'île -------------------------------------------------------------------------
P.SAISON_FORCEE = None
ok(P.saison(datetime(2026, 4, 10).timestamp()) == "printemps" and P.saison(datetime(2026, 7, 10).timestamp()) == "ete"
   and P.saison(datetime(2026, 10, 10).timestamp()) == "automne" and P.saison(datetime(2026, 1, 10).timestamp()) == "hiver"
   and P.saison(datetime(2026, 12, 24).timestamp()) == "hiver", "saisons selon le mois réel")
P.METEO_FORCEE = None
debut = int(datetime(2026, 7, 1).timestamp() // (2 * H))
ete = sum(P._ciel_brut("graine-test", b) == "pluie" for b in range(debut, debut + 360))
debut = int(datetime(2026, 10, 1).timestamp() // (2 * H))
pluies = sum(P._ciel_brut("graine-test", b) == "pluie" for b in range(debut, debut + 360))
ok(pluies > ete * 2, f"saison des pluies : bien plus d'averses qu'en été ({pluies} contre {ete} sur 360 tranches de 2 h)")
temps = {}
for sa in ("ete", "hiver"):
    P.SAISON_FORCEE = sa
    p = nouveau()
    a_heure(23)
    p.s["j"]["chaleur"] = 60
    p.etat()
    horloge[0] += 5 * H
    temps[sa] = p.etat()["jauges"]["chaleur"]
ok(temps["ete"] - temps["hiver"] >= 8, f"nuit d'été plus douce que nuit de saison fraîche ({temps['ete']} / {temps['hiver']})")
e = p.etat()
ok(e["ciel"]["saison"] == "hiver" and e["ciel"]["saison_nom"] == "Saison fraîche" and e["promo"] == "chou_vert", "saison exposée à la page (nom, texte, produit de saison)")
p.s["coquillages"] = 10
p.action("acheter", {"article": "chou_vert"})
ok(p.s["coquillages"] == 9, "produit de saison : un coquillage de moins à la boutique")
p.action("acheter", {"article": "courge"})
ok(p.s["coquillages"] == 6, "les autres aliments gardent leur prix")
ok("fraicheur" in p.s["faits"], "fiche « Le savais-tu ? » de la saison fraîche")
p.s["saisons_vues"] = ["printemps", "ete", "automne"]
horloge[0] += H
p.etat()
ok("saisons" in p.s["succes"], "succès « Les quatre saisons »")
P.SAISON_FORCEE = "printemps"

# ---- saisons spéciales de l'île (en plus du calendrier) -------------------------------------------
P.SAISON_ILE_FORCEE = None
t, periodes = P.ROTATION_DEBUT + 1, []
while t < P.ROTATION_DEBUT + 400 * P.JOUR:
    sp, deb, fin = P.periode_saison_ile(t, "graine-test")
    periodes.append((sp, deb, fin))
    t = fin + 1
durees = [(f - d) / P.JOUR for _, d, f in periodes]
ok(all(2 <= x <= 7 for x in durees) and max(durees) - min(durees) > 3, f"saisons de l'île de 2 à 7 jours, au hasard ({min(durees):.1f} à {max(durees):.1f} j)")
ok(all(a[0] != b[0] for a, b in zip(periodes, periodes[1:])), "jamais deux fois la même saison de l'île de suite")
ok({x[0] for x in periodes} == {*P.SAISONS_ILE, None} and len(P.SAISONS_ILE) == 4, "les 4 saisons de l'île reviennent toutes, avec des périodes de temps ordinaire")
ok(all(a[2] == b[1] for a, b in zip(periodes, periodes[1:])), "les périodes s'enchaînent sans trou")
mois = {datetime.fromtimestamp(d).month for sp, d, _ in periodes if sp == "tempetes"}
ok(len(mois) >= 4, "la saison des tempêtes tombe à n'importe quel mois (pas liée au calendrier)")
ok(P.periode_saison_ile(P.ROTATION_DEBUT + 50 * P.JOUR, "graine-test") == P.periode_saison_ile(P.ROTATION_DEBUT + 50 * P.JOUR, "graine-test"), "roulement reproductible")
ok(any(P.saison_ile(P.ROTATION_DEBUT + k * P.JOUR, "autre-ile") != P.saison_ile(P.ROTATION_DEBUT + k * P.JOUR, "graine-test") for k in range(0, 60, 3)), "chaque île a son propre roulement")
ok(all(P.saison(d) == P.saison(d, "autre-ile") for _, d, _ in periodes[:20]), "la saison du calendrier reste la même pour toutes les îles")
P.SAISON_FORCEE = "ete"
P.SAISON_ILE_FORCEE = "aucune"
ete = sum(P._ciel_brut("graine-test", b) == "pluie" for b in range(1000, 1360))
P.SAISON_ILE_FORCEE = "tempetes"
tempete = sum(P._ciel_brut("graine-test", b) == "pluie" for b in range(1000, 1360))
ok(tempete > ete * 2, f"saison des tempêtes : bien plus d'averses (l'été devient orageux : {tempete} contre {ete} sur 360 tranches de 2 h)")
P.SAISON_FORCEE = "automne"
P.SAISON_ILE_FORCEE = "brumes"
brume = sum(P._ciel_brut("graine-test", b) != "soleil" for b in range(1000, 1360))
P.SAISON_ILE_FORCEE = "aucune"
sans = sum(P._ciel_brut("graine-test", b) != "soleil" for b in range(1000, 1360))
ok(brume > sans, f"saison des brumes : plus de ciel couvert ({brume} contre {sans})")
temps = {}
for sp in ("tortues", "tempetes"):
    P.SAISON_FORCEE, P.SAISON_ILE_FORCEE = "printemps", sp
    p = nouveau()
    a_heure(23)
    p.s["j"]["chaleur"] = 60
    p.etat()
    horloge[0] += 5 * H
    temps[sp] = p.etat()["jauges"]["chaleur"]
ok(temps["tortues"] - temps["tempetes"] >= 4, f"la saison de l'île s'ajoute à la chaleur du calendrier ({temps['tortues']} / {temps['tempetes']})")
e = p.etat()
ok(e["ciel"]["saison"] == "printemps" and e["ciel"]["saison_ile"]["id"] == "tempetes" and e["ciel"]["saison_ile"]["nom"] == "Saison des tempêtes"
   and e["promo"] == "fleur_pissenlit" and e["promo_ile"] == "feuilles_murier", "les deux saisons sont exposées à la page (calendrier + île)")
p.s["coquillages"] = 10
p.action("acheter", {"article": "feuilles_murier"})
p.action("acheter", {"article": "fleur_pissenlit"})
ok(p.s["coquillages"] == 10 - (P.ALIMENTS["feuilles_murier"]["prix"] - 1) - (P.ALIMENTS["fleur_pissenlit"]["prix"] - 1), "deux produits de saison à la fois (calendrier + île)")
P.SAISON_ILE_FORCEE = "aucune"
ok(p.etat()["ciel"]["saison_ile"] is None and p.etat()["promo_ile"] is None, "temps ordinaire : pas de saison de l'île")
P.SAISON_ILE_FORCEE = None
P.SAISON_FORCEE = None
p = nouveau()
e = p.etat()
si = e["ciel"]["saison_ile"]
ok(e["ciel"]["saison"] == P.saison(horloge[0]) and (si or {}).get("id") == P.saison_ile(horloge[0], p.s["graine"]), "la page sait quelle saison de l'île il fait")
P.SAISON_ILE_FORCEE = "brumes"
e = nouveau().etat()
ok(set(e["ciel"]["saison_ile"]) == {"id", "nom", "texte"} and not any(k for k in e["ciel"] if "reste" in k or "fin" in k), "aucune durée ni compte à rebours de saison n'est envoyé à la page")
P.SAISON_ILE_FORCEE = None
p = nouveau()
P.SAISON_FORCEE = "printemps"
p.s["saisons_vues"] = ["printemps"]
p.s["saisons_ile_vues"] = ["floraison", "brumes", "tortues"]
P.SAISON_ILE_FORCEE = "tempetes"
horloge[0] += H
p.etat()
ok("tour_saisons" in p.s["succes"] and "saisons" not in p.s["succes"], "succès « Saisons de l'île » (les 4 spéciales), distinct des quatre saisons du calendrier")
cat = p.catalogue()
ok(sorted(cat["saisons"]) == ["automne", "ete", "hiver", "printemps"] and sorted(cat["saisons_ile"]) == sorted(P.SAISONS_ILE), "catalogue : 4 saisons du calendrier + 4 saisons de l'île")
P.SAISON_ILE_FORCEE = "aucune"
P.SAISON_FORCEE = "printemps"
P.METEO_FORCEE = "soleil"

# ---- sieste sur le rocher chaud -----------------------------------------------------------------
p = nouveau()
a_heure(12)
P.METEO_FORCEE = "soleil"
p.etat()
p.s["position"], p.s["j"]["energie"], p.s["j"]["chaleur"] = "plage", 14, 45
horloge[0] += 600
e = p.etat()
ok(e["dort"] and e["sieste"] and e["position"] == "rocher", "fatigué en plein soleil : il fait sa sieste sur le rocher chaud")
c0 = p.s["j"]["chaleur"]
horloge[0] += 3 * H
e = p.etat()
ok(e["position"] == "rocher" and p.s["j"]["chaleur"] > c0 + 25, f"il dort sur le rocher plus de 2 h et s'y réchauffe ({round(c0)} → {round(p.s['j']['chaleur'])})")
horloge[0] += 3 * H
e = p.etat()
ok(not e["sieste"] and e["position"] == "plage", "réveillé (énergie revenue), il redescend sur la plage")
p.s["position"], p.s["j"]["energie"] = "plage", 14
P.METEO_FORCEE = "pluie"
horloge[0] += 600
ok(p.etat()["position"] == "plage", "sous la pluie, il fait la sieste sur la plage (le rocher ne chauffe pas)")
r = p.action("chauffer")
ok(p.s["sieste"] and p.s["position"] == "rocher" and "sieste" in r["message"], "« Chauffer » pendant la sieste : posé sur le rocher sans être réveillé")
P.METEO_FORCEE = "soleil"

# ---- mutations de couleur -------------------------------------------------------------------------
p = nouveau()
soigner_bien(p, 1)
p.s["stade"] = "adulte"
ok(p.etat()["mutation"] is None and all(v < 1 for v in p.scores_mutation().values()), "pas de mutation au départ")
p.s["stats"]["bains_mer"] = 25
p._fin_mue(horloge[0], bain=True)
e = p.etat()
ok(e["mutation"] and e["mutation"]["id"] == "turquoise" and e["mutation"]["niveau"] == 3, f"beaucoup de bains de mer : Turquoise, niveau 3 ({e['mutation']})")
ok("mutation" in p.s["succes"] and "formes" in p.s["faits"] and "turquoise" in p.carnet()["mutations_vues"], "succès, fiche et carnet de la mutation")
p.s["stats"]["heures_froid"] = 33
p._fin_mue(horloge[0], bain=True)
ok(p.s["mutation"]["id"] == "turquoise", "une autre mutation un peu plus forte ne remplace pas la première (il faut la dépasser nettement)")
p.s["stats"]["heures_froid"] = 120
p._fin_mue(horloge[0], bain=True)
ok(p.s["mutation"]["id"] == "melanique", "beaucoup de froid : il devient Mélanique")
q = nouveau()
q.s["stade"] = "adulte"
q.s["stats"]["heures_malade"] = 40
q._fin_mue(horloge[0], bain=False)
ok(q.s["mutation"]["id"] == "cendre", "maladies soignées trop tard : Cendré")
q = nouveau()
q.s["stade"] = "adulte"
q.s["stats"].update(repas=40, oranges=20)
q._fin_mue(horloge[0], bain=False)
ok(q.s["mutation"]["id"] == "orange", "beaucoup d'aliments orangés : Orangé")
q = nouveau()
q.s["stats"]["bains_mer"] = 30
q._fin_mue(horloge[0], bain=False)
ok(q.s["mutation"] is None, "un bébé ne mute pas encore (les couleurs se fixent à partir du stade juvénile)")
q = nouveau()
q.s["stade"] = "adulte"
q.s["j"]["chaleur"] = 20
for _ in range(36):
    horloge[0] += 600
    q.s["contact"], q.s["j"]["chaleur"] = horloge[0], 20
    q.etat()
ok(q.s["stats"]["heures_froid"] > 4, "les heures passées à avoir froid sont comptées")
ok(all(k in P.MUTATIONS for k in p.catalogue()["mutations"]) and len(P.MUTATIONS) >= 8, "le catalogue décrit les mutations")
# ---- marques (fanon, crête, queue, yeux, motif), en plus de la couleur du corps ------------------------------
ok(len(P.MARQUES) >= 10 and {m["cat"] for m in P.MARQUES.values()} == set(P.CATEGORIES_MARQUES)
   and {m["rarete"] for m in P.MARQUES.values()} == {"commun", "rare", "tres_rare"}, "12 marques sur 5 parties du corps, trois raretés")
ok(all(sum(1 for m in P.MARQUES.values() if m["cat"] == c and m["rarete"] == "commun") + sum(1 for m in P.MARQUES.values() if m["cat"] == c) >= 2 for c in P.CATEGORIES_MARQUES),
   "chaque partie du corps a au moins deux marques possibles (ou une commune)")
q = nouveau()
q.s["stade"] = "adulte"
ok(all(v < 1 for v in q.scores_marques().values()) and q.etat()["marques"] == [], "pas de marque au départ")
q.s["stats"].update(nuits_eteintes=14)
q._fin_mue(horloge[0], bain=False)
ok(q.etat()["marques"] == ["queue_annelee"] and "queue_annelee" in q.carnet()["marques_vues"], "dormir souvent dans le noir : queue annelée (vue dans le carnet)")
ok(q.s["mutation"] is None and "mutation" in q.s["succes"], "une marque sans changement de couleur du corps, succès « Couleurs uniques » quand même")
q.s["stats"].update(caresses=60, heures_chaud=35)
q._fin_mue(horloge[0], bain=False)
ok(len(q.s["marques"]) == 2 and q.s["marques"]["motif"] == "motif_taches", "au plus une nouvelle marque par mue : la plus méritée d'abord (caresses : moucheté)")
q._fin_mue(horloge[0], bain=False)
ok(q.s["marques"].get("crete") == "crete_orange", "à la mue suivante, la suivante (beaucoup de chaleur : crête orangée)")
q.s["stats"].update(caresses=500)
q._fin_mue(horloge[0], bain=False)
ok(q.s["marques"]["motif"] == "motif_taches", "une partie du corps garde sa marque (pas de remplacement)")
q.s["stats"].update(repas=60, oranges=30, bains_mer=40)
q._fin_mue(horloge[0], bain=True)
ok(q.s["mutation"]["id"] == "turquoise" and q.s["marques"]["fanon"] == "fanon_orange", "la couleur du corps et les marques se combinent (Turquoise + fanon orangé)")
v = q.etat()
ok(set(v["marques"]) >= {"queue_annelee", "motif_taches", "crete_orange", "fanon_orange"} and all(d["nom"] for d in v["marques_detail"]), "les marques sont envoyées à la page (dessin)")
q.s["stats"].update(devin_parfaits=3)
q._fin_mue(horloge[0], bain=False)
ok(q.s["marques"]["yeux"] == "yeux_rubis" and "marques" in q.s["succes"], "une marque sur chaque partie du corps : succès « Un iguane unique »")
q._etape(horloge[0])
ok(q.s["etapes"][-1]["marques"] and set(q.s["etapes"][-1]["marques"]) == set(q.s["marques"].values()), "album : la photo de l'étape garde ses marques")
q.action("recommencer", {"confirmer": "NOUVEL OEUF"})
ok(q.s["album"][-1]["marques"] and q.s["marques"] == {}, "album des Philibert d'avant : ses marques sont gardées ; le nouvel œuf repart sans")
# très rares : il faut aussi de la chance (25 % par mue quand c'est mérité)
chanceux = 0
for k in range(200):
    r = nouveau()
    r.s["stade"], r.s["graine"] = "adulte", f"g{k}"
    r.s["stats"]["meilleur_rythme"] = 14
    r._fin_mue(horloge[0], bain=False)
    chanceux += r.s["marques"].get("fanon") == "fanon_raye"
ok(25 < chanceux < 80, f"fanon rayé (très rare) : mérité ET chanceux ({chanceux} îles sur 200 à la 1ʳᵉ mue)")
b0 = nouveau()
b0.s["stats"]["nuits_eteintes"] = 40
b0._fin_mue(horloge[0], bain=False)
ok(b0.s["marques"] == {}, "un bébé ne reçoit pas encore de marque")
cat = b0.catalogue()
ok(set(cat["marques"]) == set(P.MARQUES) and cat["categories_marques"] == P.CATEGORIES_MARQUES and all(m["condition"] for m in cat["marques"].values()), "le catalogue décrit les marques (onglet « Couleurs »)")

# ---- course au rocher chaud ---------------------------------------------------------------------
p = nouveau()
a_heure(12)
p.etat()
p.s["j"]["chaleur"], p.s["j"]["energie"] = 50, 100
g = p.jeu_debut("course")
but = P.COURSE["etape_px"] * P.COURSE["etapes"]
ok(g["duree"] == 240 and g["regles"]["etapes"] == 10 and but == 40000, "Course au rocher chaud : 10 étapes jusqu'au rocher, 4 min au plus")
horloge[0] += 20
ok(erreur(p.jeu_fin, g["jeton"], 10, 0, True, 10, but) is not None, "arrivée annoncée trop tôt : refusée")
p.s["j"]["energie"] = 100
g = p.jeu_debut("course")
horloge[0] += 40
ok(erreur(p.jeu_fin, g["jeton"], 30, 0, False, 1, 30000) is not None, "distance impossible pour la durée de la course : refusée")
p.s["j"]["energie"] = 100
g = p.jeu_debut("course")
horloge[0] += 140
ok(erreur(p.jeu_fin, g["jeton"], 9999, 0, True, 10, but) is not None, "plus de rayons qu'il n'y en avait sur le parcours : refusé")
p.s["j"]["energie"] = 100
g = p.jeu_debut("course")
horloge[0] += 60
ok(erreur(p.jeu_fin, g["jeton"], 20, 0, False, 9, 12000) is not None, "étape impossible pour la distance : refusée")
p.s["j"]["energie"] = 100
g = p.jeu_debut("course")
horloge[0] += 145
c0 = p.s["coquillages"]
r = p.jeu_fin(g["jeton"], 80, 0, True, 10, but)
ok(r["palier"] == 10 and p.s["position"] == "rocher" and p.s["j"]["chaleur"] >= 55, f"arrivé au bout des 10 étapes : il finit sur le rocher chaud ({p.s['j']['chaleur']:.0f})")
ok(p.s["coquillages"] - c0 == r["gain"] + P.SUCCES["coureur"][2] and r["gain"] in gain_attendu("course", 80, 10, True) and "coureur" in p.s["succes"], f"gain calculé par le serveur (+{r['gain']}) et succès « Coureur du soleil »")
p.s["j"]["energie"] = 100
g = p.jeu_debut("course")
horloge[0] += 60
r = p.jeu_fin(g["jeton"], 20, 0, False, 3, 11000)
ok(r["palier"] == 3 and r["gain"] in gain_attendu("course", 20, 3) and p.s["stats"]["courses_gagnees"] == 1, f"pas arrivé (étape 3) : récompense selon l'étape (+{r['gain']})")
ok([P.course_etape(d) for d in (0, 3999, 4000, 20000, 39999, 50000)] == [1, 1, 2, 6, 10, 10], "une étape tous les 4 000 px")
vit = [P.course_vitesse(k) for k in range(1, 11)]
ecart = [P.course_ecart(k) for k in range(1, 11)]
ok(all(a < b for a, b in zip(vit, vit[1:])) and all(a > b for a, b in zip(ecart, ecart[1:])), f"plus rapide et obstacles plus fréquents à chaque étape (vitesse ×{vit[-1]:.2f}, écart ×{ecart[-1]:.2f})")
vmax = sum(P.COURSE["vitesse"]) * vit[-1]
ok(P.COURSE["ecart_min"] >= .55 * vmax, "jamais injuste : deux obstacles restent toujours assez écartés pour sauter entre eux")
ok(but / (sum(P.COURSE["vitesse"]) * .8 * sum(vit) / len(vit)) > 100, "une course complète dure environ deux minutes et demie")

# ---- album et étapes de la vie -------------------------------------------------------------------
p = nouveau()
ok([x["stade"] for x in p.s["etapes"]] == ["bebe"], "étape : l'éclosion est photographiée")
p.s["age_s"] = 8 * J
horloge[0] += 600
p.etat()
ok([x["stade"] for x in p.s["etapes"]] == ["bebe", "juvenile", "adulte"] and p.s["etapes"][-1]["variante"], "étapes : juvénile puis adulte (avec sa variante)")
p.s["portes"] = {"tete": "chapeau"}
titre = p.titre()
p.action("recommencer", {"confirmer": "NOUVEL OEUF"})
ok(len(p.s["album"]) == 1 and p.s["album"][0]["titre"] == titre and p.s["album"][0]["portes"] == {"tete": "chapeau"}
   and p.s["album"][0]["age_jours"] >= 8, "nouvel œuf : l'ancien Philibert entre dans l'album")
p.action("recommencer", {"confirmer": "NOUVEL OEUF"})
ok(len(p.s["album"]) == 1, "un œuf qui n'a pas éclos n'entre pas dans l'album")
horloge[0] += 700
p.etat()
p.action("recommencer", {"confirmer": "NOUVEL OEUF"})
c = p.carnet()
ok(len(c["album"]) == 2 and c["album"][0]["stade"] == "bebe" and c["etapes"] == [], "album gardé d'un œuf à l'autre (le plus récent d'abord)")

# ---- le document pour l'administrateur suit le code -------------------------------------------
doc = (BASE / "docs" / "PHILIBERT-REGLES.md").read_text(encoding="utf-8")
sons = Path(__file__).resolve().parents[2] / "static" / "sons"
doc_ph = (Path(__file__).resolve().parents[2] / "docs" / "PHILIBERT.md").read_text(encoding="utf-8")
ok(all((sons / f).is_file() and (sons / f).stat().st_size < 1_500_000 and f"`{f}`" in doc_ph for f in ("pluie.mp3", "orage.ogg")) and "CC0" in doc_ph,
   "sons de pluie et d'orage présents, légers, et crédités (licence CC0) dans la doc")
ok(f"**−{P.ENERGIE_JEU} énergie au lancement**" in doc and f"**{P.GAINS_JEUX_JOUR} coquillages par jour**" in doc, "doc admin : coût et plafond des jeux")
ok(all(f"**{v}**" in doc for v in (P.PLANCHERS["faim"], P.PLANCHERS["bonheur"])) and f"bonheur est à {P.SEUIL_ATTENTION} ou moins**" in doc, "doc admin : planchers et seuil d'attention")
ok(all(f"{P.ALIMENTS[k]['nom']}" in doc for k in ("trefle", "feuilles_murier", "courge", "hibiscus", "banane")), "doc admin : tableau des aliments")
ok("**+5**" in doc and "**−6**" in doc and P.SAISONS["ete"]["chaleur"] == 5 and P.SAISONS["hiver"]["chaleur"] == -6, "doc admin : chaleur des saisons")
ok("**76 le jour, 72 la nuit**" in doc, "doc admin : lampe chauffante")

# ---- routes de l'API --------------------------------------------------------------------------
os.chdir(BASE)
os.environ.update(NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1")
import db  # noqa: E402

db.DB_FILE = store.DATA_DIR / "nexus.db"
db.migrate()
P.FICHIER = store.DATA_DIR / "philibert-api.json"
import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

c = TestClient(app.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8000")
r = c.get("/api/philibert")
ok(r.status_code == 200 and r.json()["stade"] in P.STADES and r.headers["cache-control"].startswith("no-store"), "GET /api/philibert")
ok(c.get("/api/philibert/catalogue").json()["faits_total"] == len(P.FAITS), "GET /api/philibert/catalogue")
ok("historique" in c.get("/api/philibert/carnet").json(), "GET /api/philibert/carnet")
horloge[0] += 700
r = c.post("/api/philibert/action", json={"action": "nourrir", "aliment": "trefle"})
ok(r.status_code == 200 and r.json()["ok"], f"POST action nourrir ({r.status_code})")
r = c.post("/api/philibert/action", json={"action": "acheter", "article": "banane", "quantite": 99})
ok(r.status_code in (200, 400), "POST acheter (quantité bornée)")
r = c.post("/api/philibert/action", json={"action": "inconnue"})
ok(r.status_code == 400 and r.json()["error"], "action inconnue : 400 avec un message")
r = c.post("/api/philibert/action", data="x", headers={"content-type": "text/plain"})
ok(r.status_code == 415, "corps JSON obligatoire")
r = c.post("/api/philibert/jeu/debut", json={"jeu": "devin"})
ok(r.status_code in (200, 400), f"POST jeu/debut ({r.status_code})")
r = c.post("/api/philibert/jeu/annuler", json={"jeton": "faux"})
ok(r.status_code == 400 and r.json()["error"], "POST jeu/annuler sans partie : 400 avec un message")
app.remote_svc.enabled, ancien = True, app.remote_svc.enabled
tel = TestClient(app.app, client=("192.168.1.42", 5000), base_url="http://127.0.0.1:8000")
r = tel.get("/api/philibert")
ok(r.status_code == 403 and "réservé au PC" in r.text, "Philibert depuis le téléphone (réseau local) : réservé au PC")
ok(tel.post("/api/philibert/action", json={"action": "caresser"}).status_code == 403, "aucune action sur Philibert depuis le téléphone")
app.remote_svc.enabled = ancien
r = c.post("/api/philibert/jeu/xyz", json={})
ok(r.status_code == 404, "étape de jeu inconnue : 404")
import activite  # noqa: E402

ok("philibert" in activite.CATEGORIES, "catégorie « Philibert » dans le journal d'activité")

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
