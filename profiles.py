r"""Profils visuels de NEXUS (dossier profils\).

Un profil = un sous-dossier autonome :
    profils/<id>/profil.json     nom, auteur, version, modes compatibles, description, aperçu
    profils/<id>/style.css       la feuille de style (chargée par-dessus le mode Terminal ou Sentinelle)
    profils/<id>/assets/...      images et polices (facultatif)

Sécurité : un profil ne contient que du JSON, du CSS et des fichiers statiques. Le CSS est toujours
servi après analyse : @import, url() hors du dossier assets/ (Internet, chemins absolus, ".."),
expression(), javascript:, image-set(), balises <script>… sont refusés (import, validation) ou retirés
(profil déposé à la main). Taille, nombre et types de fichiers sont limités. Rien n'est chargé depuis
Internet. Un profil invalide est ignoré avec la liste de ses erreurs, jamais de plantage.

Le format complet est décrit dans profils/FORMAT.md ; vérification : python valider_profil.py <dossier>.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import shutil
import threading
import unicodedata
import uuid
import zipfile
from pathlib import Path, PurePosixPath

import paths

PROFILES_DIR = paths.PROFILES_DIR

FORMAT_VERSION = 1
MODES = ("terminal", "sentinelle")
OUVERTURES = ("fondu", "cercle", "tele")   # fin de transition : fondu, ouverture en rond, vieille télé qui s'allume
DEFAULT_ID = "defaut"
MAX_TOTAL = 5 * 1024 * 1024          # 5 Mo pour tout le profil
MAX_CSS = 256 * 1024                 # 256 Ko pour style.css
MAX_JSON = 16 * 1024                 # 16 Ko pour profil.json
MAX_FILES = 60
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# Types autorisés dans assets/ (et type MIME servi)
ASSET_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
    ".webp": "image/webp", ".avif": "image/avif", ".svg": "image/svg+xml",
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf",
}
# Fichiers tolérés à la racine du profil en plus de profil.json et style.css (jamais servis)
DOC_FILES = {".md", ".txt"}
# En-têtes posés sur tout ce qui sort de profils/ : aucun script ne peut s'exécuter, même en ouvrant
# directement un fichier (ex. un SVG piégé)
SAFE_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; img-src 'self' data:; font-src 'self'; style-src 'unsafe-inline'; sandbox",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-cache",
}


class ProfileError(ValueError):
    """Erreur lisible par un humain (import, suppression…)."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


# --------------------------------------------------------------------------- #
#  Analyse du CSS
# --------------------------------------------------------------------------- #
_HEX_ESC = re.compile(r"\\([0-9a-fA-F]{1,6})[ \t\n\r\f]?")
_CHAR_ESC = re.compile(r"\\([^0-9a-fA-F\n\r\f])")
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_URL = re.compile(r"url\(\s*(?:\"([^\"]*)\"|'([^']*)'|([^)\s]*))\s*\)", re.I)
_STRING = re.compile(r"\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'")
_FORBIDDEN = [
    (re.compile(r"@import", re.I), "@import est interdit (le profil ne doit charger aucun autre fichier)"),
    (re.compile(r"expression\s*\(", re.I), "expression() est interdit"),
    (re.compile(r"(?:java|vb)script\s*:", re.I), "les adresses javascript: / vbscript: sont interdites"),
    (re.compile(r"-moz-binding|behavior\s*:", re.I), "-moz-binding / behavior sont interdits"),
    (re.compile(r"image-set\s*\(", re.I), "image-set() est interdit (utilise url(assets/…))"),
    (re.compile(r"<\s*/?\s*(?:script|style|iframe|object|embed|link|meta)", re.I), "balise HTML interdite dans le CSS"),
    # réservés aux réglages de l'utilisateur (tailles ⚙ Réglages, fenêtres de l'agenda) : un profil ne peut pas les annuler
    (re.compile(r"(?<![\w-])zoom\s*:", re.I), "zoom est réservé aux réglages de taille (⚙ Réglages)"),
    (re.compile(r"--nx-[\w-]*\s*:", re.I), "les variables --nx-… sont réservées aux réglages de NEXUS"),
]


