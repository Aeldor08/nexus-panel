"""Liaison de l'Agenda avec Google Agenda (agenda_google.py), sans compte Google ni réseau : faux Google local
(faux_google.py : OAuth + API Calendar), dossier de données temporaire, secrets en mémoire (jamais dans le vrai
gestionnaire d'identifiants de Windows). Couvre : identifiant client, connexion OAuth (PKCE, state), relecture,
conversions (répétitions, journée entière, rappels, anniversaires), création / modification / suppression
(une occurrence, les suivantes, toute la série), lecture seule, rappels de NEXUS, routes du panel, garde PC.
Usage : python outils/tests/test_agenda_google.py <dossier de NEXUS>"""

import datetime as dt
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
os.chdir(BASE)
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
TMP = Path(tempfile.mkdtemp(prefix="nexus-google-")).resolve()

import faux_google

SRV, FG = faux_google.serveur()
PORT = SRV.server_address[1]
os.environ.update(NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1", NEXUS_DATA_DIR=str(TMP), NEXUS_OPEN_BROWSER="0", **faux_google.env(PORT))

import agenda
import agenda_google as G
import config
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


def erreur(f, *a, **k) -> str:
    try:
        f(*a, **k)
    except agenda.AgendaError as exc:
        return str(exc)
    return ""


assert paths.USER_ROOT == TMP, paths.USER_ROOT  # jamais les vraies données
assert identifiants._keyring() is identifiants.MEMOIRE  # jamais le vrai gestionnaire de Windows
CAL = "moi@exemple.fr"
J = dt.date.today()
iso = lambda d, h, m=0: faux_google._iso(dt.datetime.combine(d, dt.time(h, m)))  # noqa: E731
config_txt = lambda: config.CONFIG_FILE.read_text(encoding="utf-8") if config.CONFIG_FILE.exists() else ""  # noqa: E731

# =========================================================================== identifiant client
print("--- identifiant client")
ok(not G.configure() and not G.connecte() and G.occurrences(J, J) == [], "au départ : rien de relié, aucune occurrence")
ok("googleusercontent" in erreur(G.enregistrer_client, "pas-un-identifiant", "secret-assez-long"), "identifiant client invalide refusé")
ok("secret" in erreur(G.enregistrer_client, faux_google.CLIENT_ID, ""), "code secret obligatoire la première fois")
e = G.enregistrer_client(faux_google.CLIENT_ID, faux_google.CLIENT_SECRET)
ok(e["configure"] and not e["connecte"] and e["secret_range"] == "windows", f"client enregistré, secret dans le gestionnaire ({e['secret_range']})")
ok(faux_google.CLIENT_SECRET not in config_txt() and faux_google.CLIENT_ID in config_txt(), "secret jamais dans config.json (identifiant oui)")
ok(faux_google.CLIENT_SECRET not in json.dumps(G.etat()), "état du panel : jamais le secret")
ok("connecte" in G.court() and not G.court()["connecte"], "vue Agenda : pas relié")

# =========================================================================== connexion OAuth
print("--- connexion")
url = G.demarrer_connexion()
ok(url.startswith(f"http://127.0.0.1:{PORT}/auth?") and "code_challenge=" in url and "access_type=offline" in url, "adresse de connexion (PKCE, accès durable)")
ok(G.etat()["connexion"]["etat"] == "attente", "connexion en attente")
q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
retour = q["redirect_uri"]
ok(retour.startswith("http://127.0.0.1:") and retour.endswith("/"), f"retour sur 127.0.0.1 ({retour})")
try:
    urllib.request.urlopen(retour + "?code=x&state=mauvais", timeout=5)
    mauvais = 200
except urllib.error.HTTPError as exc:
    mauvais = exc.code
ok(mauvais == 400 and not G.connecte(), "réponse avec un mauvais « state » : refusée")
with urllib.request.urlopen(url, timeout=10) as r:  # le faux Google redirige vers NEXUS, comme le vrai
    page = r.read().decode("utf-8")
ok("relié" in page and G.connecte(), "connexion acceptée : NEXUS est relié")
ok(G.etat()["jeton_range"] == "windows" and "rafraichir-" not in config_txt(), "jeton de Google dans le gestionnaire, pas dans config.json")
try:
    urllib.request.urlopen(retour + "?" + urllib.parse.urlencode({"code": "y", "state": q["state"]}), timeout=3)
    rejoue = "accepté"
except urllib.error.HTTPError:
    rejoue = "refusé"
except OSError:
    rejoue = "fermé"
ok(rejoue in ("refusé", "fermé"), f"serveur de retour à usage unique ({rejoue})")

# =========================================================================== relecture
print("--- relecture et conversions")
d2, d5 = J + dt.timedelta(days=2), J + dt.timedelta(days=5)
FG.ajouter(
    CAL,
    {
        "id": "unique",
        "summary": "Dentiste",
        "description": "Dr <b>Martin</b><br>2e étage",
        "start": {"dateTime": iso(d2, 10)},
        "end": {"dateTime": iso(d2, 10, 45)},
        "attendees": [{"email": "ami@exemple.fr"}],
        "location": "Lyon",
    },
)
FG.ajouter(CAL, {"id": "vacances", "summary": "Vacances", "start": {"date": d5.isoformat()}, "end": {"date": (d5 + dt.timedelta(days=3)).isoformat()}})
FG.ajouter(
    CAL,
    {
        "id": "jour",
        "summary": "Fête du village",
        "start": {"date": d2.isoformat()},
        "end": {"date": (d2 + dt.timedelta(days=1)).isoformat()},
        "reminders": {"useDefault": False, "overrides": []},
    },
)
jr = faux_google.JOURS[J.weekday()]
FG.ajouter(
    CAL,
    {
        "id": "sport",
        "summary": "Sport",
        "start": {"dateTime": iso(J, 18), "timeZone": "Europe/Paris"},
        "end": {"dateTime": iso(J, 19), "timeZone": "Europe/Paris"},
        "recurrence": [f"RRULE:FREQ=WEEKLY;BYDAY={jr}"],
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}, {"method": "email", "minutes": 1440}]},
    },
)
FG.ajouter(
    CAL,
    {
        "id": "piscine",
        "summary": "Piscine",
        "start": {"dateTime": iso(J, 12), "timeZone": "Europe/Paris"},
        "end": {"dateTime": iso(J, 13), "timeZone": "Europe/Paris"},
        "recurrence": ["RRULE:FREQ=WEEKLY;INTERVAL=2"],
    },
)
FG.ajouter(
    CAL, {"id": "invit", "summary": "Réunion", "start": {"dateTime": iso(d2, 14)}, "end": {"dateTime": iso(d2, 15)}, "organizer": {"email": "chef@exemple.fr"}}
)
FG.ajouter(
    CAL,
    {
        "id": "anniv",
        "summary": "Anniversaire de Léa",
        "eventType": "birthday",
        "start": {"date": d5.isoformat()},
        "end": {"date": (d5 + dt.timedelta(days=1)).isoformat()},
        "recurrence": ["RRULE:FREQ=YEARLY"],
    },
)
e = G.synchroniser()
ok(not e["erreur"] and e["agenda_nom"] == "Agenda de test" and e["fuseau"] == "Europe/Paris", f"relecture réussie ({e['erreur']})")
occ = {o["id"]: o for o in G.occurrences(J, J + dt.timedelta(days=30))}
u = occ.get("g:unique") or {}
ok(
    u.get("time") == "10:00" and u.get("duration") == 45 and u.get("date") == d2.isoformat() and u.get("source") == "google",
    f"évènement avec heure et durée ({u})",
)
ok(u.get("description") == "Dr Martin\n2e étage", f"description HTML de Google -> texte ({u.get('description')!r})")
ok(u.get("reminders") is None and u.get("rappels_effectifs") == [15], "rappels par défaut de l'agenda Google")
ok(u.get("lien", "").startswith("https://calendar.google.com/") and not u.get("lecture_seule"), "lien vers Google Agenda, modifiable")
v = occ.get("g:vacances") or {}
ok(v.get("time") is None and v.get("duration") == 3 * 1440, f"journée entière sur 3 jours ({v.get('duration')})")
ok((occ.get("g:jour") or {}).get("duration") is None and (occ.get("g:jour") or {}).get("reminders") == [], "journée entière d'un jour, sans rappel")
sports = sorted((o for o in occ.values() if o["event_id"] == "g:sport"), key=lambda o: o["date"])
ok(len(sports) >= 4 and all(o["repeat"] == "weekly" and o["time"] == "18:00" for o in sports), f"série hebdomadaire traduite ({len(sports)} occurrences)")
ok(sports and sports[0]["reminders"] == [1440, 30] and sports[0]["series_start"] == J.isoformat(), "rappels personnalisés et début de série")
pis = [o for o in occ.values() if o["event_id"] == "g:piscine"]
ok(pis and all(o["repeat"] == "custom" for o in pis) and len(pis) <= 3, f"« toutes les 2 semaines » : répétition personnalisée ({len(pis)})")
ok((occ.get("g:invit") or {}).get("lecture_seule") is True, "invitation (pas l'organisateur) : lecture seule")
an = [o for o in occ.values() if o["event_id"] == "g:anniv"]
ok(an and an[0]["birthday"] and an[0]["lecture_seule"], "anniversaire d'un contact Google : affiché, lecture seule")
ok(G.CACHE_FILE.exists() and G.etat()["nb_evenements"] == len(G._lire_cache()["occurrences"]), "copie locale enregistrée")
loin = J + dt.timedelta(days=G.FENETRE_APRES + 30)
FG.ajouter(CAL, {"id": "loin", "summary": "Très loin", "start": {"date": loin.isoformat()}, "end": {"date": (loin + dt.timedelta(days=1)).isoformat()}})
ok([o["title"] for o in G.occurrences(loin, loin)] == ["Très loin"], "hors de la copie : période lue à la demande")

