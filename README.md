# MCP Markdown File Server
A FastMCP-compliant Python server that scans Markdown files, extracts subject/verb keywords using spaCy, stores metadata in SQLite, and exposes endpoints for keyword-based search and content retrieval.

---

## Features

- Periodic scan of a folder for `.md` files
- NLP keyword extraction (subjects & verbs only)
- SQLite-based metadata storage
- MCP endpoints for:
  - `POST /search` → Find files by keywords
  - `POST /content` → Return file contents (Markdown or JSON)

---

## Installation (with [uv](https://github.com/astral-sh/uv))

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```


## Install dependencies
```bash
uv sync
uv run -- spacy download en_core_web_sm #for english md files
uv run -- spacy download de_core_web_sm #for german md files
```

## Run md file scanner

```bash
uv run scanner.py
```

## Run mcp server for your llm

```bash
uv ruin main.py
```