def _decode_escapes(css: str) -> str:
    """Retire les échappements CSS (\\75 rl(…) = url(…)) pour qu'ils ne cachent rien à l'analyse.
    Les guillemets, barres obliques inverses et retours à la ligne échappés sont conservés."""
    def hex_sub(m: re.Match) -> str:
        cp = int(m.group(1), 16)
        if cp == 0 or cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF:
            return "\ufffd"
        ch = chr(cp)
        return m.group(0) if ch in "\"'\\\n\r\f" else ch
    css = _HEX_ESC.sub(hex_sub, css)
    return _CHAR_ESC.sub(lambda m: m.group(0) if m.group(1) in "\"'\\" else m.group(1), css)


def _strip_comments(css: str) -> str:
    # on garde les retours à la ligne pour que les numéros de ligne des messages restent justes
    return _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), css)


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _safe_asset_ref(ref: str, assets: set[str]) -> tuple[bool, str]:
    r = ref.strip()
    if not r:
        return False, "url() vide"
    low = r.lower()
    if ":" in r or r.startswith(("/", "\\")) or low.startswith("//"):
        return False, f"url({r}) pointe hors du profil (adresse Internet, data: ou chemin absolu interdits)"
    if not re.fullmatch(r"[\w./ -]+", r):
        return False, f"url({r[:40]}) : caractères non autorisés dans le nom de fichier"
    p = PurePosixPath(r.replace("\\", "/"))
    if ".." in p.parts:
        return False, f"url({r}) contient « .. »"
    if not p.parts or p.parts[0] != "assets":
        return False, f"url({r}) doit désigner un fichier du dossier assets/ (ex. url(assets/fond.png))"
    if p.suffix.lower() not in ASSET_TYPES:
        return False, f"url({r}) : type de fichier non autorisé"
    if assets is not None and str(p) not in assets:
        return False, f"url({r}) : fichier introuvable dans le profil"
    return True, ""


def analyze_css(css: str, assets: set[str] | None) -> tuple[str, list[str]]:
    """Renvoie (CSS nettoyé, problèmes). Le CSS nettoyé est celui qui sera servi au navigateur."""
    problems: list[str] = []
    text = _strip_comments(_decode_escapes(css))

    # 1. url() : uniquement des fichiers du dossier assets/ du profil
    def url_sub(m: re.Match) -> str:
        ref = next(g for g in m.groups() if g is not None)
        ok, why = _safe_asset_ref(ref, assets)
        if ok:
            return f'url("{PurePosixPath(ref.strip().replace(chr(92), "/"))}")'
        problems.append(f"ligne {_line(text, m.start())} : {why}")
        return "none"
    text = _URL.sub(url_sub, text)

    # 2. chaînes qui contiennent une adresse (contournement d'url() par @font-face src, etc.)
    for m in _STRING.finditer(text):
        s = m.group(0)[1:-1].strip().lower()
        if "://" in s or s.startswith("//"):
            problems.append(f"ligne {_line(text, m.start())} : adresse externe interdite dans une chaîne ({s[:40]})")
    text = _STRING.sub(lambda m: '""' if ("://" in m.group(0) or m.group(0)[1:].lstrip().startswith("//")) else m.group(0), text)

    # 3. constructions interdites : la déclaration (ou la règle @) entière est retirée
    for rx, why in _FORBIDDEN:
        while True:
            m = rx.search(text)
            if not m:
                break
            problems.append(f"ligne {_line(text, m.start())} : {why}")
            start = max(text.rfind(";", 0, m.start()), text.rfind("{", 0, m.start()), text.rfind("}", 0, m.start())) + 1
            ends = [e for e in (text.find(";", m.end()), text.find("}", m.end())) if e != -1]
            end = min(ends) + (1 if ends and text[min(ends)] == ";" else 0) if ends else len(text)
            text = text[:start] + "\n" * text.count("\n", start, end) + text[end:]
    return text, problems


