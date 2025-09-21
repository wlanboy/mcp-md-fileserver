from fastmcp import FastMCP
from dataclasses import dataclass
from config import DB_PATH
import sqlite3

app = FastMCP("MD Indexer", mask_error_details=True)
CONTENT_PREFIX = "markdowndatei://"

@dataclass
class md:
    filename: str
    uri: str
    keywords: list

@app.tool(name="Finde Dateien mit")
def seach_by_keywords(keywords: list[str]) -> list[md]:
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
                md(filename = filename, uri = f"{CONTENT_PREFIX}{filename}", keywords = list(file_keywords))
            )

    return matched

@app.tool(name="Zeige die Datei")
def seach_by_keywords(filename: str) -> str:
    if not filename:
        return {}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT filename, path FROM files WHERE filename == ?", (filename,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return {"error": "Datei nicht in Datenbank gefunden"}, 404

    _, path = result
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return content

@app.resource("markdowndatei://{filename}")
def get_file_content(filename: str) -> str:
    if not filename:
        return {}
    
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT filename, path FROM files WHERE filename == filename")
        result = {}
        for fname, path in cur.fetchall():
            try:
                with open(path, encoding="utf-8") as f:
                    result[fname] = f.read()
            except Exception as e:
                result[fname] = f"[Fehler beim Lesen: {e}]"

        return result

if __name__ == "__main__":
    print(f"[Server gestartet] Datenbank: {DB_PATH}")
    app.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
