# MCP Markdown Fileserver - Technische Spezifikation

## Übersicht

Ein Model Context Protocol (MCP) Server zur Verwaltung einer Markdown-Wissensdatenbank mit automatischer NLP-basierter Stichwort-Extraktion. Der Dienst ermöglicht LLM-Clients das Durchsuchen und Abrufen von Markdown-Dokumenten.

---

## 1. Architektur

### 1.1 Komponenten

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server (HTTP)                       │
│                    localhost:8000/mcp                       │
├─────────────────────────────────────────────────────────────┤
│  Tools (5)  │  Resources (1)  │  Prompts (3)               │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Scanner    │  │  Extractor   │  │   Database   │      │
│  │  (Periodic)  │  │    (NLP)     │  │   (SQLite)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   Markdown-Verzeichnis  │
              │    (Dateisystem)        │
              └─────────────────────────┘
```

### 1.2 Datenfluss

1. **Scanner** durchsucht periodisch das konfigurierte Verzeichnis nach `.md`-Dateien
2. **Extractor** extrahiert Stichwörter mittels NLP (Nomen & Verben)
3. **Database** speichert Metadaten und Inhalte zwischen
4. **MCP Server** stellt Tools für LLM-Clients bereit

---

## 2. Konfiguration

### 2.1 Umgebungsvariablen

| Variable | Beschreibung | Standardwert | Typ |
|----------|--------------|--------------|-----|
| `MCP_SCAN_FOLDER` | Verzeichnis mit Markdown-Dateien | `/markdowns` | String |
| `MCP_SCAN_INTERVAL` | Scan-Intervall in Sekunden | `60` | Integer |
| `MCP_DB_PATH` | Pfad zur SQLite-Datenbank | `./model_context.db` | String |
| `MCP_NLP_MODEL` | spaCy-Modellname | `en_core_web_sm` | String |

### 2.2 Unterstützte NLP-Modelle

- `en_core_web_sm` - Englisch (Standard)
- `de_core_web_sm` - Deutsch
- Weitere spaCy-kompatible Modelle

---

## 3. Datenbank-Schema

### 3.1 Tabelle: `files`

```sql
CREATE TABLE files (
    filename TEXT PRIMARY KEY,  -- Dateiname (z.B. "docker.md")
    path TEXT,                  -- Vollständiger Dateipfad
    mtime REAL,                 -- Änderungszeit (Unix-Timestamp)
    keywords TEXT,              -- Komma-separierte Stichwörter
    content TEXT                -- Vollständiger Markdown-Inhalt
);
```

### 3.2 Beispieldaten

```
filename: "docker.md"
path: "/markdowns/docker.md"
mtime: 1706123456.789
keywords: "docker,container,image,build,run"
content: "# Docker Guide\n\nDocker ist eine..."
```

---

## 4. NLP Stichwort-Extraktion

### 4.1 Algorithmus

**Eingabe**: Markdown-Text
**Ausgabe**: Liste von Stichwörtern

**Verarbeitungsschritte**:
1. Text mit spaCy-Modell parsen
2. Tokens filtern nach:
   - **POS-Tags**: Nur `NOUN` (Nomen) und `VERB` (Verben)
   - **Dependency**: Nur `nsubj` (Nominalsubjekt) oder `ROOT`
3. Lemmatisierung (Grundform): "running" → "run"
4. Normalisierung: Kleinschreibung
5. Deduplizierung und Sortierung

### 4.2 Beispiel

```
Eingabe: "The Docker container runs in isolation"
Ausgabe: ["container", "docker", "run"]
```

### 4.3 Implementierungsdetails

- Modelle werden gecacht (LRU-Cache, max. 4 Modelle)
- Unterstützt Modellwechsel pro Aufruf
- Fehlerbehandlung bei fehlenden Modellen

---

## 5. File Scanner

### 5.1 Scan-Prozess

```
┌─────────────────────────────────────────────┐
│              Periodischer Scan              │
├─────────────────────────────────────────────┤
│ 1. Alle .md-Dateien im Verzeichnis finden   │
│ 2. Für jede Datei:                          │
│    - mtime prüfen (Änderung?)               │
│    - Falls geändert/neu:                    │
│      - Inhalt lesen                         │
│      - Stichwörter extrahieren              │
│      - In DB speichern/aktualisieren        │
│ 3. Gelöschte Dateien aus DB entfernen       │
│ 4. Sleep(MCP_SCAN_INTERVAL)                 │
│ 5. Wiederhole ab 1.                         │
└─────────────────────────────────────────────┘
```

### 5.2 Änderungserkennung

- Basiert auf `mtime` (Modification Time)
- Nur geänderte Dateien werden neu verarbeitet
- Reduziert CPU- und I/O-Last

### 5.3 Bereinigung

- Dateien in DB aber nicht im Dateisystem → löschen
- Automatisch bei jedem Scan-Durchlauf

---

## 6. MCP Server

### 6.1 Server-Konfiguration

- **Transport**: HTTP
- **Host**: `0.0.0.0`
- **Port**: `8000`
- **Pfad**: `/mcp`
- **URL**: `http://localhost:8000/mcp`

