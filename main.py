# main.py

from fastmcp import FastMCP

from config import DB_PATH
from tools import register_tools
from resources import register_resources, register_prompts

# Server-Instruktionen für LLMs
SERVER_INSTRUCTIONS = """
# Markdown Wissensdatenbank

Dieser Service verwaltet eine Sammlung von Markdown-Dokumenten mit automatischer
Stichwort-Extraktion. Nutze ihn, um relevante Dokumente zu finden und deren Inhalte abzurufen.

## Verfügbare Such-Tools

| Tool | Zweck |
|------|-------|
| **Zeige alle Stichwörter** | Zeigt welche Begriffe suchbar sind - START HIER wenn du nicht weißt wonach suchen |
| **Finde Dateien mit** | Sucht nach extrahierten Stichwörtern (schnell, aber nur Substantive/Verben) |
| **Volltextsuche** | Sucht nach beliebigem Text im Dateiinhalt (langsamer, aber findet alles) |
| **Liste alle Dateien** | Zeigt alle Dokumente mit ihren Stichwörtern |
| **Zeige die Datei** | Liest den Inhalt einer gefundenen Datei |

## Empfohlener Workflow

1. **Orientierung**: Nutze "Zeige alle Stichwörter" um zu sehen, welche Begriffe verfügbar sind
2. **Suchen**: Nutze "Finde Dateien mit" für Themensuche ODER "Volltextsuche" für exakte Begriffe
3. **Lesen**: Nutze "Zeige die Datei" mit dem exakten Dateinamen

## Wann welche Suche?

- **"Finde Dateien mit"**: Für thematische Suche ("Zeig mir alles zu Docker")
- **"Volltextsuche"**: Für exakte Begriffe, Codebeispiele, Konfigurationswerte

## Wichtige Hinweise

- Stichwörter werden automatisch extrahiert (Verben und Substantive)
- Alle Suchen sind case-insensitive
- Dateinamen müssen exakt angegeben werden (inkl. .md Endung)
"""

# App erstellen
app = FastMCP(
    "MD Indexer",
    instructions=SERVER_INSTRUCTIONS,
    mask_error_details=True
)

# Module registrieren
register_tools(app)
register_resources(app)
register_prompts(app)


if __name__ == "__main__":
    print(f"[Server gestartet] Datenbank: {DB_PATH}")
    app.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
