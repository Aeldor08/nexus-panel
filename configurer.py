"""Assistant de première configuration de NEXUS (lancé par installer.bat, lancer.bat ou configurer.bat).

Pose quelques questions dans la console et crée config.json :
  1. le mot de passe du stream deck (obligatoire) — seule son EMPREINTE est enregistrée, jamais le mot de passe ;
  2. le bot Discord (facultatif) : jeton du bot, ton ID utilisateur et l'ID du salon ;
  3. le dépôt GitHub dont les nouvelles versions sont surveillées (facultatif).
Il crée aussi deck.json à partir de deck.example.json s'il n'existe pas.

Tes réponses restent dans le dossier de NEXUS (config.json, jamais partagé).
Utilisation : python configurer.py        (ou double-clic sur configurer.bat)
"""

from __future__ import annotations

import getpass
import json
import re
import secrets
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG_FILE = BASE / "config.json"
DECK_FILE, DECK_EXAMPLE = BASE / "deck.json", BASE / "deck.example.json"

sys.path.insert(0, str(BASE))
from config import DEFAULTS          # noqa: E402  (valeurs par défaut : seuils d'alerte…)
from deck import hash_password       # noqa: E402

INTERACTIVE = sys.stdin.isatty()
ID_RE = re.compile(r"^\d{15,22}$")                     # les ID Discord sont des nombres de 17 à 20 chiffres
TOKEN_RE = re.compile(r"^[\w-]{20,}\.[\w-]{4,}\.[\w-]{20,}$")


def ask(prompt: str, default: str = "") -> str:
    try:
        value = input(prompt).strip()
    except EOFError:
        value = ""
    return value or default


