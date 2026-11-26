"""Images de l'installeur Windows (Inno Setup 6.7, style sombre) aux couleurs de NEXUS.

Dessins originaux (logo hexagonal de static/nexus-logo.svg, dégradé cyan → magenta, nœuds jaunes), rendus avec
Pillow en suréchantillonnage ×4 puis réduits : nets à tous les zooms de Windows. Une image par zoom, aux tailles
exactes conseillées par Inno Setup (il choisit la plus proche) :
- grande image à gauche (pages Bienvenue et Fin), rapport 164:314 ;
- petit logo en haut à droite des autres pages, carré, fond transparent ;
- fond discret derrière les pages, rapport 497:360.

Usage : python outils/images_installeur.py   →   installeur/*.png (suivis par Git, lus par installer.iss)
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BASE = Path(__file__).resolve().parents[1]
SORTIE = BASE / "installeur"
SS = 4  # suréchantillonnage

CYAN = (0, 240, 255)
MAGENTA = (255, 43, 214)
JAUNE = (252, 238, 10)
FOND_HAUT, FOND_MILIEU, FOND_BAS = (6, 10, 22), (10, 16, 36), (20, 10, 36)

# Inno Setup 6.7 : tailles de la zone d'image selon le zoom (100 %, 125 %, 150 %, 175 %, 200 %, 250 %)
TAILLES_GAUCHE = [(202, 386), (269, 515), (336, 643), (403, 772), (430, 824), (534, 1022)]
TAILLES_LOGO = [58, 77, 97, 116, 124, 159]
TAILLES_FOND = [(596, 432), (796, 576), (994, 720), (1272, 922)]

POLICE = Path("C:/Windows/Fonts/bahnschrift.ttf")


# --------------------------------------------------------------------------- outils
def melange(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def degrade_vertical(w, h, arrets):
    """arrets : [(position 0..1, couleur), …]"""
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        t = y / max(1, h - 1)
        for (p0, c0), (p1, c1) in zip(arrets, arrets[1:]):
            if p0 <= t <= p1:
                px[0, y] = melange(c0, c1, (t - p0) / max(1e-9, p1 - p0))
                break
    return col.resize((w, h))


def degrade_diagonal(w, h, c0=CYAN, c1=MAGENTA):
    """Dégradé du logo (haut-gauche cyan → bas-droite magenta)."""
    petit = Image.new("RGB", (64, 64))
    px = petit.load()
    for y in range(64):
        for x in range(64):
            px[x, y] = melange(c0, c1, (x + y) / 126)
    return petit.resize((w, h), Image.BILINEAR)


def lueur(calque_masque, couleur, rayon, force):
    """Halo coloré à partir d'un masque (L)."""
    m = calque_masque.filter(ImageFilter.GaussianBlur(rayon))
    if force != 1:
        m = m.point(lambda v: min(255, int(v * force)))
    img = Image.new("RGBA", m.size, couleur + (0,))
    img.putalpha(m)
    return img


def halo_radial(w, h, cx, cy, r, couleur, alpha):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse((cx - r, cy - r, cx + r, cy + r), fill=alpha)
    m = m.filter(ImageFilter.GaussianBlur(r * 0.55))
    img = Image.new("RGBA", (w, h), couleur + (0,))
    img.putalpha(m)
    return img


def police(taille, gras=True):
    f = ImageFont.truetype(str(POLICE), max(6, int(taille)))
    try:
        f.set_variation_by_name("Bold" if gras else "SemiLight")
    except (OSError, ValueError):
        pass
    return f


def texte_espace(draw, xy, texte, f, fill, espace):
    """Texte avec espacement des lettres ; renvoie la largeur totale."""
    x, y = xy
    for ch in texte:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + espace
    return x - xy[0] - espace


def largeur_espace(f, texte, espace):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    return sum(d.textlength(ch, font=f) for ch in texte) + espace * (len(texte) - 1)


# --------------------------------------------------------------------------- logo (static/nexus-logo.svg)
EXT = [(60, 6), (107, 33), (107, 87), (60, 114), (13, 87), (13, 33)]
INT = [(60, 20), (95, 40), (95, 80), (60, 100), (25, 80), (25, 40)]
N = [(42, 80), (42, 40), (78, 80), (78, 40)]
PISTES = [((107, 33), (116, 28)), ((13, 87), (4, 92)), ((60, 6), (60, 1)), ((60, 114), (60, 119))]
NOEUDS = [(116, 28), (4, 92)]


