from fastmcp import FastMCP
from dataclasses import dataclass, field
from typing import Annotated
from config import DB_PATH
import sqlite3

# Server-Instruktionen für LLMs
SERVER_INSTRUCTIONS = """
# Markdown Wissensdatenbank

Dieser Service verwaltet eine Sammlung von Markdown-Dokumenten mit automatischer
Stichwort-Extraktion. Nutze ihn, um relevante Dokumente zu finden und deren Inhalte abzurufen.

## Empfohlener Workflow

1. **Thema erkunden**: Nutze "Finde Dateien mit" mit thematischen Stichwörtern
2. **Übersicht gewinnen**: Nutze "Liste alle Dateien" wenn du nicht weißt, welche Dokumente existieren
3. **Inhalt lesen**: Nutze "Zeige die Datei" mit dem exakten Dateinamen aus Schritt 1 oder 2

## Wichtige Hinweise

- Stichwörter werden automatisch aus den Dokumenten extrahiert (Verben und Substantive)
- Die Suche ist case-insensitive (Groß-/Kleinschreibung egal)
- Dateinamen müssen exakt angegeben werden (inkl. .md Endung)
- Bei mehreren relevanten Dateien: Lies sie nacheinander, nicht alle auf einmal

## Beispiel-Interaktion

Nutzer fragt: "Was wissen wir über Kubernetes?"
→ Suche mit: ["kubernetes", "container", "deployment", "pod"]
→ Lies die gefundenen Dateien
→ Fasse die relevanten Informationen zusammen
"""

app = FastMCP(
    "MD Indexer",
    instructions=SERVER_INSTRUCTIONS,
    mask_error_details=True
)

CONTENT_PREFIX = "markdowndatei://"


@dataclass
class MarkdownFile:
    """Eine indexierte Markdown-Datei mit Metadaten."""
    filename: str = field(metadata={"description": "Der Dateiname inkl. .md Endung"})
    uri: str = field(metadata={"description": "Die URI zum direkten Abruf des Inhalts"})
    keywords: list[str] = field(metadata={"description": "Automatisch extrahierte Stichwörter"})


# =============================================================================
# TOOLS
# =============================================================================

@app.tool(
    name="Finde Dateien mit",
    description="""Durchsucht die Wissensdatenbank nach Dokumenten, die bestimmte Stichwörter enthalten.

WANN NUTZEN:
- Wenn du Dokumente zu einem bestimmten Thema finden möchtest
- Wenn der Nutzer nach Informationen zu einem Konzept fragt
- Als erster Schritt vor dem Lesen von Dateiinhalten

EINGABE:
- Liste von Stichwörtern (Substantive, Verben, Fachbegriffe)
- Nutze mehrere verwandte Begriffe für bessere Ergebnisse
- Beispiel: ["python", "function", "async"] für asynchrone Python-Funktionen

AUSGABE:
- Liste von Dateien mit passenden Stichwörtern
- Jede Datei enthält: filename, uri, keywords
- Leere Liste wenn nichts gefunden

TIPPS:
- Verwende Synonyme und verwandte Begriffe
- Englische UND deutsche Begriffe probieren
- Bei 0 Treffern: allgemeinere Begriffe verwenden"""
)
def search_by_keywords(
    keywords: Annotated[
        list[str],
        "Liste von Suchbegriffen. Beispiel: ['docker', 'container', 'build']"
    ]
) -> list[MarkdownFile]:
    if not keywords:
        return []

    query_keywords = set(kw.strip().lower() for kw in keywords)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, keywords FROM files")
    rows = cursor.fetchall()
    conn.close()

    matched = []
    for filename, keyword_str in rows:
        if not keyword_str:
            continue
        file_keywords = set(kw.strip().lower() for kw in keyword_str.split(","))
        if query_keywords & file_keywords:
            matched.append(
                MarkdownFile(
                    filename=filename,
                    uri=f"{CONTENT_PREFIX}{filename}",
                    keywords=list(file_keywords)
                )
            )

    return matched


@app.tool(
    name="Liste alle Dateien",
    description="""Gibt eine vollständige Liste aller indexierten Markdown-Dokumente zurück.

WANN NUTZEN:
- Wenn du einen Überblick über alle verfügbaren Dokumente brauchst
- Wenn du nicht weißt, welche Stichwörter du suchen sollst
- Um dem Nutzer zu zeigen, welche Themen abgedeckt sind

AUSGABE:
- Alle Dateien mit ihren Stichwörtern
- Sortiert nach Dateiname

TIPP: Nutze die keywords in der Ausgabe, um relevante Dateien zu identifizieren."""
)
def list_all_files() -> list[MarkdownFile]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, keywords FROM files")
    rows = cursor.fetchall()
    conn.close()

    files = []
    for filename, keyword_str in rows:
        keywords = [kw.strip() for kw in keyword_str.split(",")] if keyword_str else []
        files.append(
            MarkdownFile(
                filename=filename,
                uri=f"{CONTENT_PREFIX}{filename}",
                keywords=keywords
            )
        )

    return files


