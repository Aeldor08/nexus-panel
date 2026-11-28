"""Envoi automatique des évènements NEXUS dans Google Agenda (agenda_google.envoyer_evenements_nexus), avec le faux
Google (faux_google.py) : contenu envoyé (heure, journée entière, répétition et exceptions, rappels, note,
anniversaires), retrait de NEXUS, aucun doublon (envoi interrompu au milieu, relancé, modifié entre-temps),
évènements « NEXUS seulement » gardés, coupure réseau, refus de Google, agenda en lecture seule, réglage désactivé.
Usage : python outils/tests/test_agenda_google_envoi.py <dossier de NEXUS>"""

import datetime as dt
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
os.chdir(BASE)
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
TMP = Path(tempfile.mkdtemp(prefix="nexus-google-envoi-")).resolve()

import faux_google

SRV, FG = faux_google.serveur()
os.environ.update(NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1", NEXUS_DATA_DIR=str(TMP), NEXUS_OPEN_BROWSER="0", **faux_google.env(SRV.server_address[1]))

import agenda
import agenda_google as G
import identifiants
import paths

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  ÉCHEC", m, flush=True)


assert paths.USER_ROOT == TMP and identifiants._keyring() is identifiants.MEMOIRE  # jamais les vraies données
CAL = "moi@exemple.fr"
J = dt.date.today()
jour = lambda n: (J + dt.timedelta(days=n)).isoformat()  # noqa: E731


def google(titre: str) -> list[dict]:
    """Évènements (séries comprises, pas leurs exceptions) de ce titre dans le faux Google."""
    return [e for e in FG.events[CAL].values() if e.get("summary") == titre and not e.get("recurringEventId") and e.get("status") != "cancelled"]


def locaux() -> dict:
    return {e["title"]: e for e in agenda.load()["events"]}


def occs(n=40) -> list[dict]:
    return G.occurrences(J - dt.timedelta(days=10), J + dt.timedelta(days=n))


# =========================================================================== évènements créés AVANT la liaison
print("--- avant la liaison")
dentiste = agenda.create({"title": "Dentiste", "date": jour(3), "time": "10:30", "duration": 45, "description": "Dr Martin", "reminders": [1440, 10]})
yoga = agenda.create({"title": "Yoga", "date": jour(-7), "time": "18:00", "duration": 60, "repeat": "weekly"})
agenda.delete(yoga["id"], jour(0), "one")  # une occurrence annulée
agenda.update(yoga["id"], {"title": "Yoga (salle 2)", "time": "19:00"}, jour(7), "one")  # une occurrence modifiée
lea = agenda.create({"title": "Léa", "date": jour(5), "birthday": True, "birth_year": 2000, "reminders": [1440]})
vac = agenda.create({"title": "Vacances", "date": jour(10), "duration": 3 * 1440})
appel = agenda.create({"title": "Appel banque", "date": jour(2), "time": "09:00"})  # rappels par défaut de NEXUS
garde = agenda.create({"title": "Journal intime", "date": jour(1), "time": "21:00"}, seulement_nexus=True)
ok(garde.get("seulement_nexus") and not dentiste.get("seulement_nexus"), "choix « NEXUS seulement » noté sur l'évènement")
ok(G.comptes_locaux() == {"a_envoyer": 5, "seulement_nexus": 1}, f"5 à envoyer, 1 gardé ({G.comptes_locaux()})")

G.enregistrer_client(faux_google.CLIENT_ID, faux_google.CLIENT_SECRET)
ok(G.reglages()["envoi_auto"] is True, "envoi automatique activé par défaut")
with urllib.request.urlopen(G.demarrer_connexion(), timeout=10) as r:
    r.read()
ok(G.connecte(), "relié au faux Google")

# =========================================================================== premier envoi
print("--- envoi")
e = G.synchroniser()
ok(not e["erreur"], f"pas d'erreur ({e['erreur']})")
ok(set(locaux()) == {"Journal intime"}, f"envoyés puis retirés de NEXUS ; « NEXUS seulement » gardé ({set(locaux())})")
ok(e["envoi"] and e["envoi"]["envoyes"] == 5 and e["envoi"]["message"] == "5 évènements NEXUS envoyés dans Google Agenda", f"résultat affiché ({e['envoi']})")
ok(e["a_envoyer"] == 0 and e["seulement_nexus"] == 1, "plus rien à envoyer")
ok(G.court()["envoi"]["envoyes"] == 5, "résultat aussi dans la ligne Google de l'Agenda")
d = google("Dentiste")
ok(len(d) == 1 and d[0]["id"] == G.id_envoi(CAL, dentiste["id"]), "Dentiste : une seule fois, identifiant calculé")
ok(d and d[0]["description"] == "Dr Martin" and d[0]["extendedProperties"]["private"]["nexus_id"] == dentiste["id"], "note et trace de l'évènement NEXUS")
ok(
    d and d[0]["reminders"] == {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}, {"method": "popup", "minutes": 1440}]},
    "rappels personnalisés",
)
a = google("Appel banque")
ok(a and sorted(o["minutes"] for o in a[0]["reminders"]["overrides"]) == [30, 60], "rappels par défaut de NEXUS envoyés tels quels (1 h, 30 min)")
la = google("Léa")
ok(la and la[0]["start"] == {"date": jour(5)} and la[0]["recurrence"] == ["RRULE:FREQ=YEARLY"], "anniversaire : journée entière, chaque année")
ok(
    la and la[0]["extendedProperties"]["private"].get("nexus_anniversaire") == "1" and la[0]["extendedProperties"]["private"].get("nexus_annee") == "2000",
    "marqueur nexus_anniversaire gardé",
)
ok(la and la[0]["reminders"]["overrides"] == [{"method": "popup", "minutes": 1440 - 540}], "rappel « 1 jour avant à 9 h » : 900 min avant minuit chez Google")
v = google("Vacances")
ok(v and v[0]["start"] == {"date": jour(10)} and v[0]["end"] == {"date": jour(13)}, "journée entière sur 3 jours")
y = google("Yoga")
ok(y and y[0]["recurrence"] == ["RRULE:FREQ=WEEKLY"], "série hebdomadaire")
vus = {o["date"]: o for o in occs() if o["event_id"] == "g:" + G.id_envoi(CAL, yoga["id"])}
ok(jour(0) not in vus and jour(-7) in vus, "occurrence annulée dans NEXUS : annulée chez Google")
ok(
    vus.get(jour(7), {}).get("title") == "Yoga (salle 2)" and vus.get(jour(7), {}).get("time") == "19:00",
    "occurrence modifiée dans NEXUS : modifiée chez Google",
)
o = [o for o in occs() if o["title"] == "Léa"]
ok(
    o and o[0]["birthday"] and o[0]["age"] == J.year + (1 if jour(5)[:4] != str(J.year) else 0) - 2000 and o[0]["reminders"] == [1440],
    "Léa relue : anniversaire, âge, rappel identique",
)
envois = json.loads(G.ENVOIS_FILE.read_text(encoding="utf-8"))
ok(len(envois) == 5 and all(v["google_id"].startswith("ag") for v in envois.values()), "trace de chaque envoi")
n_google = len(FG.events[CAL])
G.synchroniser()
ok(len(FG.events[CAL]) == n_google, "relecture suivante : rien de renvoyé")

