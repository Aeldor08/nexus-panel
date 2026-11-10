r"""Mur de souvenirs : photos rattachées à un jour, stockées sur ce PC (data\souvenirs\), index SQLite.

- Formats : JPG, PNG, WebP. Le vrai type est vérifié par Pillow (pas seulement l'extension), taille limitée.
- Par défaut, les métadonnées (EXIF, dont la position GPS, XMP, commentaires) sont retirées : l'image est
  remise dans le bon sens puis réenregistrée sans elles. Option « garder les métadonnées » : fichier d'origine intact.
- Une miniature WebP est créée pour un affichage fluide du mur.
- Mur libre : chaque jour a sa propre disposition (position, taille, empilement de chaque photo et note,
  table souvenir_disposition, calculs dans mur.py). Notes façon post-it : table souvenir_notes.
"""

from __future__ import annotations

import datetime as dt
import io
import random
import re
import secrets
import time
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

import db
import store

ROOT = store.DATA_DIR / "souvenirs"
PHOTOS, THUMBS = ROOT / "photos", ROOT / "miniatures"
MAX_BYTES = 25 * 1024 * 1024          # 25 Mo par photo
MAX_PIXELS = 80_000_000               # protège contre les images géantes (« bombes »)
THUMB_SIZE = 520
FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-f0-9]{16}$")
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class SouvenirError(ValueError):
    pass


def _check_day(day: str) -> str:
    try:
        if not DATE_RE.match(day or ""):
            raise ValueError
        dt.date.fromisoformat(day)
    except ValueError:
        raise SouvenirError("date invalide")
    return day


def _row(r) -> dict:
    return {"id": r["id"], "jour": r["jour"], "legende": r["legende"], "type": r["type"], "largeur": r["largeur"],
            "hauteur": r["hauteur"], "octets": r["octets"], "exif_garde": bool(r["exif_garde"]), "ajoute": r["ajoute"],
            "url": f"/api/souvenirs/photo/{r['id']}", "miniature": f"/api/souvenirs/photo/{r['id']}?taille=mini"}


