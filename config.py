# config.py

import os

# Basisordner für Markdown-Dateien
SCAN_FOLDER = os.getenv("MCP_SCAN_FOLDER", "/markdowns")

# ⏱Scanintervall in Sekunden
SCAN_INTERVAL = int(os.getenv("MCP_SCAN_INTERVAL", "60"))

# SQLite-Datenbankpfad
DB_PATH = os.getenv("MCP_DB_PATH", "./model_context.db")

# spaCy-Modelle (kommasepariert, erstes Modell = Fallback)
SPACY_MODELS = [m.strip() for m in os.getenv("MCP_SPACY_MODELS", "en_core_web_sm,de_core_news_sm").split(",")]