def logo(taille):
    """Logo NEXUS (RGBA, fond transparent) de `taille` px de côté, avec sa lueur."""
    s = taille * SS
    k = s / 128  # viewBox 120 + marge pour la lueur
    off = 4 * k

    def P(pts):
        return [(off + x * k, off + y * k) for x, y in pts]

    trait = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(trait)
    d.line(P(EXT + EXT[:1]), fill=255, width=max(1, round(4 * k)), joint="curve")
    pts = P(INT + INT[:1])  # hexagone intérieur en pointillés
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        lg = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(lg / (9 * k)))
        for i in range(n):
            a, b = i / n, min(1, (i + 4 / 9) / n)
            d.line((x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b), fill=180, width=max(1, round(1.5 * k)))
    d.line(P(N), fill=255, width=max(1, round(8 * k)), joint="curve")

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.alpha_composite(lueur(trait, CYAN, 6 * k, 0.9))
    coul = degrade_diagonal(s, s).convert("RGBA")
    coul.putalpha(trait)
    img.alpha_composite(coul)

    pistes = Image.new("L", (s, s), 0)
    dp = ImageDraw.Draw(pistes)
    for a, b in PISTES:
        dp.line(P([a, b]), fill=230, width=max(1, round(2 * k)))
    c = Image.new("RGBA", (s, s), CYAN + (0,))
    c.putalpha(pistes)
    img.alpha_composite(c)
    dn = ImageDraw.Draw(img)
    for x, y in P(NOEUDS):
        r = 2.8 * k
        dn.ellipse((x - r, y - r, x + r, y + r), fill=JAUNE + (255,))
    return img.resize((taille, taille), Image.LANCZOS)


# --------------------------------------------------------------------------- décor
def grille_hex(w, h, pas, alpha, graine=7):
    """Trame d'hexagones très discrète (circuit), plus visible au centre."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    r = pas / math.sqrt(3)
    lig = 0
    centres = []
    y = -pas
    while y < h + pas:
        x = -pas if lig % 2 == 0 else -pas + pas / 2
        while x < w + pas:
            pts = [(x + r * math.cos(math.radians(60 * i + 30)), y + r * math.sin(math.radians(60 * i + 30))) for i in range(6)]
            d.line(pts + pts[:1], fill=alpha, width=max(1, SS))
            centres.append((x, y))
            x += pas
        y += 1.5 * r
        lig += 1
    rnd = random.Random(graine)  # quelques cellules de la trame allumées
    for cx, cy in rnd.sample(centres, max(1, len(centres) // 9)):
        rr = r * 0.82
        pts = [(cx + rr * math.cos(math.radians(60 * i + 30)), cy + rr * math.sin(math.radians(60 * i + 30))) for i in range(6)]
        d.line(pts + pts[:1], fill=min(255, int(alpha * 2.2)), width=max(1, SS))
    return m


def courbe(w, h, x0, y0, x1, y1, graine=3):
    """Petite courbe d'activité (comme les graphiques de NEXUS) : points de la ligne."""
    rnd = random.Random(graine)
    n = 22
    pts = []
    v = 0.55
    for i in range(n):
        v = min(0.92, max(0.12, v + rnd.uniform(-0.22, 0.22)))
        pts.append((x0 + (x1 - x0) * i / (n - 1), y1 - (y1 - y0) * v))
    return pts