# =========================================================================== conversions pures
print("--- répétitions")
ok(G.repetition(G.rrule("monthly", dt.date(2027, 1, 31), None, False), dt.date(2027, 1, 31)) == ("monthly", None), "le 31 de chaque mois : aller-retour")
ok(
    G.repetition(G.rrule("yearly", dt.date(2028, 2, 29), "2035-03-01", True), dt.date(2028, 2, 29)) == ("yearly", "2035-03-01"),
    "29 février, jusqu'au : aller-retour",
)
ok(G.repetition(["RRULE:FREQ=DAILY;COUNT=5"], J) == ("custom", None), "COUNT : répétition personnalisée")
ok(G.repetition(["RRULE:FREQ=WEEKLY;BYDAY=MO,TH"], dt.date(2026, 11, 30))[0] == "custom", "plusieurs jours par semaine : personnalisée")
ok(G.repetition(["RRULE:FREQ=DAILY", "EXDATE:20261201"], J)[0] == "daily", "EXDATE (occurrences supprimées) : la série reste simple")
ok(
    G._until_avant(["RRULE:FREQ=DAILY;COUNT=9"], dt.date(2026, 12, 10), True) == ["RRULE:FREQ=DAILY;UNTIL=20261209"],
    "couper une série : COUNT -> UNTIL la veille",
)

