"""Mur de souvenirs : calcul des dispositions (sans base de données ni fichiers, donc facile à tester).

Le mur est une toile de LARGEUR unités logiques : la même disposition s'affiche à l'identique sur le PC et,
réduite à l'échelle, sur le téléphone. Chaque élément (photo « p:<id> » ou note « n:<id> ») a une position
x, y, une largeur, une hauteur et un ordre d'empilement z.
"""

from __future__ import annotations

LARGEUR = 1000                     # largeur logique du mur
MARGE, ECART, COLONNES = 20, 20, 4
LEGENDE = 44                       # place sous une photo (légende + boutons)
MIN_W, MAX_W, MIN_H, MAX_H = 120, LARGEUR, 90, 1400
CELLULE = (LARGEUR - 2 * MARGE - (COLONNES - 1) * ECART) / COLONNES
NOTE_H = 200


def taille_photo(largeur: int | None, hauteur: int | None) -> tuple[float, float]:
    w, h = (largeur or 4), (hauteur or 3)
    img = min(max(CELLULE * h / w, 120), 360)
    return CELLULE, round(img + LEGENDE)


def borne(e: dict) -> dict:
    """Ramène une position dans les limites (taille mini / maxi, dans la largeur du mur)."""
    w = min(max(float(e.get("w") or CELLULE), MIN_W), MAX_W)
    h = min(max(float(e.get("h") or NOTE_H), MIN_H), MAX_H)
    x = min(max(float(e.get("x") or 0), 0), LARGEUR - w)
    y = min(max(float(e.get("y") or 0), 0), 20000)
    z = int(min(max(int(e.get("z") or 1), 1), 100000))
    return {"x": round(x, 1), "y": round(y, 1), "w": round(w, 1), "h": round(h, 1), "z": z}


def grille(elements: list[tuple[str, float, float]], debut_y: float = MARGE, z0: int = 1) -> dict[str, dict]:
    """Disposition automatique propre : colonnes de même largeur, chaque élément dans la colonne la plus courte.
    elements : (id, largeur, hauteur) dans l'ordre voulu."""
    bas = [debut_y] * COLONNES
    out = {}
    for i, (eid, _w, h) in enumerate(elements):
        c = min(range(COLONNES), key=lambda k: (bas[k], k))
        out[eid] = borne({"x": MARGE + c * (CELLULE + ECART), "y": bas[c], "w": CELLULE, "h": h, "z": z0 + i})
        bas[c] += h + ECART
    return out


def bas_du_mur(dispo: dict[str, dict]) -> float:
    return max((e["y"] + e["h"] for e in dispo.values()), default=0)
