# scanner.py

import os
import time
from db import update_file_entry, init_db
from config import SCAN_FOLDER, SCAN_INTERVAL

def scan_markdown_files(folder):
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(path)
                    update_file_entry(path, file, mtime)
                except Exception as e:
                    print(f"[Fehler] Datei konnte nicht verarbeitet werden: {path}\n{e}")

def periodic_scan():
    print(f"[Scanner gestartet] Überwache: {SCAN_FOLDER} alle {SCAN_INTERVAL} Sekunden")
    init_db()
    while True:
        scan_markdown_files(SCAN_FOLDER)
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    periodic_scan()
