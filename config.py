# config.py

import os

# 📁 Basisordner für Markdown-Dateien
SCAN_FOLDER = os.getenv("MCP_SCAN_FOLDER", "/markdowns")

# ⏱️ Scanintervall in Sekunden
SCAN_INTERVAL = int(os.getenv("MCP_SCAN_INTERVAL", "60"))

# 🗃️ SQLite-Datenbankpfad
DB_PATH = os.getenv("MCP_DB_PATH", "./model_context.db")

# 🧠 Sprache für spaCy-Modell
NLP_MODEL = os.getenv("MCP_NLP_MODEL", "en_core_web_sm")
#NLP_MODEL = os.getenv("MCP_NLP_MODEL", "de_core_web_sm")