def ask_secret(prompt: str) -> str:
    """Saisie masquée dans une vraie console (rien ne s'affiche quand on tape : c'est normal)."""
    if not INTERACTIVE:
        return ask(prompt)
    try:
        return getpass.getpass(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise
    except Exception:
        return ask(prompt)


def yes(prompt: str, default: bool = False) -> bool:
    suffix = " [O/n] " if default else " [o/N] "
    answer = ask(prompt + suffix).lower()
    return default if not answer else answer in ("o", "oui", "y", "yes")


def title(text: str) -> None:
    print("\n" + "=" * 64 + f"\n  {text}\n" + "=" * 64)


def step_password() -> str:
    title("1/3  MOT DE PASSE DU STREAM DECK")
    print("Le stream deck (onglet « Deck ») peut lancer des applis, verrouiller ou mettre le PC en veille.")
    print("Il est donc protégé par un mot de passe, demandé une fois par navigateur.")
    print("Au moins 6 caractères. Rien ne s'affiche quand tu tapes : c'est normal.")
    print("Laisse vide et appuie sur Entrée pour qu'un mot de passe soit choisi pour toi.\n")
    for _ in range(5):
        pw = ask_secret("Mot de passe : ")
        if not pw:
            pw = "nx-" + secrets.token_urlsafe(9)
            print(f"\n  Mot de passe choisi pour toi :  {pw}")
            print("  Note-le maintenant : il ne sera plus jamais affiché (seule une empreinte est enregistrée).")
            ask("  Appuie sur Entrée quand c'est noté… ")
            return pw
        if len(pw) < 6:
            print("  Trop court (6 caractères minimum). Recommence.\n")
            continue
        if ask_secret("Confirme le mot de passe : ") != pw:
            print("  Les deux saisies sont différentes. Recommence.\n")
            continue
        return pw
    raise SystemExit("Trop d'essais : relance configurer.bat quand tu veux.")


def ask_id(prompt: str) -> str:
    while True:
        v = ask(prompt).replace(" ", "")
        if not v or ID_RE.match(v):
            return v
        print("  Ce n'est pas un ID Discord (un nombre d'environ 18 chiffres). Laisse vide pour passer.")


def step_discord() -> dict:
    title("2/3  BOT DISCORD (FACULTATIF)")
    print("Le bot répond à /stats, /gpu, /disques… et envoie des alertes (température, disque plein).")
    print("Il faut d'abord créer un bot sur https://discord.com/developers/applications (voir README, étape 6).")
    if not yes("Veux-tu configurer le bot Discord maintenant ?"):
        print("  OK, pas de bot. Tu pourras le faire plus tard avec configurer.bat.")
        return {"enabled": False, "token": "", "user_id": "", "alert_channel_id": ""}

    token = ""
    while True:
        token = ask_secret("Jeton du bot (Bot → Reset Token → Copy ; vide pour passer) : ")
        if not token or TOKEN_RE.match(token):
            break
        print("  Ce jeton n'a pas le bon format (trois morceaux séparés par des points). Recommence ou laisse vide.")
    print("\nPour copier un ID : Discord → Paramètres → Avancés → active « Mode développeur »,")
    print("puis clic droit sur ton profil (ou sur le salon) → « Copier l'identifiant ».")
    user_id = ask_id("Ton ID utilisateur Discord (seul ce compte pourra utiliser les commandes) : ")
    channel_id = ask_id("ID du salon des alertes (les commandes ne répondront que là) : ")

    enabled = bool(token and user_id and channel_id)
    if enabled:
        print("  Bot Discord configuré.")
    else:
        missing = [n for n, v in (("le jeton", token), ("ton ID", user_id), ("l'ID du salon", channel_id)) if not v]
        print(f"  Il manque {', '.join(missing)} : le bot restera éteint (NEXUS fonctionne sans).")
        print("  Relance configurer.bat quand tu auras tout.")
    return {"enabled": enabled, "token": token, "user_id": user_id, "alert_channel_id": channel_id}


DEPOT_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")


def step_updates(previous: dict | None) -> str:
    """Dépôt GitHub dont les releases sont surveillées (proposé : celui d'où vient cette copie, fichier DEPOT)."""
    title("3/3  MISES À JOUR (FACULTATIF)")
    actuel = str(((previous or {}).get("mises_a_jour") or {}).get("depot") or "")
    if not actuel and (BASE / "DEPOT").is_file():
        actuel = (BASE / "DEPOT").read_text(encoding="utf-8").strip()
    print("NEXUS peut vérifier tout seul si une nouvelle version est publiée sur GitHub (rien ne s'installe sans toi).")
    print("Dépôt privé : il faudra aussi un jeton en lecture seule (voir docs\\JETON_GITHUB.md, dans les Réglages).")
    while True:
        v = ask(f"Dépôt à surveiller, propriétaire/nom{f' [{actuel}]' if actuel else ''} (« non » pour aucun) : ", actuel)
        v = v.strip().removeprefix("https://github.com/").strip("/")
        if v.lower() in ("non", "-", ""):
            print("  Pas de vérification des mises à jour (réglable plus tard : ⚙ Réglages).")
            return ""
        if DEPOT_RE.match(v):
            print(f"  Dépôt surveillé : {v}")
            return v
        print("  Format attendu : propriétaire/nom (ex. mon-pseudo/nexus-panel).")


def build_config(password: str, discord: dict, previous: dict | None = None, depot: str | None = None) -> dict:
    previous = previous or {}
    alerts = {**DEFAULTS["alerts"], **(previous.get("alerts") or {})}       # garde les seuils déjà réglés
    deck = {"password_hash": hash_password(password), "password": "",
            "rate_limit_per_minute": (previous.get("deck") or {}).get("rate_limit_per_minute",
                                                                       DEFAULTS["deck"]["rate_limit_per_minute"])}
    agenda_cfg = {**DEFAULTS["agenda"], **(previous.get("agenda") or {})}  # garde les réglages des rappels
    journal_cfg = {**DEFAULTS["journal"], **(previous.get("journal") or {})}  # garde les activités choisies
    cfg = dict(previous)                     # garde aussi les autres sections (mises à jour, numéro de schéma…)
    cfg.update({"discord": discord, "alerts": alerts, "agenda": agenda_cfg, "journal": journal_cfg, "deck": deck})
    if depot is not None:
        cfg["mises_a_jour"] = {**DEFAULTS["mises_a_jour"], **(previous.get("mises_a_jour") or {}), "depot": depot}
        if not cfg["mises_a_jour"].get("jeton"):
            cfg["mises_a_jour"].pop("jeton", None)
    return cfg


def write_config(cfg: dict) -> None:
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CONFIG_FILE)


def main() -> int:
    print("\nNEXUS — assistant de configuration")
    print("Tout reste sur ce PC : tes réponses ne sont envoyées nulle part.")
    previous = None
    if CONFIG_FILE.exists():
        try:
            previous = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = None
        if not yes("\nUne configuration existe déjà. La remplacer ?"):
            print("Rien n'a été modifié.")
            return 0

    password = step_password()
    discord = step_discord()
    depot = step_updates(previous)
    write_config(build_config(password, discord, previous, depot))

    if not DECK_FILE.exists() and DECK_EXAMPLE.exists():
        shutil.copyfile(DECK_EXAMPLE, DECK_FILE)
        print("\nBoutons du deck d'exemple créés (deck.json) : tu pourras les modifier dans l'onglet Deck.")

    title("CONFIGURATION TERMINÉE")
    print(f"Fichier créé : {CONFIG_FILE.name} (il contient tes secrets : ne le partage jamais).")
    print("Pour tout changer plus tard : double-clic sur configurer.bat.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nConfiguration annulée : rien n'a été modifié.")
        sys.exit(1)
