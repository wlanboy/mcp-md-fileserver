# tests/test_tools.py

import sqlite3
import pytest
from unittest.mock import patch

from tools import register_tools, CONTENT_PREFIX


class MockApp:
    """Minimal App-Stub, der registrierte Tool-Funktionen einfängt."""

    def __init__(self):
        self._tools: dict = {}

    def tool(self, name: str, description: str):
        def decorator(func):
            self._tools[name] = func
            return func
        return decorator

    def get(self, name: str):
        return self._tools[name]


def _create_db(path: str):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE files (
            filename TEXT PRIMARY KEY,
            path     TEXT,
            mtime    REAL,
            keywords TEXT,
            content  TEXT,
            language TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO files VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("doc1.md", "/p/doc1.md", 1.0, "docker,container,build", "Docker is great for containers", "en"),
            ("doc2.md", "/p/doc2.md", 2.0, "python,programming",     "Python is awesome",             "en"),
            ("doc3.md", "/p/doc3.md", 3.0, "docker,linux",           "Docker läuft auf Linux",        "de"),
        ],
    )
    conn.commit()
    conn.close()


@pytest.fixture
def tools(tmp_path):
    db_path = str(tmp_path / "test.db")
    _create_db(db_path)
    app = MockApp()
    with patch("tools.DB_PATH", db_path):
        register_tools(app)
        yield app


# ── search-by-keywords ────────────────────────────────────────────────────────

class TestSearchByKeywords:
    def test_finds_matching_files(self, tools):
        result = tools.get("search-by-keywords")(["docker"])
        assert len(result) == 2
        filenames = {r.filename for r in result}
        assert "doc1.md" in filenames
        assert "doc3.md" in filenames

    def test_returns_empty_for_no_match(self, tools):
        result = tools.get("search-by-keywords")(["nonexistent"])
        assert result == []

    def test_returns_empty_for_empty_keywords(self, tools):
        result = tools.get("search-by-keywords")([])
        assert result == []

    def test_filters_by_language(self, tools):
        result = tools.get("search-by-keywords")(["docker"], language="de")
        assert len(result) == 1
        assert result[0].filename == "doc3.md"

    def test_result_has_correct_uri(self, tools):
        result = tools.get("search-by-keywords")(["python"])
        assert result[0].uri == f"{CONTENT_PREFIX}doc2.md"

    def test_case_insensitive_search(self, tools):
        result = tools.get("search-by-keywords")(["DOCKER"])
        assert len(result) == 2


# ── list-all-files ────────────────────────────────────────────────────────────

class TestListAllFiles:
    def test_returns_all_files(self, tools):
        result = tools.get("list-all-files")()
        assert len(result) == 3

    def test_filters_by_language(self, tools):
        result = tools.get("list-all-files")(language="de")
        assert len(result) == 1
        assert result[0].filename == "doc3.md"

    def test_result_contains_uri(self, tools):
        result = tools.get("list-all-files")()
        for r in result:
            assert r.uri.startswith(CONTENT_PREFIX)

    def test_result_contains_keywords(self, tools):
        result = tools.get("list-all-files")()
        doc1 = next(r for r in result if r.filename == "doc1.md")
        assert "docker" in doc1.keywords


# ── list-all-keywords ─────────────────────────────────────────────────────────

class TestListAllKeywords:
    def test_counts_keywords(self, tools):
        result = tools.get("list-all-keywords")()
        assert result["docker"] == 2   # doc1 and doc3
        assert result["python"] == 1

    def test_filters_by_language(self, tools):
        result = tools.get("list-all-keywords")(language="en")
        assert "linux" not in result   # linux only in de doc
        assert "docker" in result

    def test_returns_sorted_dict(self, tools):
        result = tools.get("list-all-keywords")()
        keys = list(result.keys())
        assert keys == sorted(keys)


# ── fulltext-search ───────────────────────────────────────────────────────────

class TestFulltextSearch:
    def test_finds_match(self, tools):
        result = tools.get("fulltext-search")("Python")
        assert len(result) == 1
        assert result[0].filename == "doc2.md"

    def test_returns_empty_for_no_match(self, tools):
        result = tools.get("fulltext-search")("xyznotfound")
        assert result == []

    def test_returns_empty_for_short_query(self, tools):
        result = tools.get("fulltext-search")("d")
        assert result == []

    def test_returns_empty_for_blank_query(self, tools):
        result = tools.get("fulltext-search")("  ")
        assert result == []

    def test_match_count_is_correct(self, tools):
        # "Docker" appears once in doc1 content
        result = tools.get("fulltext-search")("Docker")
        match = next(r for r in result if r.filename == "doc1.md")
        assert match.matches >= 1

    def test_preview_is_non_empty(self, tools):
        result = tools.get("fulltext-search")("awesome")
        assert result[0].preview != ""

    def test_filters_by_language(self, tools):
        result = tools.get("fulltext-search")("Docker", language="de")
        assert len(result) == 1
        assert result[0].filename == "doc3.md"

    def test_sorted_by_match_count_descending(self, tools):
        result = tools.get("fulltext-search")("Docker")
        counts = [r.matches for r in result]
        assert counts == sorted(counts, reverse=True)


# ── get-file-by-name ──────────────────────────────────────────────────────────

class TestGetFileByName:
    def test_returns_content_from_db(self, tools):
        result = tools.get("get-file-by-name")("doc2.md")
        assert "Python" in result

    def test_returns_error_for_unknown_file(self, tools):
        result = tools.get("get-file-by-name")("missing.md")
        assert "Fehler" in result
        assert "missing.md" in result

    def test_returns_error_for_empty_filename(self, tools):
        result = tools.get("get-file-by-name")("")
        assert "Fehler" in result

    def test_returns_error_when_db_content_null_and_file_missing(self, tmp_path):
        """Datei ohne content in DB und nicht mehr auf Disk → Fehlermeldung."""
        db_path = str(tmp_path / "fallback.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE files (
                filename TEXT PRIMARY KEY, path TEXT, mtime REAL,
                keywords TEXT, content TEXT, language TEXT
            )
        """)
        conn.execute(
            "INSERT INTO files VALUES (?, ?, ?, ?, ?, ?)",
            ("ghost.md", "/nonexistent/ghost.md", 1.0, "", None, "en"),
        )
        conn.commit()
        conn.close()

        app = MockApp()
        with patch("tools.DB_PATH", db_path):
            register_tools(app)
            result = app.get("get-file-by-name")("ghost.md")
        assert "Fehler" in result
