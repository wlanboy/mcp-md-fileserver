# db.py

import sqlite3
import os
from config import DB_PATH, NLP_MODEL
from extractor import extract_keywords


def _migrate_add_content_column(conn):
    """Fügt die content-Spalte hinzu, falls sie in einer älteren DB fehlt."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(files)")
    columns = [row[1] for row in cur.fetchall()]
    if "content" not in columns:
        cur.execute("ALTER TABLE files ADD COLUMN content TEXT")
        conn.commit()
        print("[Migration] content-Spalte zur Datenbank hinzugefügt")


def init_db():
    """Initialisiert die Datenbank und legt die Tabelle an, falls sie nicht existiert."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            filename TEXT PRIMARY KEY,
            path TEXT,
            mtime REAL,
            keywords TEXT,
            content TEXT
        )
        """)
        # Migration: content-Spalte hinzufügen falls sie fehlt (für bestehende DBs)
        _migrate_add_content_column(conn)

def update_file_entry(path, filename, mtime):
    """Aktualisiert oder fügt einen Dateieintrag hinzu, wenn sich das Änderungsdatum geändert hat."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT mtime FROM files WHERE filename=?", (filename,))
        row = cur.fetchone()

        if not row or row[0] != mtime:
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                keywords = extract_keywords(content, model=NLP_MODEL)
                keyword_str = ",".join(sorted(set(keywords)))
                cur.execute("""
                    REPLACE INTO files (filename, path, mtime, keywords, content)
                    VALUES (?, ?, ?, ?, ?)
                """, (filename, path, mtime, keyword_str, content))
                conn.commit()
                print(f"[Aktualisiert] {filename} mit {len(keywords)} Stichwörtern")
            except Exception as e:
                print(f"[Fehler] Datei konnte nicht verarbeitet werden: {path}\n{e}")
