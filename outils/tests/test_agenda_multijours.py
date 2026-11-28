"""Évènements sur plusieurs jours dans l'Agenda : NEXUS (agenda.py) et Google Agenda (agenda_google.py, faux Google).
Chaque occurrence porte « fin » (dernier jour inclus) et « jours » ; elle est rendue pour toute période qui touche
l'un de ses jours, même si elle a commencé avant. Fin exclusive de Google (journée entière : end.date = lendemain
du dernier jour), fin à minuit pile, répétitions sur plusieurs jours, évènement plus long que la durée maximale du
formulaire, rappels envoyés une seule fois (au début), suppression depuis n'importe quel jour.
Usage : python outils/tests/test_agenda_multijours.py <dossier de NEXUS>"""

import datetime as dt
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
os.chdir(BASE)
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
TMP = Path(tempfile.mkdtemp(prefix="nexus-multijours-")).resolve()

import faux_google

SRV, FG = faux_google.serveur()
os.environ.update(NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1", NEXUS_DATA_DIR=str(TMP), NEXUS_OPEN_BROWSER="0", **faux_google.env(SRV.server_address[1]))

import agenda
import agenda_google as G
import identifiants
import paths
import reminders

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  ÉCHEC", m, flush=True)


assert paths.USER_ROOT == TMP and identifiants._keyring() is identifiants.MEMOIRE  # jamais les vraies données
D = dt.date.fromisoformat
J = dt.date.today()
# un vendredi dans 10 à 16 jours (dans la copie locale de Google, loin de « hier »)
VEN = J + dt.timedelta(days=10 + (4 - (J + dt.timedelta(days=10)).weekday()) % 7)
SAM, DIM, LUN = (VEN + dt.timedelta(days=i) for i in (1, 2, 3))


def occ_nexus(a, b=None) -> dict:
    return {o["title"]: o for o in agenda.occurrences(agenda.load(), a, b or a)}


# =========================================================================== dernier jour
print("--- dernier jour d'une occurrence")
f = agenda.fin_occurrence
ok(f("2026-12-01", None, 3 * 1440) == "2026-12-03", "journée entière sur 3 jours : du 1er au 3")
ok(f("2026-12-01", None, 100) == "2026-12-01" and f("2026-12-01", None, None) == "2026-12-01", "journée entière courte ou sans durée : 1 jour")
ok(f("2026-12-04", "20:00", 46 * 60) == "2026-12-06", "vendredi 20 h -> dimanche 18 h")
ok(f("2026-12-04", "22:00", 120) == "2026-12-04", "fin à minuit pile : un seul jour")
ok(f("2026-12-04", "22:00", 121) == "2026-12-05", "une minute après minuit : deux jours")
ok(f("2026-12-04", None, 5 * 1440, anniversaire=True) == "2026-12-04", "anniversaire : toujours un jour")

# =========================================================================== évènements NEXUS
print("--- évènements NEXUS")
we = agenda.create({"title": "Week-end ski", "date": VEN.isoformat(), "time": "20:00", "duration": 46 * 60, "reminders": [30]})
camp = agenda.create({"title": "Camp", "date": VEN.isoformat(), "duration": 3 * 1440})
mois = agenda.create({"title": "Week-end du mois", "date": SAM.isoformat(), "duration": 2 * 1440, "repeat": "monthly"})
for jour, attendu in (
    (VEN, {"Week-end ski", "Camp"}),
    (SAM, {"Week-end ski", "Camp", "Week-end du mois"}),
    (DIM, {"Week-end ski", "Camp", "Week-end du mois"}),
):
    vus = set(occ_nexus(jour))
    ok(vus == attendu, f"{jour:%a %d} : {sorted(vus)}")
ok(not occ_nexus(LUN).keys() & {"Week-end ski", "Camp", "Week-end du mois"}, "lundi : plus rien")
o = occ_nexus(DIM)["Week-end ski"]
ok(
    o["date"] == VEN.isoformat() and o["fin"] == DIM.isoformat() and o["jours"] == 3 and o["time"] == "20:00",
    f"une seule occurrence, datée de son début ({o['date']} -> {o['fin']})",
)
ok(occ_nexus(SAM)["Week-end du mois"]["jours"] == 2, "répétition sur 2 jours")
m2 = SAM.replace(day=1) + dt.timedelta(days=40)
m2 = dt.date(m2.year, m2.month, min(SAM.day, 28)) if SAM.day <= 28 else None
if m2:
    lendemain = m2 + dt.timedelta(days=1)
    seul = occ_nexus(lendemain).get("Week-end du mois")
    ok(
        seul and seul["date"] == m2.isoformat() and seul["fin"] == lendemain.isoformat(),
        "mois suivant : vue du 2e jour seulement, occurrence commencée la veille rendue",
    )
toutes = agenda.occurrences(agenda.load(), VEN, DIM)
ok(sum(1 for x in toutes if x["title"] == "Week-end ski") == 1, "sur toute la période : une seule fois (pas une par jour)")

# exception déplacée sur plusieurs jours, suppression depuis un autre jour que le premier
agenda.update(mois["id"], {"duration": 3 * 1440}, SAM.isoformat(), "one")
ok(occ_nexus(LUN).get("Week-end du mois", {}).get("jours") == 3, "une occurrence modifiée seule : 3 jours, visible le lundi")
o = occ_nexus(DIM)["Week-end du mois"]
agenda.delete(o["event_id"], o["original_date"], "one")  # (✕ depuis le dimanche : même occurrence)
ok("Week-end du mois" not in occ_nexus(SAM) and "Week-end du mois" not in occ_nexus(DIM), "supprimée depuis le dimanche : disparaît de tous ses jours")
agenda.delete(camp["id"])
ok("Camp" not in occ_nexus(SAM), "suppression de l'évènement entier")

# rappels : une seule fois, au début
print("--- rappels")
debut = dt.datetime.combine(VEN, dt.time(20, 0))
svc = reminders.ReminderService()
svc.state = {"seen": {}, "sent": {}, "fired": [], "discord": {}}
envoyes = []
for t in (
    debut - dt.timedelta(minutes=31),
    debut - dt.timedelta(minutes=29),
    debut + dt.timedelta(hours=5),
    debut + dt.timedelta(days=1),
    debut + dt.timedelta(days=1, hours=21),
):
    envoyes += [x for x in svc.tick(t) if "Week-end ski" in x["texte"]]
ok(len(envoyes) == 1 and envoyes[0]["delai"] == 30, f"Week-end ski : un seul rappel, 30 min avant le début ({len(envoyes)})")

# =========================================================================== Google Agenda
print("--- Google Agenda")
G.enregistrer_client(faux_google.CLIENT_ID, faux_google.CLIENT_SECRET)
G.modifier_reglages({"envoi_auto": False})  # (les évènements NEXUS ci-dessus restent locaux)
with urllib.request.urlopen(G.demarrer_connexion(), timeout=10) as r:
    r.read()
CAL = "moi@exemple.fr"
iso = lambda d, h, m=0: faux_google._iso(dt.datetime.combine(d, dt.time(h, m)))  # noqa: E731
FG.ajouter(CAL, {"id": "vacances", "summary": "Vacances", "start": {"date": VEN.isoformat()}, "end": {"date": LUN.isoformat()}})  # du ven. au dim. inclus
FG.ajouter(
    CAL,
    {
        "id": "festival",
        "summary": "Festival",
        "start": {"dateTime": iso(VEN, 20)},
        "end": {"dateTime": iso(DIM, 18)},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 60}]},
    },
)
FG.ajouter(CAL, {"id": "minuit", "summary": "Soirée", "start": {"dateTime": iso(VEN, 21)}, "end": {"dateTime": iso(SAM, 0)}})
FG.ajouter(
    CAL,
    {
        "id": "mensuel",
        "summary": "Rando du mois",
        "start": {"date": SAM.isoformat()},
        "end": {"date": LUN.isoformat()},
        "recurrence": ["RRULE:FREQ=MONTHLY;COUNT=3"],
    },
)
long_fin = VEN + dt.timedelta(days=20)
FG.ajouter(CAL, {"id": "long", "summary": "Chantier", "start": {"date": VEN.isoformat()}, "end": {"date": long_fin.isoformat()}})
e = G.synchroniser()
ok(not e["erreur"], f"relecture ({e['erreur']})")


