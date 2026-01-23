# tools.py

from dataclasses import dataclass, field
from typing import Annotated
import sqlite3

from config import DB_PATH

CONTENT_PREFIX = "markdowndatei://"


@dataclass
class MarkdownFile:
    """Eine indexierte Markdown-Datei mit Metadaten."""
    filename: str = field(metadata={"description": "Der Dateiname inkl. .md Endung"})
    uri: str = field(metadata={"description": "Die URI zum direkten Abruf des Inhalts"})
    keywords: list[str] = field(metadata={"description": "Automatisch extrahierte Stichwörter"})


@dataclass
class SearchResult:
    """Ein Volltextsuche-Treffer mit Kontext."""
    filename: str = field(metadata={"description": "Der Dateiname"})
    matches: int = field(metadata={"description": "Anzahl der Treffer in dieser Datei"})
    preview: str = field(metadata={"description": "Textausschnitt mit dem ersten Treffer"})


def register_tools(app):
    """Registriert alle Tools bei der FastMCP-App."""

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
        name="Zeige alle Stichwörter",
        description="""Listet alle verfügbaren Stichwörter in der Wissensdatenbank auf.

WANN NUTZEN:
- Als ERSTER Schritt, wenn du nicht weißt, welche Begriffe suchbar sind
- Um dem Nutzer zu zeigen, welche Themen in der Datenbank abgedeckt sind
- Um passende Suchbegriffe für "Finde Dateien mit" zu finden

AUSGABE:
- Alphabetisch sortierte Liste aller einzigartigen Stichwörter
- Anzahl der Dateien pro Stichwort

TIPP: Die häufigsten Stichwörter zeigen die Schwerpunkte der Wissensdatenbank."""
    )
    def list_all_keywords() -> dict[str, int]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT keywords FROM files")
        rows = cursor.fetchall()
        conn.close()

        keyword_counts: dict[str, int] = {}
        for (keyword_str,) in rows:
            if not keyword_str:
                continue
            for kw in keyword_str.split(","):
                kw = kw.strip().lower()
                if kw:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        return dict(sorted(keyword_counts.items()))

    @app.tool(
        name="Volltextsuche",
        description="""Durchsucht den INHALT aller Markdown-Dateien nach einem Suchbegriff.

WANN NUTZEN:
- Wenn "Finde Dateien mit" keine Ergebnisse liefert
- Für exakte Begriffe, die keine extrahierten Stichwörter sind
- Für Codebeispiele, Konfigurationswerte, URLs, etc.
- Wenn der Nutzer nach einem spezifischen Text sucht

EINGABE:
- query: Der Suchbegriff (kann auch mehrere Wörter sein)
- Beispiel: "docker-compose.yml" oder "kubectl apply"

AUSGABE:
- Liste von Dateien mit Treffern
- Anzahl der Treffer pro Datei
- Textvorschau mit dem ersten Treffer

UNTERSCHIED zu "Finde Dateien mit":
- "Finde Dateien mit": Sucht nur in extrahierten Stichwörtern (Substantive/Verben)
- "Volltextsuche": Sucht im gesamten Dateiinhalt (findet alles)"""
    )
    def fulltext_search(
        query: Annotated[
            str,
            "Suchbegriff für die Volltextsuche. Beispiel: 'docker-compose' oder 'SELECT * FROM'"
        ]
    ) -> list[SearchResult]:
        if not query or len(query.strip()) < 2:
            return []

        query_lower = query.strip().lower()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filename, content FROM files WHERE content IS NOT NULL")
        rows = cursor.fetchall()
        conn.close()

        results = []
        for filename, content in rows:
            if not content:
                continue

            content_lower = content.lower()
            matches = content_lower.count(query_lower)

            if matches > 0:
                idx = content_lower.find(query_lower)
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 50)
                preview = content[start:end]
                if start > 0:
                    preview = "..." + preview
                if end < len(content):
                    preview = preview + "..."

                results.append(SearchResult(
                    filename=filename,
                    matches=matches,
                    preview=preview.replace("\n", " ")
                ))

        results.sort(key=lambda x: x.matches, reverse=True)
        return results

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
        cursor.execute("SELECT content, path FROM files WHERE filename = ?", (filename,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return f"Fehler: Datei '{filename}' nicht gefunden. Nutze 'Liste alle Dateien' um verfügbare Dateien zu sehen."

        content, path = result

        # Inhalt aus DB zurückgeben (falls vorhanden)
        if content:
            return content

        # Fallback: Aus Dateisystem lesen (für alte Einträge ohne content)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return f"Fehler: Die Datei '{filename}' wurde aus dem Dateisystem entfernt."
        except Exception as e:
            return f"Fehler beim Lesen der Datei: {e}"