def add(data: bytes, day: str, caption: str = "", keep_exif: bool = False) -> dict:
    day = _check_day(day)
    caption = (caption or "").strip()[:300]
    if not data:
        raise SouvenirError("fichier vide")
    if len(data) > MAX_BYTES:
        raise SouvenirError(f"photo trop lourde ({len(data) // 1048576} Mo, maximum {MAX_BYTES // 1048576} Mo)")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()                              # vrai contenu d'image, pas seulement l'extension
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise SouvenirError("ce fichier n'est pas une image JPG, PNG ou WebP valide")
    if fmt not in FORMATS:
        raise SouvenirError(f"format {fmt or 'inconnu'} non accepté (JPG, PNG ou WebP)")
    ext, mime = FORMATS[fmt]
    pid = secrets.token_hex(8)
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        upright = ImageOps.exif_transpose(img)            # bon sens d'affichage avant de retirer l'EXIF
        if keep_exif:
            out = data
        else:
            buf = io.BytesIO()
            if fmt == "JPEG":
                upright.convert("RGB").save(buf, "JPEG", quality=92, optimize=True)   # sans exif ni xmp
            elif fmt == "PNG":
                upright.save(buf, "PNG", optimize=True)                               # sans blocs texte/exif
            else:
                upright.save(buf, "WEBP", quality=90)
            out = buf.getvalue()
        thumb = upright.copy()
        thumb.thumbnail((THUMB_SIZE, THUMB_SIZE))
        if thumb.mode not in ("RGB", "RGBA"):
            thumb = thumb.convert("RGBA" if "A" in thumb.mode else "RGB")
        tbuf = io.BytesIO()
        thumb.save(tbuf, "WEBP", quality=80)
        width, height = upright.size
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise SouvenirError(f"image illisible ({exc})")
    year_dir = PHOTOS / day[:4]
    year_dir.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    rel = f"photos/{day[:4]}/{pid}.{ext}"
    (ROOT / rel).write_bytes(out)
    (THUMBS / f"{pid}.webp").write_bytes(tbuf.getvalue())
    db.conn().execute(
        "INSERT INTO photos(id, jour, legende, fichier, miniature, type, largeur, hauteur, octets, exif_garde, ajoute)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (pid, day, caption, rel, f"miniatures/{pid}.webp", mime, width, height, len(out), int(keep_exif), time.time()))
    return get(pid)


def get(pid: str) -> dict | None:
    if not ID_RE.match(pid or ""):
        return None
    r = db.conn().execute("SELECT * FROM photos WHERE id = ?", (pid,)).fetchone()
    return _row(r) if r else None


def file_for(pid: str, mini: bool) -> tuple[Path, str] | None:
    if not ID_RE.match(pid or ""):
        return None
    r = db.conn().execute("SELECT fichier, miniature, type FROM photos WHERE id = ?", (pid,)).fetchone()
    if not r:
        return None
    path = (ROOT / (r["miniature"] if mini else r["fichier"])).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        return None
    return path, "image/webp" if mini else r["type"]


def day_photos(day: str) -> list[dict]:
    day = _check_day(day)
    return [_row(r) for r in db.conn().execute("SELECT * FROM photos WHERE jour = ? ORDER BY ajoute", (day,))]


def month_counts(month: str) -> dict[str, int]:
    if not re.match(r"^\d{4}-\d{2}$", month or ""):
        raise SouvenirError("mois invalide")
    rows = db.conn().execute("SELECT jour, COUNT(*) n FROM photos WHERE jour LIKE ? GROUP BY jour", (month + "-%",))
    return {r["jour"]: r["n"] for r in rows}


def timeline(limit: int = 60) -> list[dict]:
    """Frise : les jours qui ont des photos, du plus récent au plus ancien, avec une photo de couverture."""
    rows = db.conn().execute(
        "SELECT jour, COUNT(*) n, MIN(id) couverture FROM photos GROUP BY jour ORDER BY jour DESC LIMIT ?", (limit,))
    return [{"jour": r["jour"], "n": r["n"], "miniature": f"/api/souvenirs/photo/{r['couverture']}?taille=mini"} for r in rows]


def on_this_day(day: str) -> list[dict]:
    """« Ce jour-là » : la même date les années précédentes (le 29 février compte le 28 les autres années)."""
    day = _check_day(day)
    md = day[5:]
    rows = list(db.conn().execute("SELECT * FROM photos WHERE substr(jour, 6) = ? AND jour < ? ORDER BY jour DESC, ajoute",
                                  (md, day)))
    if md == "02-28":
        rows += db.conn().execute("SELECT * FROM photos WHERE substr(jour, 6) = '02-29' AND jour < ?", (day,))
    return [_row(r) for r in rows]


def random_old(before: str, n: int = 30) -> list[dict]:
    before = _check_day(before)
    rows = [_row(r) for r in db.conn().execute("SELECT * FROM photos WHERE jour < ?", (before,))]
    random.shuffle(rows)
    return rows[:max(1, min(n, 100))]


def update(pid: str, day: str | None = None, caption: str | None = None) -> dict:
    p = get(pid)
    if not p:
        raise SouvenirError("photo introuvable")
    if day is not None and _check_day(day) != p["jour"]:
        db.conn().execute("UPDATE photos SET jour = ? WHERE id = ?", (day, pid))
        db.conn().execute("DELETE FROM souvenir_disposition WHERE element = ?", ("p:" + pid,))   # replacée sur le nouveau jour
    if caption is not None:
        db.conn().execute("UPDATE photos SET legende = ? WHERE id = ?", (str(caption).strip()[:300], pid))
    return get(pid)


def delete(pid: str) -> None:
    r = db.conn().execute("SELECT fichier, miniature FROM photos WHERE id = ?", (pid,)).fetchone() if ID_RE.match(pid or "") else None
    if not r:
        raise SouvenirError("photo introuvable")
    for rel in (r["fichier"], r["miniature"]):
        path = (ROOT / rel).resolve()
        if path.is_relative_to(ROOT.resolve()):
            path.unlink(missing_ok=True)
    db.conn().execute("DELETE FROM photos WHERE id = ?", (pid,))
    db.conn().execute("DELETE FROM souvenir_disposition WHERE element = ?", ("p:" + pid,))


# --------------------------------------------------------------------------- #
#  Notes façon post-it et disposition du mur, par jour
# --------------------------------------------------------------------------- #
NOTE_COLORS = ("jaune", "rose", "vert", "bleu", "violet", "peche",               # pastels accordés au thème
               "menthe", "ciel", "lavande", "corail", "sable", "blanc",       # pastels fixes
               "kraft", "ardoise", "nuit", "bordeaux")                         # papiers foncés (écriture claire)
NOTE_INKS = ("auto", "noir", "sepia", "marine", "bordeaux", "foret", "violet", "blanc", "or")
NOTE_FONTS = ("theme", "sans", "serif", "manuscrite", "plume", "feutre", "machine", "elegante", "titre")
NOTE_MAX = 2000
FONT_MIN, FONT_MAX = 10, 48
NOTE_ID_RE = re.compile(r"^[a-f0-9]{12}$")
ELEM_RE = re.compile(r"^(p:[a-f0-9]{16}|n:[a-f0-9]{12})$")


def _note_row(r) -> dict:
    keys = r.keys()
    return {"id": r["id"], "jour": r["jour"], "texte": r["texte"], "couleur": r["couleur"], "police": r["police"],
            "encre": r["encre"] if "encre" in keys else "auto", "fonte": r["fonte"] if "fonte" in keys else "theme",
            "epinglee": bool(r["epinglee"]), "cree": r["cree"], "modifie": r["modifie"]}


def get_note(nid: str) -> dict | None:
    if not NOTE_ID_RE.match(nid or ""):
        return None
    r = db.conn().execute("SELECT * FROM souvenir_notes WHERE id = ?", (nid,)).fetchone()
    return _note_row(r) if r else None


def day_notes(day: str) -> list[dict]:
    """Notes du jour + notes épinglées des jours précédents (une seule note, visible sur chaque jour suivant)."""
    day = _check_day(day)
    return [_note_row(r) for r in db.conn().execute(
        "SELECT * FROM souvenir_notes WHERE jour = ? OR (epinglee = 1 AND jour < ?) ORDER BY cree", (day, day))]


def _clean_note(texte=None, couleur=None, police=None, encre=None, fonte=None) -> dict:
    out = {}
    if encre is not None:
        if encre not in NOTE_INKS:
            raise SouvenirError("couleur d'écriture inconnue")
        out["encre"] = encre
    if fonte is not None:
        if fonte not in NOTE_FONTS:
            raise SouvenirError("police inconnue")
        out["fonte"] = fonte
    if texte is not None:
        t = str(texte)
        if len(t) > NOTE_MAX:
            raise SouvenirError(f"note trop longue ({NOTE_MAX} caractères maximum)")
        out["texte"] = t
    if couleur is not None:
        if couleur not in NOTE_COLORS:
            raise SouvenirError("couleur de note inconnue")
        out["couleur"] = couleur
    if police is not None:
        try:
            out["police"] = min(max(int(police), FONT_MIN), FONT_MAX)
        except (TypeError, ValueError):
            raise SouvenirError("taille de police invalide")
    return out


def add_note(day: str, texte: str = "", couleur: str = "jaune", police: int = 18, position: dict | None = None) -> dict:
    import mur
    day = _check_day(day)
    vals = _clean_note(texte, couleur, police)
    nid, now = secrets.token_hex(6), time.time()
    c = db.conn()
    c.execute("INSERT INTO souvenir_notes(id, jour, texte, couleur, police, epinglee, cree, modifie) VALUES(?,?,?,?,?,0,?,?)",
              (nid, day, vals["texte"], vals["couleur"], vals["police"], now, now))
    dispo = _layout_rows(day)
    z = max((e["z"] for e in dispo.values()), default=0) + 1
    if position and all(k in position for k in ("x", "y")):
        e = mur.borne({"x": position["x"], "y": position["y"], "w": mur.CELLULE, "h": mur.NOTE_H, "z": z})
    else:                                           # sous le contenu du jour
        e = mur.grille([("n:" + nid, mur.CELLULE, mur.NOTE_H)], mur.bas_du_mur(dispo) + mur.ECART, z)["n:" + nid]
    _write_layout(day, {"n:" + nid: e})
    return get_note(nid)


def update_note(nid: str, **changes) -> dict:
    n = get_note(nid)
    if not n:
        raise SouvenirError("note introuvable")
    vals = _clean_note(changes.get("texte"), changes.get("couleur"), changes.get("police"), changes.get("encre"), changes.get("fonte"))
    if changes.get("epinglee") is not None:
        vals["epinglee"] = 1 if changes["epinglee"] else 0
    if vals:
        sets = ", ".join(f"{k} = ?" for k in vals)
        db.conn().execute(f"UPDATE souvenir_notes SET {sets}, modifie = ? WHERE id = ?", (*vals.values(), time.time(), nid))
    if vals.get("epinglee") == 0:                   # désépinglée : elle ne reste que sur son jour
        db.conn().execute("DELETE FROM souvenir_disposition WHERE element = ? AND jour != ?", ("n:" + nid, n["jour"]))
    return get_note(nid)


def delete_note(nid: str) -> None:
    if not get_note(nid):
        raise SouvenirError("note introuvable")
    c = db.conn()
    c.execute("DELETE FROM souvenir_notes WHERE id = ?", (nid,))
    c.execute("DELETE FROM souvenir_disposition WHERE element = ?", ("n:" + nid,))


def _layout_rows(day: str) -> dict[str, dict]:
    return {r["element"]: {"x": r["x"], "y": r["y"], "w": r["largeur"], "h": r["hauteur"], "z": r["z"]}
            for r in db.conn().execute("SELECT * FROM souvenir_disposition WHERE jour = ?", (day,))}


def _write_layout(day: str, elements: dict[str, dict]) -> None:
    c = db.conn()
    for eid, e in elements.items():
        c.execute("""INSERT INTO souvenir_disposition(jour, element, x, y, largeur, hauteur, z) VALUES(?,?,?,?,?,?,?)
                     ON CONFLICT(jour, element) DO UPDATE SET x = excluded.x, y = excluded.y, largeur = excluded.largeur,
                     hauteur = excluded.hauteur, z = excluded.z""", (day, eid, e["x"], e["y"], e["w"], e["h"], e["z"]))


def _elements(day: str, photos: list[dict], notes: list[dict]) -> list[tuple[str, float, float]]:
    import mur
    return ([("p:" + p["id"], *mur.taille_photo(p["largeur"], p["hauteur"])) for p in photos]
            + [("n:" + n["id"], mur.CELLULE, mur.NOTE_H) for n in notes])


def wall(day: str) -> dict:
    """Mur d'un jour : photos, notes et disposition. Un élément sans place enregistrée reçoit une place
    automatique (sous le reste), aussitôt enregistrée : revenir sur le jour affiche le même mur."""
    import mur
    day = _check_day(day)
    photos, notes = day_photos(day), day_notes(day)
    dispo = _layout_rows(day)
    items = _elements(day, photos, notes)
    missing = [it for it in items if it[0] not in dispo]
    if missing:
        z0 = max((e["z"] for e in dispo.values()), default=0) + 1
        start = mur.bas_du_mur(dispo) + mur.ECART if dispo else mur.MARGE
        new = mur.grille(missing, start, z0)
        _write_layout(day, new)
        dispo.update(new)
    valid = {it[0] for it in items}
    return {"jour": day, "photos": photos, "notes": notes, "largeur_mur": mur.LARGEUR,
            "disposition": {k: v for k, v in dispo.items() if k in valid},
            "limites": {"min_w": mur.MIN_W, "max_w": mur.MAX_W, "min_h": mur.MIN_H, "max_h": mur.MAX_H}}


def save_layout(day: str, elements: dict) -> dict:
    """Enregistre la place d'éléments du mur de ce jour (seuls ceux affichés ce jour-là sont acceptés)."""
    import mur
    day = _check_day(day)
    if not isinstance(elements, dict) or len(elements) > 500:
        raise SouvenirError("disposition invalide")
    valid = {it[0] for it in _elements(day, day_photos(day), day_notes(day))}
    clean = {}
    for eid, e in elements.items():
        if not ELEM_RE.match(str(eid)) or eid not in valid or not isinstance(e, dict):
            continue
        try:
            clean[eid] = mur.borne(e)
        except (TypeError, ValueError):
            raise SouvenirError("disposition invalide")
    _write_layout(day, clean)
    return wall(day)


def auto_layout(day: str) -> dict:
    """« Réorganiser automatiquement » : grille propre pour tout le mur du jour."""
    import mur
    day = _check_day(day)
    items = _elements(day, day_photos(day), day_notes(day))
    db.conn().execute("DELETE FROM souvenir_disposition WHERE jour = ?", (day,))
    _write_layout(day, mur.grille(items))
    return wall(day)


def summary(day: str) -> dict:
    c = db.conn()
    return {"aujourdhui": c.execute("SELECT COUNT(*) FROM photos WHERE jour = ?", (day,)).fetchone()[0],
            "total": c.execute("SELECT COUNT(*) FROM photos").fetchone()[0],
            "ce_jour_la": c.execute("SELECT COUNT(*) FROM photos WHERE substr(jour, 6) = ? AND jour < ?",
                                    (day[5:], day)).fetchone()[0]}