### 6.2 Server-Instruktionen (für LLM-Clients)

```
# Markdown Wissensdatenbank

Dieser Service verwaltet eine Sammlung von Markdown-Dokumenten mit automatischer
Stichwort-Extraktion. Nutze ihn, um relevante Dokumente zu finden und deren
Inhalte abzurufen.

## Verfügbare Such-Tools
- Zeige alle Stichwörter
- Finde Dateien mit
- Volltextsuche
- Liste alle Dateien
- Zeige die Datei

## Empfohlener Workflow
1. Orientierung: Nutze "Zeige alle Stichwörter" um zu sehen, welche Begriffe
   verfügbar sind
2. Suchen: Nutze "Finde Dateien mit" für Themensuche ODER "Volltextsuche"
   für exakte Begriffe
3. Lesen: Nutze "Zeige die Datei" mit dem exakten Dateinamen
```

---

## 7. MCP Tools (5 Stück)

### 7.1 Tool: "Zeige alle Stichwörter"

**Zweck**: Alle verfügbaren Stichwörter mit Häufigkeit anzeigen

**Parameter**: Keine

**Rückgabe**:
```json
{
  "docker": 3,
  "kubernetes": 2,
  "container": 4
}
```

**Algorithmus**:
1. Alle Einträge aus `files`-Tabelle laden
2. Komma-separierte Keywords splitten
3. Häufigkeit pro Keyword zählen
4. Alphabetisch sortiert zurückgeben

---

### 7.2 Tool: "Finde Dateien mit"

**Zweck**: Dateien nach Stichwörtern suchen (schnellste Suche)

**Parameter**:
```
keywords: string[]  // z.B. ["docker", "container"]
```

**Rückgabe**:
```json
[
  {
    "filename": "docker.md",
    "uri": "markdowndatei://docker.md",
    "keywords": ["docker", "container", "image"]
  }
]
```

**Algorithmus**:
1. Eingabe-Keywords auf Kleinschreibung normalisieren
2. Alle Dateien mit Keywords aus DB laden
3. Schnittmenge bilden: `eingabe_keywords ∩ datei_keywords`
4. Bei Übereinstimmung → Datei in Ergebnisliste
5. Nach Dateiname sortiert zurückgeben

---

### 7.3 Tool: "Liste alle Dateien"

**Zweck**: Alle indexierten Dokumente auflisten

**Parameter**: Keine

**Rückgabe**:
```json
[
  {
    "filename": "docker.md",
    "uri": "markdowndatei://docker.md",
    "keywords": ["docker", "container"]
  },
  {
    "filename": "kubernetes.md",
    "uri": "markdowndatei://kubernetes.md",
    "keywords": ["kubernetes", "pod"]
  }
]
```

---

### 7.4 Tool: "Volltextsuche"

**Zweck**: Inhalte durchsuchen (umfassend, aber langsamer)

**Parameter**:
```
query: string  // z.B. "docker-compose" (min. 2 Zeichen)
```

**Rückgabe**:
```json
[
  {
    "filename": "docker.md",
    "matches": 5,
    "preview": "...example docker-compose configuration..."
  }
]
```