def occ_g(a, b=None) -> dict:
    return {o["title"]: o for o in G.occurrences(a, b or a)}


v = occ_g(DIM).get("Vacances")
ok(
    v and v["date"] == VEN.isoformat() and v["fin"] == DIM.isoformat() and v["jours"] == 3,
    f"fin exclusive de Google : du ven. au dim. inclus ({v and v['fin']})",
)
ok("Vacances" not in occ_g(LUN), "lundi (end.date de Google) : plus affiché")
fe = occ_g(SAM).get("Festival")
ok(
    fe and fe["time"] == "20:00" and fe["fin"] == DIM.isoformat() and fe["jours"] == 3 and fe["duration"] == 46 * 60,
    "avec heure : vendredi 20 h -> dimanche 18 h",
)
so = occ_g(VEN).get("Soirée")
ok(so and so["jours"] == 1 and "Soirée" not in occ_g(SAM), "fin à minuit pile : un seul jour")
ra = [o for o in G.occurrences(J, J + dt.timedelta(days=120)) if o["title"] == "Rando du mois"]
ok(len(ra) == 3 and all(o["jours"] == 2 and D(o["fin"]) == D(o["date"]) + dt.timedelta(days=1) for o in ra), f"répétition mensuelle sur 2 jours ({len(ra)})")
if len(ra) > 1:
    dim2 = D(ra[1]["fin"])
    ok("Rando du mois" in occ_g(dim2) and occ_g(dim2)["Rando du mois"]["date"] == ra[1]["date"], "2e mois : visible le dimanche, occurrence du samedi")
