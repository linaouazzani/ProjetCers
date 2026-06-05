"""
database.py — Base de données SQLite pour CERS Capbreton
=========================================================
Stocke les clubs, leurs logos et toute donnée persistante.
Le fichier cers_data.db est créé automatiquement au premier lancement.
"""

import sqlite3
import os
import json
from datetime import datetime

# Chemin du fichier SQLite — même dossier que l'application
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_APP_DIR, "cers_data.db")


# ── Connexion ──────────────────────────────────────────────────────────────────

def _connexion() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # accès par nom de colonne
    return conn


# ── Initialisation ─────────────────────────────────────────────────────────────

def init_db():
    """Crée les tables et injecte les clubs prédéfinis si la base est vide."""
    with _connexion() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clubs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nom          TEXT    NOT NULL UNIQUE,
                sport        TEXT    NOT NULL DEFAULT '',
                sport_key    TEXT    NOT NULL DEFAULT '',
                division     TEXT    NOT NULL DEFAULT '',
                couleur      TEXT    NOT NULL DEFAULT '#1c3f6e',
                logo_b64     TEXT,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

        # Seeder les clubs prédéfinis si la table est vide
        count = conn.execute("SELECT COUNT(*) FROM clubs").fetchone()[0]
        if count == 0:
            _seeder_clubs_predefinis(conn)


def _seeder_clubs_predefinis(conn: sqlite3.Connection):
    """Injecte tous les clubs de clubs_database.py dans SQLite."""
    from clubs_database import CLUBS_DATABASE
    batch = []
    for sport_key, sport_data in CLUBS_DATABASE.items():
        sport_label = sport_data["label"].replace("🏉", "").replace("⚽", "")\
                       .replace("🏀", "").replace("🤾", "").replace("🏐", "").strip()
        for division, club_list in sport_data["divisions"].items():
            for club in club_list:
                batch.append((
                    club["nom"],
                    sport_label,
                    sport_key,
                    division,
                    club.get("couleur", "#1c3f6e"),
                    None,  # pas de logo pour les clubs prédéfinis
                ))
    conn.executemany(
        "INSERT OR IGNORE INTO clubs (nom, sport, sport_key, division, couleur, logo_b64) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        batch,
    )
    conn.commit()
    print(f"[DB] {len(batch)} clubs prédéfinis injectés dans SQLite.")


# ── CRUD clubs ─────────────────────────────────────────────────────────────────

def rechercher_clubs(query: str, limite: int = 8) -> list[dict]:
    """Recherche insensible à la casse — retourne les clubs correspondants."""
    if not query or len(query) < 2:
        return []
    with _connexion() as conn:
        rows = conn.execute(
            "SELECT * FROM clubs WHERE lower(nom) LIKE ? LIMIT ?",
            (f"%{query.lower()}%", limite)
        ).fetchall()
    return [dict(r) for r in rows]


def enregistrer_club(nom: str, sport: str, division: str = "Autre",
                     couleur: str = "#1c3f6e", logo_b64: str = None,
                     sport_key: str = "autre") -> dict:
    """Insère ou met à jour un club. Retourne le dict club."""
    with _connexion() as conn:
        conn.execute("""
            INSERT INTO clubs (nom, sport, sport_key, division, couleur, logo_b64)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(nom) DO UPDATE SET
                sport    = excluded.sport,
                sport_key = excluded.sport_key,
                division = excluded.division,
                couleur  = excluded.couleur,
                logo_b64 = COALESCE(excluded.logo_b64, clubs.logo_b64)
        """, (nom, sport, sport_key, division, couleur, logo_b64))
        conn.commit()
        row = conn.execute("SELECT * FROM clubs WHERE nom = ?", (nom,)).fetchone()
    return dict(row) if row else {}


def get_club(nom: str) -> dict | None:
    """Retourne un club par son nom exact."""
    with _connexion() as conn:
        row = conn.execute("SELECT * FROM clubs WHERE lower(nom) = ?",
                           (nom.lower(),)).fetchone()
    return dict(row) if row else None


def lister_clubs_custom() -> list[dict]:
    """Retourne les clubs ajoutés manuellement (hors clubs prédéfinis)."""
    with _connexion() as conn:
        rows = conn.execute(
            "SELECT * FROM clubs WHERE sport_key = 'autre' OR logo_b64 IS NOT NULL"
            " ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def supprimer_club(nom: str):
    """Supprime un club par son nom."""
    with _connexion() as conn:
        conn.execute("DELETE FROM clubs WHERE lower(nom) = ?", (nom.lower(),))
        conn.commit()


# ── Migration depuis clubs_db.json (si existant) ───────────────────────────────

def migrer_depuis_json(json_path: str):
    """Importe les clubs d'un fichier clubs_db.json existant dans SQLite."""
    if not os.path.exists(json_path):
        return
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        migres = 0
        for _nom, club in data.items():
            enregistrer_club(
                nom      = club.get("nom", _nom),
                sport    = club.get("sport", "Autre"),
                division = club.get("division", "Autre"),
                couleur  = club.get("couleur", "#1c3f6e"),
                logo_b64 = club.get("logo_b64"),
            )
            migres += 1
        print(f"[DB] {migres} club(s) migrés depuis {json_path}")
    except Exception as e:
        print(f"[DB] Erreur migration JSON : {e}")


# ── Point d'entrée ─────────────────────────────────────────────────────────────

# Initialisation automatique à l'import
init_db()

# Migration automatique depuis l'ancien JSON si présent
_OLD_JSON = os.path.join(_APP_DIR, "clubs_db.json")
if os.path.exists(_OLD_JSON):
    migrer_depuis_json(_OLD_JSON)
