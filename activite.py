"""Journal d'activité des actions sensibles, consultable dans le panel (fenêtre « Santé de NEXUS »).

Catégories : deck (boutons, connexions, édition), maj (installation, retour, jeton, réglages), appareil
(appairage du téléphone, appareil refusé ou retiré), processus (fermeture), focus (sessions Pomodoro),
philibert (éclosion, évolutions, vétérinaire, vacances de l'iguane), agenda (liaison Google Agenda, évènements
Google créés ou supprimés depuis NEXUS).
Une ligne JSON par évènement dans data/activite.jsonl (données personnelles : hors Git, jamais partagé).
Jamais de secret dans le journal : ni mot de passe, ni jeton, ni contenu privé.
"""

from __future__ import annotations

import json
import threading
import time

import store

FICHIER = store.DATA_DIR / "activite.jsonl"
MAX_LIGNES, GARDER = 3000, 2000  # au-delà de 3000 lignes, on garde les 2000 plus récentes
CATEGORIES = {
    "deck": "Deck",
    "maj": "Mises à jour",
    "appareil": "Appareils",
    "processus": "Processus",
    "focus": "Focus",
    "philibert": "Philibert",
    "systeme": "Démarrage de Windows",
    "agenda": "Agenda",
}
_lock = threading.Lock()
_n = None  # nombre de lignes (compté à la première écriture)
_vus: dict[str, float] = {}  # anti-répétition (ex. un appareil non appairé qui réessaie en boucle)


def noter(categorie: str, action: str, resultat: str = "ok", detail: str = "", ip: str = "", source: str = "web", unique_s: float = 0) -> None:
    """Ajoute un évènement. Ne lève jamais d'exception (le journal ne doit rien casser).
    unique_s : ignore le même évènement (catégorie, action, ip) répété dans ce délai."""
    global _n
    try:
        now = time.time()
        if unique_s:
            cle = f"{categorie}|{action}|{ip}"
            if now - _vus.get(cle, 0) < unique_s:
                return
            _vus[cle] = now
        ligne = json.dumps(
            {
                "t": round(now, 1),
                "cat": categorie if categorie in CATEGORIES else "deck",
                "action": str(action)[:80],
                "resultat": str(resultat)[:20],
                "detail": str(detail)[:240],
                "ip": str(ip or "")[:45],
                "source": str(source or "")[:12],
            },
            ensure_ascii=False,
        )
        with _lock:
            FICHIER.parent.mkdir(parents=True, exist_ok=True)
            if _n is None:
                try:
                    with open(FICHIER, encoding="utf-8") as f:
                        _n = sum(1 for _ in f)
                except OSError:
                    _n = 0
            with open(FICHIER, "a", encoding="utf-8") as f:
                f.write(ligne + "\n")
            _n += 1
            if _n > MAX_LIGNES:
                lignes = FICHIER.read_text(encoding="utf-8").splitlines()[-GARDER:]
                tmp = FICHIER.with_suffix(".tmp")
                tmp.write_text("\n".join(lignes) + "\n", encoding="utf-8")
                tmp.replace(FICHIER)
                _n = len(lignes)
    except Exception:
        pass


def lire(n: int = 200, categorie: str | None = None) -> list[dict]:
    """Évènements les plus récents d'abord (catégorie facultative)."""
    try:
        lignes = FICHIER.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for ligne in reversed(lignes):
        try:
            e = json.loads(ligne)
        except ValueError:
            continue
        if categorie and e.get("cat") != categorie:
            continue
        out.append(e)
        if len(out) >= n:
            break
    return out