# --------------------------------------------------------------------------- #
#  Validation d'un dossier
# --------------------------------------------------------------------------- #
def _check_meta(raw: bytes) -> tuple[dict | None, list[str], list[str]]:
    errors, warnings = [], []
    if len(raw) > MAX_JSON:
        return None, [f"profil.json trop gros ({len(raw)} octets, maximum {MAX_JSON})"], []
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        return None, ["profil.json n'est pas encodé en UTF-8"], []
    except ValueError as exc:
        return None, [f"profil.json n'est pas du JSON valide ({exc})"], []
    if not isinstance(data, dict):
        return None, ["profil.json doit contenir un objet { … }"], []

    def text(key: str, max_len: int, required: bool) -> str:
        v = data.get(key)
        if v is None or v == "":
            if required:
                errors.append(f"champ « {key} » manquant dans profil.json")
            return ""
        if not isinstance(v, str):
            errors.append(f"champ « {key} » : du texte est attendu")
            return ""
        v = v.strip()
        if len(v) > max_len:
            errors.append(f"champ « {key} » trop long ({len(v)} caractères, maximum {max_len})")
        if "<" in v or ">" in v:
            errors.append(f"champ « {key} » : les caractères < et > sont interdits")
        return v[:max_len]

    meta = {
        "nom": text("nom", 40, True),
        "auteur": text("auteur", 40, False) or "anonyme",
        "version": text("version", 20, True),
        "description": text("description", 240, False),
    }
    modes = data.get("modes")
    if not isinstance(modes, list) or not modes:
        errors.append("champ « modes » manquant : liste parmi \"terminal\" et \"sentinelle\" (ex. [\"terminal\", \"sentinelle\"])")
        modes = []
    bad = [m for m in modes if m not in MODES]
    if bad:
        errors.append(f"champ « modes » : valeur(s) inconnue(s) {bad} (autorisées : terminal, sentinelle)")
    meta["modes"] = [m for m in MODES if m in modes]

    fmt = data.get("format", FORMAT_VERSION)
    if fmt != FORMAT_VERSION:
        warnings.append(f"champ « format » = {fmt!r} : ce NEXUS connaît le format {FORMAT_VERSION}")

    apercu = data.get("apercu") or {}
    couleurs, miniature = [], None
    if not isinstance(apercu, dict):
        errors.append("champ « apercu » : un objet est attendu, ex. {\"couleurs\": [\"#101010\", \"#00ff9c\"]}")
    else:
        c = apercu.get("couleurs") or []
        if not isinstance(c, list) or len(c) > 5 or not all(isinstance(x, str) and HEX_RE.match(x) for x in c):
            errors.append("apercu.couleurs : liste de 1 à 5 couleurs au format #rrggbb")
        else:
            couleurs = c
        if apercu.get("miniature") is not None:
            miniature = apercu["miniature"] if isinstance(apercu["miniature"], str) else ""
    meta["apercu"] = {"couleurs": couleurs, "miniature": miniature}

    # Animations de la page de garde (facultatif) : le panel garde la main sur la navigation et les durées
    anim = data.get("animations")
    meta["animations"] = None
    if anim is not None:
        if not isinstance(anim, dict):
            errors.append("champ « animations » : un objet est attendu, ex. {\"intro_ms\": 6000}")
        else:
            out_a = {}
            for key, lo, hi in (("intro_ms", 0, 10000), ("transition_ms", 300, 5000)):
                if key in anim:
                    v = anim[key]
                    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
                        errors.append(f"animations.{key} : nombre entier de millisecondes entre {lo} et {hi}")
                    else:
                        out_a[key] = v
            if "remplace_transition" in anim:
                if not isinstance(anim["remplace_transition"], bool):
                    errors.append("animations.remplace_transition : true ou false")
                else:
                    out_a["remplace_transition"] = anim["remplace_transition"]
            if "ouverture" in anim:                    # comment la page de garde laisse place au sommaire
                if anim["ouverture"] not in OUVERTURES:
                    errors.append(f"animations.ouverture : {', '.join(OUVERTURES)}")
                else:
                    out_a["ouverture"] = anim["ouverture"]
            bad = sorted(set(anim) - {"intro_ms", "transition_ms", "remplace_transition", "ouverture"})
            if bad:
                warnings.append(f"champ(s) ignoré(s) dans animations : {', '.join(bad)}")
            meta["animations"] = out_a or None

    # Compatibilité : version minimale du panel (« panel_min_version » : "1.0.0") ; trop récent → profil refusé
    pmv = data.get("panel_min_version")
    meta["panel_min_version"] = None
    if pmv is not None:
        if not isinstance(pmv, str) or not re.fullmatch(r"\d+\.\d+\.\d+", pmv.strip()):
            errors.append("champ « panel_min_version » : numéro de version du panel, ex. \"1.0.0\"")
        else:
            import version as _version
            cur = _version.current()
            if tuple(int(x) for x in pmv.split(".")) > tuple(int(x) for x in (re.findall(r"\d+", cur) + ["0", "0", "0"])[:3]):
                errors.append(f"ce profil demande NEXUS {pmv} ou plus récent (installé : {cur}) : mets le panel à jour")
            meta["panel_min_version"] = pmv.strip()
    known = {"nom", "auteur", "version", "description", "modes", "apercu", "format", "animations", "panel_min_version"}
    extra = sorted(set(data) - known)
    if extra:
        warnings.append(f"champ(s) ignoré(s) dans profil.json : {', '.join(extra)}")
    if not errors and not couleurs and not miniature:
        warnings.append("pas d'aperçu : ajoute apercu.couleurs pour afficher ses couleurs dans le menu")
    return meta, errors, warnings