# =========================================================================== créer
print("--- créer depuis NEXUS")
n_avant = len(FG.events[CAL])
r = G.creer({"title": "Rendez-vous banque", "date": d5.isoformat(), "time": "09:30", "duration": None, "reminders": [10], "description": "apporter le RIB"})
cree = FG.events[CAL].get(r["id"][2:]) or {}
ok(len(FG.events[CAL]) == n_avant + 1 and cree.get("summary") == "Rendez-vous banque", "évènement créé dans Google")
ok(
    cree.get("start", {}).get("timeZone") == "Europe/Paris"
    and cree.get("reminders") == {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]},
    "fuseau de l'agenda et rappel envoyés",
)
o = next((o for o in G.occurrences(d5, d5) if o["id"] == r["id"]), {})
ok(o.get("time") == "09:30" and o.get("duration") is None and o.get("reminders") == [10], f"relu tel quel (sans durée) ({o})")
r2 = G.creer(
    {
        "title": "Loyer",
        "date": dt.date(J.year, J.month, 1).isoformat() if J.day == 1 else (J + dt.timedelta(days=1)).isoformat(),
        "repeat": "monthly",
        "reminders": None,
    }
)
ok(FG.events[CAL][r2["id"][2:]].get("recurrence", [""])[0].startswith("RRULE:FREQ=MONTHLY"), "série mensuelle créée")
r3 = G.creer({"title": "Léo", "date": d2.isoformat(), "birthday": True, "birth_year": 2015})
o3 = next((o for o in G.occurrences(d2, d2) if o["id"].startswith(r3["id"])), {})
ok(
    o3.get("birthday") and o3.get("age") == d2.year - 2015 and o3.get("repeat") == "yearly" and not o3.get("lecture_seule"),
    f"anniversaire NEXUS gardé dans Google ({o3.get('age')})",
)
ok("titre" in erreur(G.creer, {"title": "", "date": d2.isoformat()}).lower(), "mêmes vérifications que l'Agenda de NEXUS")