# --------------------------------------------------------------------------- les trois images
def image_gauche(w0, h0):
    w, h = w0 * SS, h0 * SS
    img = degrade_vertical(w, h, [(0, FOND_HAUT), (0.55, FOND_MILIEU), (1, FOND_BAS)]).convert("RGBA")
    trame = grille_hex(w, h, w / 5.2, 11)
    fondu = degrade_vertical(1, h, [(0, (40, 40, 40)), (0.32, (255, 255, 255)), (0.7, (150, 150, 150)), (1, (30, 30, 30))]).convert("L").resize((w, h))
    trame = ImageChops.multiply(trame, fondu)
    t = Image.new("RGBA", (w, h), CYAN + (0,))
    t.putalpha(trame)
    img.alpha_composite(t)
    img.alpha_composite(halo_radial(w, h, w * 0.5, h * 0.30, w * 0.48, CYAN, 34))
    img.alpha_composite(halo_radial(w, h, w * 0.55, h * 1.04, w * 0.7, MAGENTA, 46))

    # logo
    lt = int(w * 0.64)
    lg = logo(max(8, int(w0 * 0.64))).resize((lt, lt), Image.LANCZOS)
    img.alpha_composite(lg, (int((w - lt) / 2), int(h * 0.30 - lt / 2)))

    # « NEXUS »
    d = ImageDraw.Draw(img, "RGBA")  # mode RGBA : les couleurs semi-transparentes se mélangent
    f = police(w * 0.2)
    esp = w * 0.035
    lw = largeur_espace(f, "NEXUS", esp)
    masque = Image.new("L", (w, h), 0)
    y_mot = h * 0.505
    texte_espace(ImageDraw.Draw(masque), ((w - lw) / 2, y_mot), "NEXUS", f, 255, esp)
    img.alpha_composite(lueur(masque, CYAN, w * 0.03, 0.55))
    horiz = Image.linear_gradient("L").rotate(90, expand=True).resize((w, h))
    coul = Image.composite(Image.new("RGBA", (w, h), MAGENTA + (255,)), Image.new("RGBA", (w, h), CYAN + (255,)), horiz)
    coul.putalpha(masque)
    img.alpha_composite(coul)

    # sous-titre
    fs = police(w * 0.052, gras=False)
    sous = "TABLEAU DE BORD DU PC"
    es = w * 0.012
    sw = largeur_espace(fs, sous, es)
    texte_espace(d, ((w - sw) / 2, h * 0.615), sous, fs, (150, 172, 205, 255), es)
    # filet sous le sous-titre
    d.line((w * 0.3, h * 0.66, w * 0.7, h * 0.66), fill=CYAN + (90,), width=SS)

    # courbe d'activité en bas
    x0, x1, y0, y1 = w * 0.1, w * 0.9, h * 0.74, h * 0.88
    for i in range(5):  # repères
        yy = y0 + (y1 - y0) * i / 4
        d.line((x0, yy, x1, yy), fill=(120, 140, 190, 14), width=max(1, SS // 2))
    pts = courbe(w, h, x0, y0, x1, y1)
    aire = Image.new("L", (w, h), 0)
    ImageDraw.Draw(aire).polygon(pts + [(x1, y1), (x0, y1)], fill=60)
    aire = ImageChops.multiply(aire, degrade_vertical(1, h, [(0, (255,) * 3), (0.74, (255,) * 3), (0.88, (0,) * 3), (1, (0,) * 3)]).convert("L").resize((w, h)))
    a = Image.new("RGBA", (w, h), CYAN + (0,))
    a.putalpha(aire)
    img.alpha_composite(a)
    ligne = Image.new("L", (w, h), 0)
    ImageDraw.Draw(ligne).line(pts, fill=255, width=max(1, int(w * 0.011)), joint="curve")
    img.alpha_composite(lueur(ligne, CYAN, w * 0.02, 0.8))
    lc = Image.new("RGBA", (w, h), CYAN + (255,))
    lc.putalpha(ligne)
    img.alpha_composite(lc)
    xd, yd = pts[-1]
    r = w * 0.016
    d.ellipse((xd - r, yd - r, xd + r, yd + r), fill=JAUNE + (255,))

    # filet néon sur le bord droit (sépare l'image de la page)
    filet = degrade_vertical(1, h, [(0, (0, 0, 0)), (0.2, CYAN), (0.8, MAGENTA), (1, (0, 0, 0))])
    fw = max(SS, int(w * 0.008))
    img.paste(filet.resize((fw, h)), (w - fw, 0))
    return img.convert("RGB").resize((w0, h0), Image.LANCZOS)


def image_fond(w0, h0):
    w, h = w0 * SS // 2, h0 * SS // 2  # fond flou : ×2 suffit
    img = degrade_vertical(w, h, [(0, (11, 15, 28)), (1, (13, 11, 26))]).convert("RGBA")
    trame = grille_hex(w, h, h / 6.5, 9, graine=11)
    t = Image.new("RGBA", (w, h), CYAN + (0,))
    t.putalpha(trame)
    img.alpha_composite(t)
    img.alpha_composite(halo_radial(w, h, w * 1.02, h * -0.05, h * 0.75, CYAN, 34))
    img.alpha_composite(halo_radial(w, h, w * -0.05, h * 1.08, h * 0.8, MAGENTA, 30))
    return img.convert("RGB").resize((w0, h0), Image.LANCZOS)


def main() -> None:
    SORTIE.mkdir(exist_ok=True)
    for vieux in SORTIE.glob("*.png"):
        vieux.unlink()
    for w, h in TAILLES_GAUCHE:
        image_gauche(w, h).save(SORTIE / f"gauche-{w}x{h}.png", optimize=True)
    for c in TAILLES_LOGO:
        lg = logo(c)
        lg.save(SORTIE / f"logo-{c}.png", optimize=True)
    for w, h in TAILLES_FOND:
        image_fond(w, h).save(SORTIE / f"fond-{w}x{h}.png", optimize=True)
    total = sum(p.stat().st_size for p in SORTIE.glob("*.png"))
    print(f"{len(list(SORTIE.glob('*.png')))} images dans {SORTIE} ({total / 1024:.0f} Ko)")


if __name__ == "__main__":
    main()
