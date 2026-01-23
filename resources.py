# resources.py

import sqlite3

from config import DB_PATH


def register_resources(app):
    """Registriert alle Resources bei der FastMCP-App."""

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
            cur.execute("SELECT content, path FROM files WHERE filename = ?", (filename,))
            result = cur.fetchone()

        if not result:
            return f"Fehler: Datei '{filename}' nicht gefunden"

        content, path = result

        # Inhalt aus DB zurückgeben (falls vorhanden)
        if content:
            return content

        # Fallback: Aus Dateisystem lesen (für alte Einträge ohne content)
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return f"Fehler: Datei '{path}' existiert nicht mehr"
        except Exception as e:
            return f"Fehler beim Lesen: {e}"


def register_prompts(app):
    """Registriert alle Prompts bei der FastMCP-App."""

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