# =========================================================================== modifier / supprimer
print("--- modifier et supprimer")
FG.journal.clear()
G.modifier(
    "g:unique",
    {
        "title": "Dentiste (Dr Martin)",
        "date": d2.isoformat(),
        "time": "10:00",
        "duration": 45,
        "description": "Dr Martin\n2e étage",
        "repeat": "none",
        "until": None,
        "birthday": False,
        "reminders": None,
    },
)
patchs = [c for m, ch, c in FG.journal if m == "PATCH"]
ok(patchs == [{"summary": "Dentiste (Dr Martin)"}], f"seul le titre est envoyé ({patchs})")
ok(FG.events[CAL]["unique"].get("attendees") and FG.events[CAL]["unique"].get("location") == "Lyon", "invités et lieu jamais effacés")
G.modifier("g:unique", {"time": "11:15", "duration": 30})
u = FG.events[CAL]["unique"]
ok(
    faux_google._local(u["start"]["dateTime"]).strftime("%H:%M") == "11:15" and faux_google._local(u["end"]["dateTime"]).strftime("%H:%M") == "11:45",
    "heure et durée changées",
)
ok("seulement dans Google Agenda" in erreur(G.modifier, "g:invit", {"title": "x"}), "invitation : modification refusée")
ok(erreur(G.supprimer, "g:anniv") != "", "anniversaire d'un contact : suppression refusée")

s1 = sports[1]
G.modifier("g:sport", {"title": "Sport (salle B)", "time": "19:00"}, s1["original_date"], "one")
occ = {o["id"]: o for o in G.occurrences(J, J + dt.timedelta(days=30))}
sp = sorted((o for o in occ.values() if o["event_id"] == "g:sport"), key=lambda o: o["date"])
ok(sp[1]["title"] == "Sport (salle B)" and sp[1]["time"] == "19:00" and sp[1]["exception"], "cette occurrence seulement")
ok(sp[0]["title"] == "Sport" and sp[2]["title"] == "Sport", "les autres occurrences ne bougent pas")
ok("seule occurrence" in erreur(G.modifier, "g:sport", {"repeat": "daily"}, s1["original_date"], "one"), "répétition non modifiable pour une occurrence")

G.modifier("g:sport", {"title": "Sport du soir", "date": sp[0]["date"], "time": "18:30", "repeat": "weekly"}, sp[0]["original_date"], "all")
m = FG.events[CAL]["sport"]
ok(
    m["summary"] == "Sport du soir"
    and faux_google._local(m["start"]["dateTime"]).strftime("%H:%M") == "18:30"
    and m["recurrence"][0].startswith("RRULE:FREQ=WEEKLY"),
    "toute la série",
)
ok(m["reminders"]["overrides"][1]["method"] == "email", "rappel par e-mail de Google gardé (rappels non modifiés)")

