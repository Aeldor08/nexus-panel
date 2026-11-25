"""Configuration de NEXUS : fichier config.json à la racine (exclu de Git, voir .gitignore).

Contient les secrets (jeton du bot Discord, mot de passe du stream deck) et les seuils d'alerte.
Modèle : config.example.json. Si config.json est absent ou illisible, NEXUS démarre quand même
avec les valeurs par défaut (bot et deck désactivés) et affiche un avertissement.
"""

from __future__ import annotations

import copy
import json

import paths

CONFIG_FILE = paths.CONFIG_FILE

DEFAULTS = {
    "discord": {
        "enabled": True,
        "token": "",                 # jeton du bot (Discord Developer Portal → Bot → Reset Token)
        "user_id": "",               # ton ID utilisateur : seul toi peux utiliser les commandes
        "alert_channel_id": "",      # salon des alertes (et le seul où les commandes répondent)
    },
    "alerts": {
        "cpu_temp": 85,              # °C
        "gpu_temp": 83,              # °C
        "ram_percent": 92,           # %
        "disk_percent": 95,          # % d'espace utilisé
        "cooldown_minutes": 30,      # une alerte par type au plus toutes les X minutes
        "check_seconds": 30,         # intervalle de vérification
    },
    "agenda": {
        "rappels_minutes": [60, 30],  # rappels par défaut : 1 h puis 30 min avant (modifiable par évènement)
        "heure_reference": "09:00",  # « début » des évènements sans heure et des anniversaires, pour les rappels
        "rappels_discord": True,     # envoyer aussi les rappels dans le salon Discord (si le bot est configuré)
    },
    "journal": {
        # émojis d'activité proposés chaque jour dans le Journal (modifiables)
        "activites": [{"emoji": "🎮", "nom": "Jeu"}, {"emoji": "🏃", "nom": "Sport"}, {"emoji": "📚", "nom": "Lecture"},
                      {"emoji": "🎵", "nom": "Musique"}, {"emoji": "👥", "nom": "Amis"}, {"emoji": "💼", "nom": "Travail"},
                      {"emoji": "🍳", "nom": "Cuisine"}, {"emoji": "🌳", "nom": "Dehors"}, {"emoji": "🎬", "nom": "Film"}],
    },
    "deck": {
        "password_hash": "",         # empreinte écrite par l'assistant (configurer.bat)
        "password": "",              # ou mot de passe en clair (anciennes configs) ; l'un des deux est obligatoire
        "rate_limit_per_minute": 30, # requêtes max par minute et par adresse
    },
    "mises_a_jour": {
        "depot": "",                 # dépôt GitHub à surveiller : « propriétaire/nom » (ex. mon-pseudo/nexus-panel)
        "actif": True,               # vérification automatique (au démarrage puis toutes les N heures)
        "intervalle_heures": 6,
        "discord": False,            # simple message « nouvelle version disponible » (le bot n'installe jamais rien)
        "jeton": "",                 # repli SEULEMENT si le gestionnaire d'identifiants de Windows est indisponible
        "signature": "auto",         # auto : vérifie si signé, accepte sinon ; requise : refuse un exe non signé
        "certificat": "",            # empreinte SHA1 du certificat attendu (vide = n'importe quel signataire valide)
    },
}

# Schéma de config.json : numéro + migrations (une sauvegarde de config.json est faite avant chacune)
CONFIG_VERSION = 1


def _migration_1(cfg: dict) -> dict:
    """1 : section « mises_a_jour » explicite (dépôt à surveiller, intervalle, Discord)."""
    sec = cfg.setdefault("mises_a_jour", {})
    depot = paths.DEPOT_FILE     # mis dans l'archive de release : dépôt d'origine
    if not sec.get("depot") and depot.is_file():
        sec["depot"] = depot.read_text(encoding="utf-8").strip()[:140]
    for k, v in DEFAULTS["mises_a_jour"].items():
        if k != "jeton":
            sec.setdefault(k, v)
    return cfg


MIGRATIONS = [(1, _migration_1)]

_cache: dict | None = None
_cache_mtime: float | None = None       # date de config.json au moment de la lecture
warnings: list[str] = []


def _merge(base: dict, user: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (user or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _merge(out[k], v)
        elif k in out:
            out[k] = v
    return out


def _mtime() -> float | None:
    try:
        return CONFIG_FILE.stat().st_mtime
    except OSError:
        return None


def load(force: bool = False) -> dict:
    """Configuration fusionnée (valeurs par défaut + config.json). Relue dès que config.json change sur le disque :
    « Configurer NEXUS » (un autre processus) prend effet sans redémarrer, ancien mot de passe compris."""
    global _cache, _cache_mtime
    mtime = _mtime()
    if _cache is not None and not force and mtime == _cache_mtime:
        return _cache
    _cache_mtime = mtime
    warnings.clear()
    user = {}
    if CONFIG_FILE.exists():
        try:
            user = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if not isinstance(user, dict):
                raise ValueError("le fichier doit contenir un objet JSON")
        except (OSError, ValueError) as exc:
            warnings.append(f"config.json illisible ({exc}) : valeurs par défaut utilisées")
            user = {}
    else:
        warnings.append("config.json absent : lance configurer.bat (sources) ou NEXUS.exe --configure "
                        "(raccourci « Configurer NEXUS ») pour définir le mot de passe du deck et le bot Discord")
    _cache = _merge(DEFAULTS, user)
    return _cache


def get(section: str) -> dict:
    return load()[section]


def migrer() -> int:
    """Applique les migrations manquantes de config.json (sauvegarde dans data/backups/ avant chacune).
    Renvoie le numéro de schéma. Sans config.json (installation neuve) : rien à migrer."""
    import time
    if not CONFIG_FILE.exists():
        return CONFIG_VERSION
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0                                    # illisible : load() le signale, on n'y touche pas
    cur = int(data.get("config_version") or 0)
    todo = [(v, f) for v, f in MIGRATIONS if v > cur]
    for v, f in todo:
        backups = paths.BACKUP_DIR
        backups.mkdir(parents=True, exist_ok=True)
        (backups / f"config-v{cur}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        data = f(data)
        data["config_version"] = cur = v
        tmp = CONFIG_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(CONFIG_FILE)
    if todo:
        load(force=True)
    return cur


def as_int(value) -> int | None:
    """Les ID Discord peuvent être écrits en texte ou en nombre dans le JSON."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None