# =========================================================================== jamais de doublon
print("--- interruptions")
b1 = agenda.create({"title": "Interrompu 1", "date": jour(4), "time": "08:00"})
vrai_retirer = agenda.retirer_envoye


def plantage(*a, **k):
    raise RuntimeError("NEXUS fermé en plein envoi")


agenda.retirer_envoye = plantage
try:
    G.synchroniser()
except RuntimeError:
    pass
agenda.retirer_envoye = vrai_retirer
ok(len(google("Interrompu 1")) == 1 and "Interrompu 1" in locaux(), "arrêt après l'envoi : chez Google ET encore dans NEXUS")
G.synchroniser()
ok(len(google("Interrompu 1")) == 1 and "Interrompu 1" not in locaux(), "reprise : retiré de NEXUS, toujours une seule fois chez Google")

b2 = agenda.create({"title": "Interrompu 2", "date": jour(4), "time": "09:00"})
vrai_noter = G._noter_envoi
G._noter_envoi = plantage
try:
    G.synchroniser()
except RuntimeError:
    pass
G._noter_envoi = vrai_noter
ok(len(google("Interrompu 2")) == 1 and "Interrompu 2" in locaux(), "arrêt avant même la trace : chez Google, encore dans NEXUS")
agenda.update(b2["id"], {"title": "Interrompu 2 (corrigé)"})  # modifié dans NEXUS entre-temps
G.synchroniser()
ok(
    not google("Interrompu 2") and len(google("Interrompu 2 (corrigé)")) == 1 and not [t for t in locaux() if t.startswith("Interrompu")],
    "reprise : Google refuse le doublon (409), mis à jour avec la modification",
)

