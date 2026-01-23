# MCP Markdown Wissensdatenbank

Ein MCP-Server (Model Context Protocol) zur Verwaltung von Markdown-Dokumenten mit automatischer Stichwort-Extraktion. LLMs können damit eine Sammlung von Markdown-Dateien durchsuchen und deren Inhalte abrufen.

## Features

- **Automatischer Scan** von Markdown-Dateien mit konfigurierbarem Intervall
- **NLP-Keyword-Extraktion** mit spaCy (Substantive & Verben)
- **Volltextsuche** im gesamten Dateiinhalt
- **SQLite-Datenbank** für schnellen Zugriff (inkl. gecachtem Content)
- **Semantische Instruktionen** für LLMs mit Workflow-Empfehlungen
- **Prompt-Templates** für häufige Aufgaben

## Tools

| Tool | Beschreibung |
|------|--------------|
| **Zeige alle Stichwörter** | Listet alle verfügbaren Keywords mit Häufigkeit |
| **Finde Dateien mit** | Sucht nach Dateien anhand von Stichwörtern |
| **Volltextsuche** | Durchsucht den gesamten Dateiinhalt |
| **Liste alle Dateien** | Zeigt alle indexierten Dokumente |
| **Zeige die Datei** | Gibt den Inhalt einer Datei zurück |

## Prompts

| Prompt | Beschreibung |
|--------|--------------|
| **Thema recherchieren** | Systematische Recherche zu einem Thema |
| **Dokument zusammenfassen** | Strukturierte Zusammenfassung einer Datei |
| **Wissenslücke finden** | Analysiert fehlende Themen in einem Bereich |

## Installation

### Voraussetzungen

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (empfohlen)

### Setup

```bash
# uv installieren (falls nicht vorhanden)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Dependencies installieren
uv sync

# spaCy-Modell herunterladen
uv run -- python -m spacy download en_core_web_sm  # Englisch
uv run -- python -m spacy download de_core_web_sm  # Deutsch
```

## Konfiguration

Umgebungsvariablen (oder Standardwerte in `config.py`):

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `MCP_SCAN_FOLDER` | Ordner mit Markdown-Dateien | `/markdowns` |
| `MCP_SCAN_INTERVAL` | Scan-Intervall in Sekunden | `60` |
| `MCP_DB_PATH` | Pfad zur SQLite-Datenbank | `./model_context.db` |
| `MCP_NLP_MODEL` | spaCy-Modell | `en_core_web_sm` |

## Verwendung

### 1. Scanner starten

Der Scanner überwacht den konfigurierten Ordner und indiziert Markdown-Dateien:

```bash
uv run scanner.py
```

### 2. MCP-Server starten

```bash
uv run main.py
```

Der Server läuft auf `http://0.0.0.0:8000/mcp`.

### 3. Mit LLM verbinden

#### LM Studio

1. Settings → Program → Install
2. `mcp.json` bearbeiten und Server hinzufügen

#### Claude Desktop / andere MCP-Clients

Server-URL: `http://localhost:8000/mcp`

## Beispiel-Interaktion

```
Nutzer: Was wissen wir über Docker?

LLM:
1. Nutzt "Zeige alle Stichwörter" → findet "docker", "container", "image"
2. Nutzt "Finde Dateien mit" ["docker", "container"] → findet docker.md, docker-compose.md
3. Nutzt "Zeige die Datei" "docker.md" → liest Inhalt
4. Fasst die Informationen zusammen
```

