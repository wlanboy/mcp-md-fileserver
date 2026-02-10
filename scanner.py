# scanner.py

import os
import time
import sqlite3
from db import update_file_entry, init_db
from extractor import ensure_models
from config import SCAN_FOLDER, SCAN_INTERVAL, DB_PATH


def scan_markdown_files(folder: str) -> set[str]:
    """Scannt den Ordner nach Markdown-Dateien und gibt die gefundenen Dateinamen zurück."""
    found_files = set()
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                found_files.add(file)
                try:
                    mtime = os.path.getmtime(path)
                    update_file_entry(path, file, mtime)
                except Exception as e:
                    print(f"[Fehler] Datei konnte nicht verarbeitet werden: {path}\n{e}")
    return found_files


def cleanup_deleted_files(found_files: set[str]):
    """Entfernt Dateien aus der Datenbank, die nicht mehr im Dateisystem existieren."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT filename FROM files")
        db_files = {row[0] for row in cur.fetchall()}

        deleted = db_files - found_files
        for filename in deleted:
            cur.execute("DELETE FROM files WHERE filename = ?", (filename,))
            print(f"[Entfernt] {filename} (Datei existiert nicht mehr)")

        if deleted:
            conn.commit()


def periodic_scan():
    print(f"[Scanner gestartet] Überwache: {SCAN_FOLDER} alle {SCAN_INTERVAL} Sekunden")
    ensure_models()
    init_db()
    while True:
        found_files = scan_markdown_files(SCAN_FOLDER)
        cleanup_deleted_files(found_files)
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    periodic_scan()