ch = occ_g(long_fin - dt.timedelta(days=1)).get("Chantier")
ok(ch and ch["jours"] == 20 and ch["duration"] == agenda.MAX_DURATION_MIN, "plus long que la durée maxi du formulaire : affiché sur ses 20 jours")
ok(sum(1 for o in G.occurrences(VEN, DIM) if o["title"] == "Festival") == 1, "Google : une seule occurrence pour tout le week-end")
rap = [o for o in G.occurrences_rappels(VEN, DIM) if o["title"] == "Festival"]
ok(len(rap) == 1 and rap[0]["reminders"] == [60], "rappels Google : une occurrence, rappel au début seulement")
svc2 = reminders.ReminderService()
svc2.state = {"seen": {}, "sent": {}, "fired": [], "discord": {}}
envoyes = []
for t in (debut - dt.timedelta(minutes=61), debut - dt.timedelta(minutes=59), debut + dt.timedelta(days=1), debut + dt.timedelta(days=1, hours=22)):
    envoyes += [x for x in svc2.tick(t) if "Festival" in x["texte"]]
ok(len(envoyes) == 1, f"Festival : un seul rappel ({len(envoyes)})")

# modifier depuis le 2e jour : agit sur l'évènement entier
G.modifier("g:festival", {"title": "Festival de musique"})
ok(
    FG.events[CAL]["festival"]["summary"] == "Festival de musique" and "Festival de musique" in occ_g(DIM),
    "modifié (depuis n'importe quel jour) : tout l'évènement",
)
r = occ_g(dim2 if len(ra) > 1 else SAM)["Rando du mois"]
G.supprimer(r["event_id"], r["original_date"], "one")
ra2 = [o for o in G.occurrences(J, J + dt.timedelta(days=120)) if o["title"] == "Rando du mois"]
ok(len(ra2) == 2 and r["date"] not in {o["date"] for o in ra2}, "série Google : une occurrence supprimée depuis son 2e jour")

# =========================================================================== route du panel
print("--- route")
from fastapi.testclient import TestClient

import app

pc = TestClient(app.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8000")
r = pc.get(f"/api/agenda?debut={DIM}&fin={DIM}").json()
noms = {o["title"]: o for o in r["occurrences"]}
ok({"Week-end ski", "Vacances", "Festival de musique"} <= set(noms), f"/api/agenda sur le dimanche seul : évènements commencés vendredi ({sorted(noms)})")
ok(noms.get("Week-end ski", {}).get("jours") == 3 and noms.get("Vacances", {}).get("fin") == DIM.isoformat(), "« fin » et « jours » envoyés au navigateur")

G.arreter()
SRV.shutdown()
print(f"\n{passed} vérifications passées, {failed} en échec")
sys.exit(1 if failed else 0)
