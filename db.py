r"""Base SQLite locale de NEXUS (data\nexus.db) : souvenirs, statistiques personnelles, journal.

- Une seule connexion par thread, mode WAL (lectures pendant les écritures, pas de blocage du panel).
- Migrations numérotées (MIGRATIONS) appliquées dans l'ordre au démarrage. Avant toute migration sur une
  base existante, une copie est faite dans data\backups\.
- Une migration est soit du SQL, soit le nom d'une fonction « _… » de ce module (étape en Python).
- Installation neuve : la base est créée vide, les trois catégories démarrent sans données.
Tout reste sur ce PC : rien n'est jamais envoyé ailleurs.
"""

from __future__ import annotations

import shutil
import sqlite3
import threading
import time

import store

DB_FILE = store.DATA_DIR / "nexus.db"

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
    CREATE TABLE reglages (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);

    -- Souvenirs : une ligne par photo (fichiers dans data/souvenirs/)
    CREATE TABLE photos (
        id TEXT PRIMARY KEY, jour TEXT NOT NULL, legende TEXT NOT NULL DEFAULT '',
        fichier TEXT NOT NULL, miniature TEXT NOT NULL, type TEXT NOT NULL,
        largeur INTEGER, hauteur INTEGER, octets INTEGER, exif_garde INTEGER NOT NULL DEFAULT 0,
        ajoute REAL NOT NULL
    );
    CREATE INDEX photos_jour ON photos(jour);

    -- Statistiques : agrégats par heure et par application (jamais de titre de fenêtre ni de contenu)
    CREATE TABLE activite_heure (
        jour TEXT NOT NULL, heure INTEGER NOT NULL,
        actif_s REAL NOT NULL DEFAULT 0, inactif_s REAL NOT NULL DEFAULT 0,
        cpu_somme REAL NOT NULL DEFAULT 0, cpu_max REAL NOT NULL DEFAULT 0, cpu_n INTEGER NOT NULL DEFAULT 0,
        gpu_somme REAL NOT NULL DEFAULT 0, gpu_max REAL NOT NULL DEFAULT 0, gpu_n INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (jour, heure)
    );
    CREATE TABLE temps_appli (
        jour TEXT NOT NULL, nom TEXT NOT NULL, categorie TEXT NOT NULL, secondes REAL NOT NULL DEFAULT 0,
        PRIMARY KEY (jour, nom, categorie)
    );
    CREATE TABLE sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, debut REAL NOT NULL, fin REAL NOT NULL,
                           actif_s REAL NOT NULL DEFAULT 0);
    CREATE INDEX sessions_debut ON sessions(debut);

    -- Journal : une entrée par jour
    CREATE TABLE journal (
        jour TEXT PRIMARY KEY, humeur TEXT NOT NULL DEFAULT '', activites TEXT NOT NULL DEFAULT '[]',
        texte TEXT NOT NULL DEFAULT '', modifie REAL NOT NULL
    );
    """,
    ),
    (
        2,
        """
    -- Souvenirs : notes façon post-it rattachées à un jour (épinglée = visible aussi les jours suivants)
    CREATE TABLE souvenir_notes (
        id TEXT PRIMARY KEY, jour TEXT NOT NULL, texte TEXT NOT NULL DEFAULT '',
        couleur TEXT NOT NULL DEFAULT 'jaune', police INTEGER NOT NULL DEFAULT 18,
        epinglee INTEGER NOT NULL DEFAULT 0, cree REAL NOT NULL, modifie REAL NOT NULL
    );
    CREATE INDEX souvenir_notes_jour ON souvenir_notes(jour);

    -- Souvenirs : disposition du mur, PAR JOUR (élément « p:<photo> » ou « n:<note> »), unités du mur (mur.py)
    CREATE TABLE souvenir_disposition (
        jour TEXT NOT NULL, element TEXT NOT NULL,
        x REAL NOT NULL, y REAL NOT NULL, largeur REAL NOT NULL, hauteur REAL NOT NULL, z INTEGER NOT NULL,
        PRIMARY KEY (jour, element)
    );
    """,
    ),
    (3, "_disposition_photos_existantes"),
    (
        4,
        """
    -- Post-it : couleur d'écriture (« auto » = foncée sur fond clair, claire sur fond sombre) et police
    ALTER TABLE souvenir_notes ADD COLUMN encre TEXT NOT NULL DEFAULT 'auto';
    ALTER TABLE souvenir_notes ADD COLUMN fonte TEXT NOT NULL DEFAULT 'theme'
    """,
    ),
]
VERSION = MIGRATIONS[-1][0]


def _disposition_photos_existantes(con: sqlite3.Connection) -> None:
    """Migration 3 : chaque jour qui a déjà des photos reçoit une disposition automatique (grille)."""
    import mur

    days: dict[str, list] = {}
    for r in con.execute("SELECT id, jour, largeur, hauteur FROM photos ORDER BY jour, ajoute"):
        days.setdefault(r["jour"], []).append(("p:" + r["id"], *mur.taille_photo(r["largeur"], r["hauteur"])))
    for day, items in days.items():
        for eid, e in mur.grille(items).items():
            con.execute(
                "INSERT OR IGNORE INTO souvenir_disposition(jour, element, x, y, largeur, hauteur, z) VALUES(?,?,?,?,?,?,?)",
                (day, eid, e["x"], e["y"], e["w"], e["h"], e["z"]),
            )


_local = threading.local()
_init_lock = threading.Lock()
_ready = False


def _connect() -> sqlite3.Connection:
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_FILE, timeout=10, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def migrate() -> int:
    """Crée la base si besoin et applique les migrations manquantes. Renvoie la version."""
    global _ready
    with _init_lock:
        existed = DB_FILE.exists()
        con = _connect()
        try:
            _migrer(con, existed)
        finally:
            con.close()  # (aussi si une migration échoue)
        _ready = True
        return VERSION


def _migrer(con: sqlite3.Connection, existed: bool) -> None:
    cur = con.execute("PRAGMA user_version").fetchone()[0]
    todo = [(v, sql) for v, sql in MIGRATIONS if v > cur]
    if todo and existed and cur > 0:
        (store.DATA_DIR / "backups").mkdir(parents=True, exist_ok=True)
        con.execute("PRAGMA wal_checkpoint(FULL)")
        shutil.copy2(DB_FILE, store.DATA_DIR / "backups" / f"nexus-v{cur}-{time.strftime('%Y%m%d-%H%M%S')}.db")
    for v, sql in todo:
        con.execute("BEGIN")
        try:
            if sql.startswith("_"):  # étape en Python (ex. calcul de dispositions)
                globals()[sql](con)
            else:
                for statement in _split(sql):  # dans la transaction (executescript la validerait)
                    con.execute(statement)
            con.execute(f"PRAGMA user_version = {v}")
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise


def _split(sql: str) -> list[str]:
    """Découpe un script en instructions (pas de « ; » dans nos chaînes), sans les commentaires."""
    lines = [ligne for ligne in sql.splitlines() if not ligne.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def conn() -> sqlite3.Connection:
    if not _ready:
        migrate()
    c = getattr(_local, "con", None)
    if c is None:
        c = _local.con = _connect()
    return c


def get_setting(key: str, default=None):
    import json

    row = conn().execute("SELECT valeur FROM reglages WHERE cle = ?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["valeur"])
    except ValueError:
        return default


def set_setting(key: str, value) -> None:
    import json

    conn().execute("INSERT INTO reglages(cle, valeur) VALUES(?, ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur", (key, json.dumps(value)))