sp = sorted((o for o in G.occurrences(J, J + dt.timedelta(days=60)) if o["event_id"] == "g:sport"), key=lambda o: o["date"])
coupe = sp[2]
G.modifier("g:sport", {"title": "Sport (nouveau club)", "date": coupe["date"], "time": "20:00", "repeat": "weekly"}, coupe["original_date"], "following")
occ = sorted(G.occurrences(J, J + dt.timedelta(days=60)), key=lambda o: o["date"])
anciens = [o for o in occ if o["event_id"] == "g:sport"]
nouveaux = [o for o in occ if o["title"] == "Sport (nouveau club)"]
ok(anciens and max(o["date"] for o in anciens) < coupe["date"], "les suivantes : l'ancienne série s'arrête la veille")
ok(
    nouveaux and nouveaux[0]["date"] == coupe["date"] and all(o["time"] == "20:00" and o["repeat"] == "weekly" for o in nouveaux),
    "… et une nouvelle série commence à cette date",
)
dates = [o["date"] for o in anciens + nouveaux]
ok(len(dates) == len(set(dates)) and set(dates) == {o["date"] for o in sp}, "mêmes dates qu'avant, aucune en double")
nid = nouveaux[0]["event_id"]

G.supprimer(nid, nouveaux[1]["original_date"], "one")
reste = [o for o in G.occurrences(J, J + dt.timedelta(days=60)) if o["event_id"] == nid]
ok(len(reste) == len(nouveaux) - 1 and nouveaux[1]["date"] not in {o["date"] for o in reste}, "supprimer cette occurrence seulement")
G.supprimer(nid, reste[2]["original_date"], "following")
reste2 = [o for o in G.occurrences(J, J + dt.timedelta(days=60)) if o["event_id"] == nid]
ok(len(reste2) == 2, f"supprimer cette occurrence et les suivantes ({len(reste2)})")
G.supprimer(nid)
ok(not [o for o in G.occurrences(J, J + dt.timedelta(days=60)) if o["event_id"] == nid] and nid[2:] not in FG.events[CAL], "supprimer toute la série")
G.modifier("g:piscine", {"title": "Piscine municipale", "repeat": "custom"}, pis[0]["original_date"], "all")
ok(
    FG.events[CAL]["piscine"]["recurrence"] == ["RRULE:FREQ=WEEKLY;INTERVAL=2"] and FG.events[CAL]["piscine"]["summary"] == "Piscine municipale",
    "répétition personnalisée gardée telle quelle",
)
G.supprimer("g:unique")
ok("unique" not in FG.events[CAL] and "introuvable" in erreur(G.modifier, "g:unique", {"title": "x"}).lower(), "supprimé dans Google ; puis introuvable")

# =========================================================================== rappels de NEXUS
print("--- rappels")
dans = dt.datetime.now().replace(second=0, microsecond=0) + dt.timedelta(minutes=20)
r = G.creer({"title": "Appel important", "date": dans.date().isoformat(), "time": dans.strftime("%H:%M"), "duration": 15, "reminders": [10]})
svc = reminders.ReminderService()
envoyes = svc.tick(dans - dt.timedelta(minutes=10, seconds=-5))
ok(any(f["occurrence"] == r["id"] and f["delai"] == 10 for f in envoyes), f"rappel 10 min avant un évènement Google ({[f['titre'] for f in envoyes]})")
G.modifier_reglages({"rappels": False})
svc2 = reminders.ReminderService()
svc2.state = {"seen": {}, "sent": {}, "fired": [], "discord": {}}
ok(not [f for f in svc2.tick(dans - dt.timedelta(minutes=10, seconds=-5)) if f["occurrence"].startswith("g:")], "rappels Google désactivés dans ⚙ Réglages")
G.modifier_reglages({"rappels": True})

# =========================================================================== routes du panel et garde
print("--- routes")
from fastapi.testclient import TestClient

import app