def validate_dir(folder: Path, strict: bool = True) -> dict:
    """Vérifie un dossier de profil.
    strict=True (import, valider_profil.py) : tout problème de CSS est une erreur.
    strict=False (profil déposé à la main) : le CSS dangereux est retiré et signalé en avertissement.
    Renvoie {"ok", "meta", "errors", "warnings", "css", "assets", "size"}."""
    errors: list[str] = []
    warnings: list[str] = []
    res = {"ok": False, "meta": None, "errors": errors, "warnings": warnings, "css": "", "assets": [], "size": 0}
    if not folder.is_dir():
        errors.append(f"{folder} n'est pas un dossier")
        return res

    total, count, assets = 0, 0, set()
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder).as_posix()
        if p.is_symlink():
            errors.append(f"{rel} : les liens symboliques sont interdits")
            continue
        if p.is_dir():
            if rel != "assets" and not rel.startswith("assets/"):
                errors.append(f"{rel}/ : dossier non autorisé (seul assets/ est permis)")
            continue
        count += 1
        size = p.stat().st_size
        total += size
        parts = PurePosixPath(rel).parts
        if len(parts) == 1:
            if rel in ("profil.json", "style.css") or p.suffix.lower() in DOC_FILES:
                continue
            errors.append(f"{rel} : fichier non autorisé à la racine (permis : profil.json, style.css, *.md, *.txt, assets/)")
        elif parts[0] == "assets":
            ext = p.suffix.lower()
            if ext not in ASSET_TYPES:
                errors.append(f"{rel} : type de fichier non autorisé (permis : {', '.join(sorted(ASSET_TYPES))})")
                continue
            if ext == ".svg":
                svg = p.read_bytes()[:MAX_TOTAL].decode("utf-8", errors="ignore").lower()
                if re.search(r"<script|<foreignobject|\son[a-z]+\s*=|javascript:|<iframe|<!entity", svg):
                    errors.append(f"{rel} : SVG avec script, événement ou contenu actif : interdit")
                    continue
                if re.search(r"(?:href|src)\s*=\s*[\"'](?:https?:)?//", svg):
                    errors.append(f"{rel} : SVG qui charge une ressource depuis Internet : interdit")
                    continue
            assets.add(rel)
        else:
            errors.append(f"{rel} : emplacement non autorisé")
    res["size"] = total
    if count > MAX_FILES:
        errors.append(f"trop de fichiers ({count}, maximum {MAX_FILES})")
    if total > MAX_TOTAL:
        errors.append(f"profil trop lourd ({total / 1048576:.1f} Mo, maximum {MAX_TOTAL // 1048576} Mo)")

    pj = folder / "profil.json"
    if not pj.is_file():
        errors.append("profil.json manquant")
    else:
        meta, e, w = _check_meta(pj.read_bytes()[:MAX_JSON + 1])
        errors += e
        warnings += w
        res["meta"] = meta
        mini = (meta or {}).get("apercu", {}).get("miniature")
        if mini is not None:
            ok, why = _safe_asset_ref(mini, assets)
            if not ok or PurePosixPath(mini).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"):
                errors.append(f"apercu.miniature : {why or 'une image est attendue'}")
                meta["apercu"]["miniature"] = None

    sc = folder / "style.css"
    if not sc.is_file():
        errors.append("style.css manquant")
    elif sc.stat().st_size > MAX_CSS:
        errors.append(f"style.css trop gros ({sc.stat().st_size // 1024} Ko, maximum {MAX_CSS // 1024} Ko)")
    else:
        try:
            raw_css = sc.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            errors.append("style.css n'est pas encodé en UTF-8")
            raw_css = None
        if raw_css is not None:
            cleaned, problems = analyze_css(raw_css, assets)
            res["css"] = cleaned
            if problems:
                if strict:
                    errors += [f"style.css {p}" for p in problems]
                else:
                    # Un fichier d'assets/ manquant rend le profil invalide (retour au profil Défaut) :
                    # un décor ou une police absente pourrait rendre le panel illisible.
                    missing = [p for p in problems if "fichier introuvable dans le profil" in p]
                    errors += [f"style.css {p} (fichier manquant)" for p in missing]
                    warnings += [f"style.css {p} — retiré" for p in problems if p not in missing]
    res["assets"] = sorted(assets)
    res["ok"] = not errors
    return res


