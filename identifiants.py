"""Secrets de NEXUS dans le gestionnaire d'identifiants de Windows (bibliothèque keyring).

Utilisé pour le jeton GitHub des mises à jour (maj.py) et le jeton du bot Discord (config.py).
Si le gestionnaire est indisponible (keyring absent, session sans profil…), les fonctions renvoient
None / False : l'appelant garde alors le secret dans config.json (exclu de Git), comme avant.
Les valeurs ne sont jamais écrites dans les journaux.
"""

from __future__ import annotations

SERVICE_MAJ = "NEXUS-panel-mises-a-jour"  # clé : propriétaire/dépôt
SERVICE_DISCORD = "NEXUS-panel-discord"  # clé : CLE_JETON_BOT
CLE_JETON_BOT = "jeton-bot"


def _keyring():
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