**Algorithmus**:
1. Query validieren (mindestens 2 Zeichen)
2. Alle Dateien mit Inhalt aus DB laden
3. Für jede Datei:
   - Inhalt in Kleinschreibung konvertieren
   - Vorkommen zählen (case-insensitive)
   - Bei Treffern: Preview extrahieren (50 Zeichen Kontext vor/nach)
4. Nach Trefferanzahl absteigend sortieren
5. Ergebnisse zurückgeben

**Preview-Format**:
- `"..."` am Anfang wenn nicht am Textanfang
- 50 Zeichen vor dem ersten Treffer
- Der Treffer selbst
- 50 Zeichen nach dem Treffer
- `"..."` am Ende wenn nicht am Textende

---

### 7.5 Tool: "Zeige die Datei"

**Zweck**: Vollständigen Dateiinhalt abrufen

**Parameter**:
```
filename: string  // z.B. "docker.md"
```

**Rückgabe**:
```
# Docker Guide

Docker ist eine Containerisierungsplattform...
```

**Algorithmus**:
1. Dateiname validieren (nicht leer)
2. In DB nach filename suchen
3. Falls gefunden:
   - `content`-Feld zurückgeben
   - Fallback: Aus Dateisystem lesen (Legacy-Support)
4. Falls nicht gefunden:
   - Fehlermeldung mit Hinweis auf "Liste alle Dateien"

**Fehlermeldungen**:
```
"Fehler: Kein Dateiname angegeben. Bitte gib den Namen der gewünschten
Datei an (z.B. 'docker.md'). Nutze 'Liste alle Dateien' um verfügbare
Dateien zu sehen."

"Fehler: Datei '{filename}' nicht gefunden. Nutze 'Liste alle Dateien'
um verfügbare Dateien zu sehen."
```

---

## 8. MCP Resources

### 8.1 URI-Schema

**Format**: `markdowndatei://{filename}`

**Beispiele**:
- `markdowndatei://docker.md`
- `markdowndatei://kubernetes-guide.md`

**Verhalten**:
- Identisch mit Tool "Zeige die Datei"
- Ermöglicht direkten Zugriff über URI-Referenz

---

## 9. MCP Prompts (3 Stück)

### 9.1 Prompt: "Thema recherchieren"

**Beschreibung**: Systematische Recherche zu einem Thema

**Parameter**:
```
topic: string  // z.B. "Docker"
```

**Template**:
```
Ich möchte alles über "{topic}" aus der Wissensdatenbank erfahren.

Bitte gehe so vor:
1. Suche nach Dokumenten mit Stichwörtern zu "{topic}" und verwandten Begriffen
2. Liste die gefundenen Dokumente mit einer kurzen Einschätzung ihrer Relevanz
3. Lies die relevantesten Dokumente
4. Fasse die wichtigsten Informationen zu "{topic}" zusammen

Falls keine Dokumente gefunden werden, liste alle verfügbaren Dokumente und
prüfe, ob eines davon indirekt relevant sein könnte.
```

---

### 9.2 Prompt: "Dokument zusammenfassen"

**Beschreibung**: Strukturierte Zusammenfassung eines Dokuments

**Parameter**:
```
filename: string  // z.B. "docker.md"
```

**Template**:
```
Bitte erstelle eine Zusammenfassung des Dokuments "{filename}".

Gehe so vor:
1. Lade den Inhalt der Datei "{filename}"
2. Erstelle eine strukturierte Zusammenfassung mit:
   - Hauptthema (1 Satz)
   - Kernpunkte (Bullet Points)
   - Wichtige Details oder Codebeispiele
   - Verwandte Themen (basierend auf den Keywords)
```

---

### 9.3 Prompt: "Wissenslücke finden"

**Beschreibung**: Analyse von Lücken in der Wissensdatenbank

**Parameter**:
```
domain: string  // z.B. "DevOps"
```

**Template**:
```
Analysiere die Wissensdatenbank im Bereich "{domain}".

Bitte:
1. Liste alle Dokumente auf
2. Identifiziere welche Themen im Bereich "{domain}" abgedeckt sind
3. Schlage vor, welche Dokumente fehlen könnten, um das Thema vollständig
   abzudecken
```