# =========================================================================== réseau coupé, refus
print("--- réseau coupé, refus")
for i in range(3):
    agenda.create({"title": f"Hors ligne {i}", "date": jour(6), "time": f"1{i}:00"})
FG.ecritures_avant_coupure = 1
e = G.synchroniser()
FG.ecritures_avant_coupure = None
ok("interrompu" in e["erreur"] and "Nouvel essai" in e["erreur"] and G.court()["erreur"] == e["erreur"], f"erreur dans la ligne Google ({e['erreur']})")
restent = sorted(t for t in locaux() if t.startswith("Hors ligne"))
ok(restent == ["Hors ligne 1", "Hors ligne 2"] and len(google("Hors ligne 0")) == 1, f"le premier est parti, les autres restent dans NEXUS ({restent})")
e = G.synchroniser()
ok(
    not e["erreur"] and not [t for t in locaux() if t.startswith("Hors ligne")] and all(len(google(f"Hors ligne {i}")) == 1 for i in range(3)),
    "réseau revenu : envoyés, une fois chacun",
)

FG.refuser_titre = "Refusé"
agenda.create({"title": "Refusé par Google", "date": jour(6)})
agenda.create({"title": "Accepté", "date": jour(6)})
e = G.synchroniser()
FG.refuser_titre = ""
ok("Refusé par Google" in locaux() and "Accepté" not in locaux() and google("Accepté"), "un refus de Google n'arrête pas les autres envois")
ok("refusé" in e["erreur"] and "Refusé par Google" in e["erreur"], f"refus signalé ({e['erreur']})")
G.synchroniser()
ok(len(google("Refusé par Google")) == 1 and "Refusé par Google" not in locaux(), "accepté au nouvel essai")

# =========================================================================== lecture seule, réglage désactivé
print("--- lecture seule, désactivé")
agenda.create({"title": "Pour la famille", "date": jour(8)})
G.modifier_reglages({"agenda": "famille@exemple.fr"})
e = G.synchroniser()
ok(
    "Pour la famille" in locaux() and "lecture seule" in e["erreur"] and "lecture seule" in e["envoi"]["message"],
    f"agenda en lecture seule : rien n'est envoyé ({e['erreur']})",
)
ok(not FG.events["famille@exemple.fr"], "rien dans l'agenda en lecture seule")
G.modifier_reglages({"agenda": "primary", "envoi_auto": False})
e = G.synchroniser()
ok("Pour la famille" in locaux() and not e["envoi_auto"], "envoi automatique désactivé : l'évènement reste dans NEXUS")
G.modifier_reglages({"envoi_auto": True})
G.synchroniser()
ok("Pour la famille" not in locaux() and len(google("Pour la famille")) == 1, "réactivé : envoyé")
ok(set(locaux()) == {"Journal intime"}, "à la fin, seul l'évènement « NEXUS seulement » reste local")

# =========================================================================== routes
print("--- routes")
from fastapi.testclient import TestClient

import app

pc = TestClient(app.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8000")
r = pc.post("/api/agenda/evenements", json={"champs": {"title": "Choix NEXUS", "date": jour(2)}, "agenda": "nexus"}).json()
ok(r["ok"] and r["evenement"].get("seulement_nexus") is True, "formulaire « NEXUS (sur ce PC seulement) » : marqué")
r = pc.post("/api/agenda/evenements", json={"champs": {"title": "Sans choix", "date": jour(2)}}).json()
ok(r["ok"] and not r["evenement"].get("seulement_nexus"), "sans choix (Google pas relié) : sera envoyé")
r = pc.get(f"/api/agenda?debut={jour(0)}&fin={jour(5)}").json()
ok(any(o["title"] == "Choix NEXUS" and o["seulement_nexus"] for o in r["occurrences"]), "occurrence marquée « NEXUS seulement » pour la vue")
ok(pc.post("/api/agenda/google/reglages", json={"envoi_auto": False}).json()["envoi_auto"] is False, "réglage par la route (PC)")
pc.post("/api/agenda/google/reglages", json={"envoi_auto": True})
r = pc.post("/api/agenda/synchroniser", json={}).json()
ok(
    r["google"]["envoi"]["envoyes"] == 1 and "Sans choix" not in locaux() and "Choix NEXUS" in locaux(),
    "relire maintenant : envoie « Sans choix », garde « Choix NEXUS »",
)

G.arreter()
SRV.shutdown()
print(f"\n{passed} vérifications passées, {failed} en échec")
sys.exit(1 if failed else 0)