@app.tool(
    name="Zeige die Datei",
    description="""Liest und gibt den vollständigen Inhalt einer Markdown-Datei zurück.

WANN NUTZEN:
- Nachdem du mit "Finde Dateien mit" oder "Liste alle Dateien" relevante Dateien gefunden hast
- Wenn der Nutzer den Inhalt eines bestimmten Dokuments sehen möchte

EINGABE:
- filename: Der exakte Dateiname aus der vorherigen Suche (inkl. .md)
- Beispiel: "kubernetes-basics.md"

AUSGABE:
- Der vollständige Markdown-Inhalt der Datei
- Fehlermeldung wenn Datei nicht existiert

WICHTIG: Verwende den exakten Dateinamen aus der Suchergebnis-Liste!"""
)
def get_file_by_name(
    filename: Annotated[
        str,
        "Exakter Dateiname inkl. .md Endung. Beispiel: 'docker-compose.md'"
    ]
) -> str:
    if not filename:
        return "Fehler: Kein Dateiname angegeben. Bitte gib den exakten Dateinamen an (z.B. 'readme.md')."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, path FROM files WHERE filename = ?", (filename,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return f"Fehler: Datei '{filename}' nicht gefunden. Nutze 'Liste alle Dateien' um verfügbare Dateien zu sehen."

    _, path = result
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"Fehler: Die Datei '{filename}' wurde aus dem Dateisystem entfernt."
    except Exception as e:
        return f"Fehler beim Lesen der Datei: {e}"


# =============================================================================
# RESOURCES
# =============================================================================

@app.resource(
    "markdowndatei://{filename}",
    description="Direkter Zugriff auf den Inhalt einer Markdown-Datei über ihre URI."
)
def get_file_content(filename: str) -> str:
    """Resource-Handler für Markdown-Dateien."""
    if not filename:
        return "Fehler: Kein Dateiname angegeben"

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT path FROM files WHERE filename = ?", (filename,))
        result = cur.fetchone()

    if not result:
        return f"Fehler: Datei '{filename}' nicht gefunden"

    path = result[0]
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Fehler: Datei '{path}' existiert nicht mehr"
    except Exception as e:
        return f"Fehler beim Lesen: {e}"


# =============================================================================
# PROMPTS - Vorgefertigte Workflows für häufige Aufgaben
# =============================================================================

@app.prompt(
    name="Thema recherchieren",
    description="Hilft bei der systematischen Recherche zu einem Thema in der Wissensdatenbank."
)
def research_topic(topic: str) -> str:
    return f"""Ich möchte alles über "{topic}" aus der Wissensdatenbank erfahren.

Bitte gehe so vor:
1. Suche nach Dokumenten mit Stichwörtern zu "{topic}" und verwandten Begriffen
2. Liste die gefundenen Dokumente mit einer kurzen Einschätzung ihrer Relevanz
3. Lies die relevantesten Dokumente
4. Fasse die wichtigsten Informationen zu "{topic}" zusammen

Falls keine Dokumente gefunden werden, liste alle verfügbaren Dokumente und prüfe,
ob eines davon indirekt relevant sein könnte."""


@app.prompt(
    name="Dokument zusammenfassen",
    description="Erstellt eine Zusammenfassung eines bestimmten Dokuments."
)
def summarize_document(filename: str) -> str:
    return f"""Bitte erstelle eine Zusammenfassung des Dokuments "{filename}".

Gehe so vor:
1. Lade den Inhalt der Datei "{filename}"
2. Erstelle eine strukturierte Zusammenfassung mit:
   - Hauptthema (1 Satz)
   - Kernpunkte (Bullet Points)
   - Wichtige Details oder Codebeispiele
   - Verwandte Themen (basierend auf den Keywords)"""


@app.prompt(
    name="Wissenslücke finden",
    description="Analysiert welche Themen in der Wissensdatenbank fehlen könnten."
)
def find_knowledge_gaps(domain: str) -> str:
    return f"""Analysiere die Wissensdatenbank im Bereich "{domain}".

Bitte:
1. Liste alle Dokumente auf
2. Identifiziere welche Themen im Bereich "{domain}" abgedeckt sind
3. Schlage vor, welche Dokumente fehlen könnten, um das Thema vollständig abzudecken"""

if __name__ == "__main__":
    print(f"[Server gestartet] Datenbank: {DB_PATH}")
    app.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