---

## 10. Datenstrukturen

### 10.1 MarkdownFile

```
MarkdownFile {
    filename: string      // "docker.md"
    uri: string          // "markdowndatei://docker.md"
    keywords: string[]   // ["docker", "container", "image"]
}
```

### 10.2 SearchResult

```
SearchResult {
    filename: string     // "docker.md"
    matches: integer     // 5
    preview: string      // "...example text..."
}
```

### 10.3 KeywordCount

```
KeywordCount {
    [keyword: string]: integer  // {"docker": 3, "container": 4}
}
```

---

## 11. Fehlerbehandlung

### 11.1 Dateiverarbeitung

- Datei nicht lesbar → Überspringen, Fehler loggen
- Encoding-Fehler → UTF-8 erzwingen
- Leere Datei → Normale Verarbeitung (leere Keywords)

### 11.2 NLP-Modell

- Modell nicht gefunden → RuntimeError mit Hinweis auf Installation
- Modell-Ladezeit → Gecacht nach erstem Laden

### 11.3 Datenbank

- DB nicht vorhanden → Automatisch erstellen
- Schema-Migration → Automatisch bei Start
- Concurrent Access → SQLite-Locking

### 11.4 Tool-Aufrufe

- Ungültige Parameter → Beschreibende Fehlermeldung
- Leere Ergebnisse → Leere Liste (kein Fehler)
- Datei nicht gefunden → Hinweis auf "Liste alle Dateien"

---

## 12. Sicherheit

### 12.1 Dateizugriff

- Nur Lesezugriff auf konfiguriertes Verzeichnis
- Keine Schreiboperationen auf Dateisystem
- Pfad-Validierung gegen Directory Traversal

### 12.2 Datenbank

- Parameterisierte Queries (SQL-Injection-Schutz)
- Lokale SQLite-Datei (kein Netzwerkzugriff)

### 12.3 MCP-Server

- Fehlerdetails maskiert (`mask_error_details=True`)
- Nur lokaler Zugriff empfohlen

---

## 13. Performance-Charakteristik

| Operation | Typische Dauer |
|-----------|---------------|
| Stichwort-Extraktion | 50-200ms pro Datei |
| Keyword-Suche | <10ms |
| Volltextsuche | 50-500ms |
| Datei abrufen | <5ms (aus Cache) |

**Speicherverbrauch**:
- spaCy-Modell: ~200-500MB RAM
- SQLite-Cache: Proportional zur Dokumentanzahl

---

## 14. Abhängigkeiten

### 14.1 Laufzeitumgebung

- Python 3.12+
- SQLite 3

### 14.2 Python-Pakete

```
fastmcp==2.12.3      # MCP-Framework
spacy>=3.8.7         # NLP-Bibliothek
uvicorn>=0.36.0      # ASGI-Server
```

### 14.3 spaCy-Modelle (separat zu installieren)

```bash
python -m spacy download en_core_web_sm  # Englisch
python -m spacy download de_core_web_sm  # Deutsch
```

---

## 15. Spring Boot Implementierung - Hinweise

### 15.1 Komponenten-Mapping

| Python-Komponente | Spring Boot Äquivalent |
|-------------------|------------------------|
| FastMCP | Spring MVC Controller + Custom MCP Handler |
| SQLite + sqlite3 | H2/SQLite + Spring Data JPA |
| spaCy | OpenNLP / Stanford CoreNLP / Python-Subprocess |
| asyncio Scanner | @Scheduled + TaskExecutor |
| Environment vars | application.properties / @ConfigurationProperties |

### 15.2 NLP-Alternativen für Java

**Option A: Java-native NLP**
- Apache OpenNLP
- Stanford CoreNLP
- LangChain4j

**Option B: Python-Integration**
- ProcessBuilder für Python-Script-Aufrufe
- Jep (Java Embedded Python)
- GraalPython

### 15.3 MCP-Protokoll

Das Model Context Protocol erfordert:
- JSON-RPC-ähnliche Kommunikation
- Tool-Registrierung mit Schema
- Resource-Provider für URI-Handling
- Prompt-Templates

### 15.4 Empfohlene Spring-Komponenten