# --------------------------------------------------------------------------- #
#  Bibliothèque de profils
# --------------------------------------------------------------------------- #
def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40].strip("-")
    return s or "profil"


class ProfileLibrary:
    def __init__(self, root: Path = PROFILES_DIR) -> None:
        self.root = root
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[str, dict]] = {}     # id -> (signature, résultat de validation)

    # -- lecture -----------------------------------------------------------------
    def _signature(self, folder: Path) -> str:
        h = hashlib.sha1()
        for p in sorted(folder.rglob("*")):
            try:
                st = p.lstat()
            except OSError:
                continue
            h.update(f"{p.relative_to(folder)}|{st.st_size}|{st.st_mtime_ns}".encode())
        return h.hexdigest()[:12]

    def _folders(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        return sorted(p for p in self.root.iterdir()
                      if p.is_dir() and not p.name.startswith(("_", ".")) and not p.is_symlink())

    def _load(self, folder: Path) -> tuple[str, dict]:
        sig = self._signature(folder)
        cached = self._cache.get(folder.name)
        if cached and cached[0] == sig:
            return cached
        res = validate_dir(folder, strict=False)
        if folder.name == DEFAULT_ID or not ID_RE.match(folder.name):
            res["ok"] = False
            res["errors"].append(f"nom de dossier « {folder.name} » invalide ou réservé "
                                 "(minuscules, chiffres et tirets, 40 caractères max, pas « defaut »)")
        self._cache[folder.name] = (sig, res)
        return sig, res

    def scan(self) -> dict:
        """Relit le dossier profils/ (à chaque appel : un profil déposé apparaît tout de suite)."""
        profiles, invalid = [], []
        with self._lock:
            names = set()
            for folder in self._folders():
                names.add(folder.name)
                try:
                    sig, res = self._load(folder)
                except OSError as exc:
                    invalid.append({"dossier": folder.name, "erreurs": [f"lecture impossible : {exc}"]})
                    continue
                if not res["ok"]:
                    invalid.append({"dossier": folder.name, "erreurs": res["errors"][:12]})
                    continue
                m = res["meta"]
                mini = m["apercu"]["miniature"]
                profiles.append({
                    "id": folder.name, "nom": m["nom"], "auteur": m["auteur"], "version": m["version"],
                    "description": m["description"], "modes": m["modes"], "couleurs": m["apercu"]["couleurs"],
                    "miniature": f"/profils/{folder.name}/{mini}?v={sig}" if mini else None,
                    "css": f"/profils/{folder.name}/style.css?v={sig}", "avertissements": res["warnings"][:12],
                    "animations": m.get("animations"),
                })
            for gone in set(self._cache) - names:
                del self._cache[gone]
        profiles.sort(key=lambda p: p["nom"].lower())
        default = {"id": DEFAULT_ID, "nom": "Défaut", "auteur": "NEXUS", "version": "intégré",
                   "description": "L'apparence d'origine du mode. Toujours disponible.",
                   "modes": list(MODES), "couleurs": [], "miniature": None, "css": None, "avertissements": [],
                   "integre": True}
        return {"profils": [default] + profiles, "invalides": invalid,
                "limites": {"total_mo": MAX_TOTAL // 1048576, "css_ko": MAX_CSS // 1024, "fichiers": MAX_FILES}}

    def _valid(self, pid: str) -> dict | None:
        if not ID_RE.match(pid or "") or pid == DEFAULT_ID:
            return None
        folder = self.root / pid
        if not folder.is_dir() or folder.is_symlink():
            return None
        with self._lock:
            _, res = self._load(folder)
        return res if res["ok"] else None

    def signature(self, pid: str) -> str | None:
        """Version courante du profil (change dès qu'un de ses fichiers change) : sert aux adresses versionnées."""
        if self._valid(pid) is None:
            return None
        with self._lock:
            sig, _ = self._load(self.root / pid)
        return sig

    def css(self, pid: str) -> str | None:
        res = self._valid(pid)
        if res is None:
            return None
        sig = self.signature(pid)
        header = f"/* Profil NEXUS « {res['meta']['nom']} » — CSS vérifié et nettoyé par le serveur */\n"
        # Adresses des fichiers versionnées (?v=…) : le navigateur les garde en cache, et une nouvelle version
        # du profil change l'adresse (jamais d'image périmée)
        css = re.sub(r"""url\((["']?)(assets/[^"'()?]+)\1\)""", lambda m: f'url({m.group(1)}{m.group(2)}?v={sig}{m.group(1)})', res["css"])
        return header + css

    def asset(self, pid: str, rel: str) -> tuple[Path, str] | None:
        res = self._valid(pid)
        if res is None:
            return None
        rel = PurePosixPath(rel.replace("\\", "/"))
        key = str(PurePosixPath("assets") / rel)
        if ".." in rel.parts or key not in res["assets"]:
            return None
        path = (self.root / pid / key).resolve()
        if not path.is_relative_to((self.root / pid).resolve()):
            return None
        return path, ASSET_TYPES[path.suffix.lower()]

    # -- export --------------------------------------------------------------------
    def export_zip(self, pid: str) -> tuple[str, bytes]:
        res = self._valid(pid)
        if res is None:
            raise ProfileError("profil introuvable ou invalide")
        folder = self.root / pid
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(folder / "profil.json", f"{pid}/profil.json")
            z.writestr(f"{pid}/style.css", res["css"])       # la version vérifiée
            for a in res["assets"]:
                z.write(folder / a, f"{pid}/{a}")
            for doc in sorted(folder.iterdir()):           # licences des polices, LISEZMOI… (jamais servis)
                if doc.is_file() and not doc.is_symlink() and doc.suffix.lower() in DOC_FILES and doc.stat().st_size <= 256 * 1024:
                    z.write(doc, f"{pid}/{doc.name}")
        return f"profil-{pid}.zip", buf.getvalue()

    # -- import --------------------------------------------------------------------
    def import_zip(self, data: bytes, on_conflict: str | None = None) -> dict:
        if len(data) > MAX_TOTAL + 512 * 1024:
            raise ProfileError(f"fichier trop gros (maximum {MAX_TOTAL // 1048576} Mo)")
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise ProfileError("ce fichier n'est pas un .zip valide")
        with z:
            entries = []
            for info in z.infolist():
                name = info.filename.replace("\\", "/")
                if info.is_dir():
                    continue
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ProfileError(f"{name} : les liens symboliques sont interdits")
                p = PurePosixPath(name)
                if name.startswith("/") or re.match(r"^[A-Za-z]:", name) or ".." in p.parts:
                    raise ProfileError(f"{name} : chemin interdit (absolu ou avec « .. »)")
                entries.append((p, info))
            if len(entries) > MAX_FILES:
                raise ProfileError(f"trop de fichiers dans le zip ({len(entries)}, maximum {MAX_FILES})")
            if sum(i.file_size for _, i in entries) > MAX_TOTAL:
                raise ProfileError(f"profil trop lourd une fois décompressé (maximum {MAX_TOTAL // 1048576} Mo)")
            # profil.json à la racine du zip, ou dans un unique dossier
            roots = {p.parts[0] for p, _ in entries if len(p.parts) > 1}
            if any(p.as_posix() == "profil.json" for p, _ in entries):
                strip = 0
            elif len(roots) == 1 and any(len(p.parts) == 2 and p.parts[1] == "profil.json" for p, _ in entries):
                strip = 1
            else:
                raise ProfileError("profil.json introuvable dans le zip (à la racine ou dans un seul dossier)")
            files = {}
            budget = MAX_TOTAL
            for p, info in entries:
                if strip and (len(p.parts) < 2):
                    continue
                rel = PurePosixPath(*p.parts[strip:])
                with z.open(info) as f:
                    content = f.read(budget + 1)
                budget -= len(content)
                if budget < 0:
                    raise ProfileError(f"profil trop lourd une fois décompressé (maximum {MAX_TOTAL // 1048576} Mo)")
                files[rel.as_posix()] = content
        return self._install(files, on_conflict)

    def import_files(self, items: list[dict], on_conflict: str | None = None) -> dict:
        """Import d'un dossier déposé dans le navigateur : [{"chemin": "x/style.css", "base64": "…"}]."""
        if not isinstance(items, list) or not items:
            raise ProfileError("dossier vide")
        if len(items) > MAX_FILES:
            raise ProfileError(f"trop de fichiers ({len(items)}, maximum {MAX_FILES})")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for it in items:
                if not isinstance(it, dict):
                    raise ProfileError("élément invalide")
                try:
                    content = base64.b64decode(str(it.get("base64") or ""), validate=True)
                except ValueError:
                    raise ProfileError(f"{it.get('chemin')} : contenu illisible")
                z.writestr(str(it.get("chemin") or "")[:300], content)
        return self.import_zip(buf.getvalue(), on_conflict)

    def _install(self, files: dict[str, bytes], on_conflict: str | None) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / f".import-{uuid.uuid4().hex[:8]}"
        try:
            for rel, content in files.items():
                target = tmp / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            res = validate_dir(tmp, strict=True)
            if not res["ok"]:
                raise ProfileError("profil refusé", res["errors"])
            meta = res["meta"]
            pid = slugify(meta["nom"])
            if pid == DEFAULT_ID:
                pid = "defaut-perso"
            with self._lock:
                existing = self.root / pid
                if existing.exists():
                    if on_conflict not in ("replace", "keep"):
                        old = self._cache.get(pid, (None, {}))[1].get("meta") or {}
                        return {"conflict": True, "id": pid, "nom": meta["nom"], "nom_existant": old.get("nom", pid)}
                    if on_conflict == "replace":
                        shutil.rmtree(existing)
                    else:
                        n = 2
                        while (self.root / f"{pid[:36]}-{n}").exists():
                            n += 1
                        pid = f"{pid[:36]}-{n}"
                        data = json.loads((tmp / "profil.json").read_text(encoding="utf-8-sig"))
                        data["nom"] = f"{meta['nom'][:34]} ({n})"
                        (tmp / "profil.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                        meta["nom"] = data["nom"]
                tmp.rename(self.root / pid)
                self._cache.pop(pid, None)
            return {"ok": True, "id": pid, "nom": meta["nom"], "modes": meta["modes"], "avertissements": res["warnings"]}
        finally:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)

    def delete(self, pid: str) -> None:
        if pid == DEFAULT_ID:
            raise ProfileError("le profil Défaut est intégré : il ne peut pas être supprimé")
        if not ID_RE.match(pid or ""):
            raise ProfileError("profil introuvable")
        folder = self.root / pid
        if not folder.is_dir() or folder.is_symlink():
            raise ProfileError("profil introuvable")
        with self._lock:
            shutil.rmtree(folder)
            self._cache.pop(pid, None)
