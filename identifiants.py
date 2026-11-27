"""Secrets de NEXUS dans le gestionnaire d'identifiants de Windows (bibliothèque keyring).

Utilisé pour le jeton GitHub des mises à jour (maj.py), le jeton du bot Discord (config.py) et la liaison
avec Google Agenda (agenda_google.py : secret du client OAuth et jeton de rafraîchissement).
Si le gestionnaire est indisponible (keyring absent, session sans profil…), les fonctions renvoient
None / False : l'appelant garde alors le secret dans config.json (exclu de Git), comme avant.
Les valeurs ne sont jamais écrites dans les journaux.
Tests et copies isolées : NEXUS_IDENTIFIANTS=memoire range tout en mémoire (jamais dans le vrai gestionnaire de Windows).
"""

from __future__ import annotations

import os

SERVICE_MAJ = "NEXUS-panel-mises-a-jour"  # clé : propriétaire/dépôt
SERVICE_DISCORD = "NEXUS-panel-discord"  # clé : CLE_JETON_BOT
CLE_JETON_BOT = "jeton-bot"
SERVICE_GOOGLE = "NEXUS-panel-google-agenda"  # clés : CLE_SECRET_GOOGLE, CLE_JETON_GOOGLE
CLE_SECRET_GOOGLE = "secret-client"
CLE_JETON_GOOGLE = "jeton-rafraichissement"


class _Memoire:
    """Gestionnaire d'identifiants en mémoire (NEXUS_IDENTIFIANTS=memoire) : rien n'est écrit sur le disque."""

    def __init__(self) -> None:
        self.valeurs: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, cle: str) -> str | None:
        return self.valeurs.get((service, cle))

    def set_password(self, service: str, cle: str, valeur: str) -> None:
        self.valeurs[(service, cle)] = valeur

    def delete_password(self, service: str, cle: str) -> None:
        self.valeurs.pop((service, cle), None)


MEMOIRE = _Memoire()


def _keyring():
    if os.environ.get("NEXUS_IDENTIFIANTS", "").strip().lower() == "memoire":
        return MEMOIRE
    try:
        import keyring

        return keyring
    except Exception:  # (paquet absent ou dorsal introuvable : repli sur config.json)
        return None


def disponible() -> bool:
    return _keyring() is not None


def lire(service: str, cle: str) -> str | None:
    kr = _keyring()
    if not kr or not cle:
        return None
    try:
        return kr.get_password(service, cle) or None
    except Exception as exc:
        print(f"[Identifiants] lecture impossible ({type(exc).__name__}) : {service}")
        return None


def ecrire(service: str, cle: str, valeur: str) -> bool:
    """Range la valeur ; renvoie False si le gestionnaire est indisponible (l'appelant garde le repli)."""
    kr = _keyring()
    if not kr or not cle:
        return False
    try:
        kr.set_password(service, cle, valeur)
        return True
    except Exception as exc:
        print(f"[Identifiants] gestionnaire de Windows indisponible ({type(exc).__name__}) : {service}")
        return False


def supprimer(service: str, cle: str) -> None:
    kr = _keyring()
    if not kr or not cle:
        return
    try:
        kr.delete_password(service, cle)
    except Exception:
        pass  # (déjà absent : rien à faire)