```
spring-boot-starter-web      # HTTP-Server
spring-boot-starter-data-jpa # Datenbankzugriff
spring-ai-core               # AI/MCP-Integration
```

---

## 16. API-Schnittstellenvertrag

### 16.1 MCP Tool-Definitionen

```json
{
  "tools": [
    {
      "name": "Zeige alle Stichwörter",
      "description": "Zeigt alle verfügbaren Stichwörter mit Häufigkeit",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
      }
    },
    {
      "name": "Finde Dateien mit",
      "description": "Sucht Dateien nach Stichwörtern",
      "inputSchema": {
        "type": "object",
        "properties": {
          "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Liste von Stichwörtern"
          }
        },
        "required": ["keywords"]
      }
    },
    {
      "name": "Liste alle Dateien",
      "description": "Listet alle indexierten Markdown-Dokumente",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
      }
    },
    {
      "name": "Volltextsuche",
      "description": "Durchsucht Dateiinhalte nach einem Begriff",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Suchbegriff (min. 2 Zeichen)",
            "minLength": 2
          }
        },
        "required": ["query"]
      }
    },
    {
      "name": "Zeige die Datei",
      "description": "Gibt den vollständigen Inhalt einer Datei zurück",
      "inputSchema": {
        "type": "object",
        "properties": {
          "filename": {
            "type": "string",
            "description": "Name der Markdown-Datei"
          }
        },
        "required": ["filename"]
      }
    }
  ]
}
```

### 16.2 MCP Resource-Definition

```json
{
  "resources": [
    {
      "uri": "markdowndatei://{filename}",
      "name": "Markdown-Datei",
      "description": "Zugriff auf eine Markdown-Datei über URI",
      "mimeType": "text/markdown"
    }
  ]
}
```

### 16.3 MCP Prompt-Definitionen

```json
{
  "prompts": [
    {
      "name": "Thema recherchieren",
      "description": "Systematische Recherche zu einem Thema",
      "arguments": [
        {
          "name": "topic",
          "description": "Das zu recherchierende Thema",
          "required": true
        }
      ]
    },
    {
      "name": "Dokument zusammenfassen",
      "description": "Strukturierte Zusammenfassung erstellen",
      "arguments": [
        {
          "name": "filename",
          "description": "Name der zusammenzufassenden Datei",
          "required": true
        }
      ]
    },
    {
      "name": "Wissenslücke finden",
      "description": "Lücken in der Wissensdatenbank analysieren",
      "arguments": [
        {
          "name": "domain",
          "description": "Der zu analysierende Themenbereich",
          "required": true
        }
      ]
    }
  ]
}
```

---

## 17. Testszenarien

### 17.1 Unit Tests

- [ ] Stichwort-Extraktion mit verschiedenen Texten
- [ ] Keyword-Matching-Logik
- [ ] Volltextsuche mit Sonderzeichen
- [ ] Preview-Generierung an Textgrenzen

### 17.2 Integrationstests

- [ ] Datei-Scan und DB-Update
- [ ] Änderungserkennung bei mtime
- [ ] Bereinigung gelöschter Dateien
- [ ] Concurrent DB-Zugriffe

### 17.3 E2E-Tests

- [ ] Kompletter Workflow: Scan → Index → Suche → Abruf
- [ ] MCP-Tool-Aufrufe über HTTP
- [ ] Fehlerszenarien (fehlende Datei, ungültige Parameter)

---

## 18. Beispiel-Workflow

### Typischer LLM-Client-Workflow

```
Benutzer: "Was wissen wir über Docker?"

LLM-Assistent:
1. Ruft "Zeige alle Stichwörter" auf
   → Erkennt: "docker" ist verfügbar (3 Dateien)

2. Ruft "Finde Dateien mit" ["docker"] auf
   → Erhält: docker.md, docker-compose.md, dockerfile-best-practices.md

3. Ruft "Zeige die Datei" "docker.md" auf
   → Erhält: Vollständiger Markdown-Inhalt

4. Fasst Informationen für Benutzer zusammen
```

---

**Version**: 1.0
**Datum**: 2026-01-25
**Basierend auf**: mcp-md-fileserver (Python-Implementierung)
