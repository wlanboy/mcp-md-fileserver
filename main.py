# main.py

from fastmcp import FastMCP

from config import DB_PATH
from tools import register_tools
from resources import register_resources, register_prompts

# App erstellen
app = FastMCP(
    "MD Indexer",
    mask_error_details=True
)

# Module registrieren
register_tools(app)
register_resources(app)
register_prompts(app)


if __name__ == "__main__":
    print(f"[Server gestartet] Datenbank: {DB_PATH}")
    app.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