pc = TestClient(app.app, client=("127.0.0.1", 5000), base_url="http://127.0.0.1:8000")
tel = TestClient(app.app, client=("192.168.1.50", 5000), base_url="http://127.0.0.1:8000")
r = pc.get(f"/api/agenda?debut={J}&fin={J + dt.timedelta(days=30)}").json()
ok(
    r["google"]["connecte"] and any(o.get("source") == "google" for o in r["occurrences"]) and "custom" in r["repetitions"],
    "/api/agenda : occurrences Google mêlées aux autres",
)
ok([o["date"] for o in r["occurrences"]] == sorted(o["date"] for o in r["occurrences"]), "occurrences triées")
ok(faux_google.CLIENT_SECRET not in json.dumps(r) and "rafraichir-" not in json.dumps(r), "jamais de secret dans /api/agenda")
r = pc.post("/api/agenda/evenements", json={"champs": {"title": "Par l'API", "date": d2.isoformat(), "time": "08:00"}, "agenda": "google"}).json()
ok(r.get("ok") and r["evenement"]["id"].startswith("g:"), "création dans Google par la route du panel")
gid = r["evenement"]["id"]
r = pc.post(f"/api/agenda/evenements/{gid}/modifier", json={"champs": {"title": "Par l'API (modifié)"}}).json()
ok(r.get("ok") and FG.events[CAL][gid[2:]]["summary"] == "Par l'API (modifié)", "modification par la route (identifiant g:…)")
r = pc.post("/api/agenda/evenements", json={"champs": {"title": "Local", "date": d2.isoformat()}}).json()
ok(r.get("ok") and not r["evenement"]["id"].startswith("g:") and len(agenda.load()["events"]) == 1, "sans « agenda » : évènement NEXUS, comme avant")
ok(pc.post(f"/api/agenda/evenements/{gid}/supprimer", json={}).json().get("ok") and gid[2:] not in FG.events[CAL], "suppression par la route")
r = pc.post("/api/agenda/evenements/g:invit/modifier", json={"champs": {"title": "x"}})
ok(r.status_code == 400 and "error" in r.json(), "erreur lisible (400) pour un évènement en lecture seule")
ok(pc.get("/api/agenda/google").status_code == 200 and tel.get("/api/agenda/google").status_code in (401, 403), "réglages Google : réservés au PC")
ok(
    pc.get("/api/agenda/google/agendas").json()["agendas"][0]["id"] == CAL and len(pc.get("/api/agenda/google/agendas").json()["agendas"]) == 1,
    "liste des agendas où écrire",
)
ok(pc.post("/api/agenda/synchroniser", json={}).json()["google"]["connecte"], "relire maintenant")

# agenda en lecture seule
G.modifier_reglages({"agenda": "famille@exemple.fr"})
G.synchroniser()
ok(G.court()["lecture_seule"] and "lecture seule" in erreur(G.creer, {"title": "x", "date": d2.isoformat()}), "agenda en lecture seule : création refusée")
G.modifier_reglages({"agenda": "primary"})
G.synchroniser()

# API désactivée dans le projet Google Cloud
FG.refuser_api = True
ok("API Google Calendar n'est pas activée" in G.synchroniser()["erreur"], "API non activée : message clair")
FG.refuser_api = False
ok(not G.synchroniser()["erreur"], "erreur effacée à la relecture suivante")

# =========================================================================== jeton révoqué, déconnexion
print("--- jeton révoqué, déconnexion")
FG.refresh.clear()
FG.acces.clear()
G._acces.update(jeton="", expire=0)
e = G.synchroniser()
ok("reconnecte-toi" in e["erreur"] and not G.connecte(), f"jeton révoqué chez Google : reconnexion demandée ({e['erreur']})")
url = G.demarrer_connexion()
with urllib.request.urlopen(url, timeout=10) as r:
    r.read()
ok(G.connecte(), "reconnexion")
G.deconnecter()
ok(not G.connecte() and not G.CACHE_FILE.exists() and G.occurrences(J, J + dt.timedelta(days=30)) == [], "déconnexion : jeton et copie oubliés")
ok(G.configure(), "… l'identifiant client reste (reconnexion en un clic)")
G.enregistrer_client("", "")
ok(not G.configure() and not identifiants.MEMOIRE.valeurs and "client_secret" not in config_txt(), "effacer l'identifiant client : plus aucun secret")

G.arreter()
SRV.shutdown()
print(f"\n{passed} vérifications passées, {failed} en échec")
sys.exit(1 if failed else 0)
