# tools.py

from dataclasses import dataclass, field
from typing import Annotated
import sqlite3

from config import DB_PATH

CONTENT_PREFIX = "markdowndatei://"


@dataclass
class MarkdownFile:
    """schema:DigitalDocument – Ein indexiertes Markdown-Dokument mit Metadaten."""
    filename: str = field(metadata={"description": "schema:name – Dateiname inkl. .md Endung"})
    uri: str = field(metadata={"description": "schema:url – URI zum direkten Abruf des Inhalts"})
    keywords: list[str] = field(metadata={"description": "schema:keywords – Automatisch extrahierte Stichwörter"})
    language: str = field(metadata={"description": "schema:inLanguage – Erkannte Sprache (ISO-639-1, z.B. 'en', 'de')"})


@dataclass
class SearchResult:
    """Ergebnis einer schema:SearchAction – Volltextsuche-Treffer mit Kontext."""
    filename: str = field(metadata={"description": "schema:name – Dateiname des Treffers"})
    matches: int = field(metadata={"description": "schema:resultCount – Anzahl der Treffer in dieser Datei"})
    preview: str = field(metadata={"description": "schema:description – Textausschnitt mit dem ersten Treffer"})


def register_tools(app):
    """Registriert alle Tools bei der FastMCP-App."""

    @app.tool(
        name="search-by-keywords",
        description="schema:SearchAction – Sucht schema:DigitalDocument anhand von schema:keywords. "
                    "Gibt Dokumente zurück, deren extrahierte Stichwörter mindestens einen der Suchbegriffe enthalten. "
                    "Optional filterbar nach schema:inLanguage."
    )
    def search_by_keywords(
        keywords: Annotated[
            list[str],
            "Suchbegriffe, z.B. ['docker', 'container', 'build']"
        ],
        language: Annotated[
            str | None,
            "ISO-639-1 Sprachfilter, z.B. 'de' oder 'en'. Wenn nicht angegeben, werden alle Sprachen durchsucht."
        ] = None
    ) -> list[MarkdownFile]:
        if not keywords:
            return []

        query_keywords = set(kw.strip().lower() for kw in keywords)
        lang_filter = language.strip().lower() if language else None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filename, keywords, language FROM files")
        rows = cursor.fetchall()
        conn.close()

        matched = []
        for filename, keyword_str, file_lang in rows:
            if not keyword_str:
                continue
            if lang_filter and (file_lang or "unknown") != lang_filter:
                continue
            file_keywords = set(kw.strip().lower() for kw in keyword_str.split(","))
            if query_keywords & file_keywords:
                matched.append(
                    MarkdownFile(
                        filename=filename,
                        uri=f"{CONTENT_PREFIX}{filename}",
                        keywords=list(file_keywords),
                        language=file_lang or "unknown"
                    )
                )

        return matched

    @app.tool(
        name="list-all-files",
        description="schema:DiscoverAction – Gibt eine schema:ItemList aller indexierten schema:DigitalDocument zurück, "
                    "jeweils mit schema:name, schema:keywords und schema:inLanguage. "
                    "Optional filterbar nach schema:inLanguage."
    )
    def list_all_files(
        language: Annotated[
            str | None,
            "ISO-639-1 Sprachfilter, z.B. 'de' oder 'en'. Wenn nicht angegeben, werden alle Dateien zurückgegeben."
        ] = None
    ) -> list[MarkdownFile]:
        lang_filter = language.strip().lower() if language else None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filename, keywords, language FROM files")
        rows = cursor.fetchall()
        conn.close()

        files = []
        for filename, keyword_str, file_lang in rows:
            if lang_filter and (file_lang or "unknown") != lang_filter:
                continue
            keywords = [kw.strip() for kw in keyword_str.split(",")] if keyword_str else []
            files.append(
                MarkdownFile(
                    filename=filename,
                    uri=f"{CONTENT_PREFIX}{filename}",
                    keywords=keywords,
                    language=file_lang or "unknown"
                )
            )

        return files

    @app.tool(
        name="list-all-keywords",
        description="schema:DiscoverAction – Listet alle schema:DefinedTerm (extrahierte Stichwörter) mit der Anzahl "
                    "zugehöriger schema:DigitalDocument auf. Zeigt das Themenspektrum der Wissensdatenbank. "
                    "Optional filterbar nach schema:inLanguage."
    )
    def list_all_keywords(
        language: Annotated[
            str | None,
            "ISO-639-1 Sprachfilter, z.B. 'de' oder 'en'. Wenn nicht angegeben, werden Stichwörter aller Sprachen angezeigt."
        ] = None
    ) -> dict[str, int]:
        lang_filter = language.strip().lower() if language else None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT keywords, language FROM files")
        rows = cursor.fetchall()
        conn.close()

        keyword_counts: dict[str, int] = {}
        for keyword_str, file_lang in rows:
            if not keyword_str:
                continue
            if lang_filter and (file_lang or "unknown") != lang_filter:
                continue
            for kw in keyword_str.split(","):
                kw = kw.strip().lower()
                if kw:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        return dict(sorted(keyword_counts.items()))

    @app.tool(
        name="fulltext-search",
        description="schema:SearchAction – Durchsucht schema:text aller schema:DigitalDocument nach einem Textbegriff. "
                    "Findet auch Codebeispiele, URLs und Konfigurationswerte, die nicht als schema:keywords extrahiert werden. "
                    "Optional filterbar nach schema:inLanguage."
    )
    def fulltext_search(
        query: Annotated[
            str,
            "Suchbegriff, z.B. 'docker-compose' oder 'SELECT * FROM'"
        ],
        language: Annotated[
            str | None,
            "ISO-639-1 Sprachfilter, z.B. 'de' oder 'en'. Wenn nicht angegeben, werden alle Sprachen durchsucht."
        ] = None
    ) -> list[SearchResult]:
        if not query or len(query.strip()) < 2:
            return []

        query_lower = query.strip().lower()
        lang_filter = language.strip().lower() if language else None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filename, content, language FROM files WHERE content IS NOT NULL")
        rows = cursor.fetchall()
        conn.close()

        results = []
        for filename, content, file_lang in rows:
            if not content:
                continue
            if lang_filter and (file_lang or "unknown") != lang_filter:
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
        name="get-file-by-name",
        description="schema:ReadAction – Gibt den vollständigen schema:text eines schema:DigitalDocument zurück. "
                    "Der schema:name muss exakt angegeben werden (inkl. .md) und kann über die Such-Tools ermittelt werden."
    )
    def get_file_by_name(
        filename: Annotated[
            str,
            "Exakter Dateiname inkl. .md Endung, z.B. 'kubernetes-basics.md'"
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
            return f"Fehler: Datei '{filename}' nicht gefunden. Nutze 'list-all-files' um verfügbare Dateien zu sehen."

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
