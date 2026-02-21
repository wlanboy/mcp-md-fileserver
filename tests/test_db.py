# tests/test_db.py

import sqlite3
import pytest
from unittest.mock import patch

from db import _migrate_columns, init_db, update_file_entry


def _columns(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(files)").fetchall()]
    conn.close()
    return cols


# ── _migrate_columns ──────────────────────────────────────────────────────────

class TestMigrateColumns:
    def test_adds_content_column_if_missing(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE files (filename TEXT PRIMARY KEY, path TEXT, mtime REAL, keywords TEXT)")
        conn.commit()

        _migrate_columns(conn)
        conn.close()

        assert "content" in _columns(db_path)

    def test_adds_language_column_if_missing(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE files (filename TEXT PRIMARY KEY, path TEXT, mtime REAL, keywords TEXT)")
        conn.commit()

        _migrate_columns(conn)
        conn.close()

        assert "language" in _columns(db_path)

    def test_no_error_if_columns_already_exist(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE files (
                filename TEXT PRIMARY KEY, path TEXT, mtime REAL,
                keywords TEXT, content TEXT, language TEXT
            )
        """)
        conn.commit()

        # Must not raise
        _migrate_columns(conn)
        conn.close()


# ── init_db ───────────────────────────────────────────────────────────────────

class TestInitDb:
    def test_creates_files_table(self, tmp_path):
        db_path = str(tmp_path / "new.db")
        with patch("db.DB_PATH", db_path):
            init_db()
        assert "filename" in _columns(db_path)

    def test_creates_all_required_columns(self, tmp_path):
        db_path = str(tmp_path / "new.db")
        with patch("db.DB_PATH", db_path):
            init_db()
        cols = _columns(db_path)
        for col in ("filename", "path", "mtime", "keywords", "content", "language"):
            assert col in cols

    def test_idempotent_second_call(self, tmp_path):
        db_path = str(tmp_path / "new.db")
        with patch("db.DB_PATH", db_path):
            init_db()
            init_db()  # Must not raise

    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "sub" / "nested.db"
        with patch("db.DB_PATH", str(nested)):
            init_db()
        assert nested.exists()


# ── update_file_entry ─────────────────────────────────────────────────────────

def _setup_db(path: str):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE files (
            filename TEXT PRIMARY KEY, path TEXT, mtime REAL,
            keywords TEXT, content TEXT, language TEXT
        )
    """)
    conn.commit()
    conn.close()


class TestUpdateFileEntry:
    def test_inserts_new_file(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _setup_db(db_path)

        md = tmp_path / "new.md"
        md.write_text("Hello world")

        with patch("db.DB_PATH", db_path), \
             patch("db.detect_language", return_value="en"), \
             patch("db.extract_keywords", return_value=["hello", "world"]):
            update_file_entry(str(md), "new.md", 1.0)

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT filename, language, keywords FROM files WHERE filename='new.md'").fetchone()
        conn.close()

        assert row is not None
        assert row[1] == "en"
        assert "hello" in row[2]

    def test_updates_existing_file_on_mtime_change(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _setup_db(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO files VALUES (?, ?, ?, ?, ?, ?)",
            ("doc.md", str(tmp_path / "doc.md"), 1.0, "old", "old content", "en"),
        )
        conn.commit()
        conn.close()

        md = tmp_path / "doc.md"
        md.write_text("Updated content")

        with patch("db.DB_PATH", db_path), \
             patch("db.detect_language", return_value="en"), \
             patch("db.extract_keywords", return_value=["updated"]):
            update_file_entry(str(md), "doc.md", 2.0)  # new mtime

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT keywords FROM files WHERE filename='doc.md'").fetchone()
        conn.close()

        assert row[0] == "updated"

    def test_skips_processing_when_mtime_unchanged(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _setup_db(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO files VALUES (?, ?, ?, ?, ?, ?)",
            ("stable.md", "/path/stable.md", 42.0, "old", "old content", "de"),
        )
        conn.commit()
        conn.close()

        with patch("db.DB_PATH", db_path), \
             patch("db.detect_language") as mock_detect, \
             patch("db.extract_keywords") as mock_extract:
            update_file_entry("/path/stable.md", "stable.md", 42.0)  # same mtime

        mock_detect.assert_not_called()
        mock_extract.assert_not_called()

    def test_stores_content_in_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _setup_db(db_path)

        md = tmp_path / "content.md"
        md.write_text("# My Document\nSome text here.")

        with patch("db.DB_PATH", db_path), \
             patch("db.detect_language", return_value="en"), \
             patch("db.extract_keywords", return_value=["document"]):
            update_file_entry(str(md), "content.md", 1.0)

        conn = sqlite3.connect(db_path)
        content = conn.execute("SELECT content FROM files WHERE filename='content.md'").fetchone()[0]
        conn.close()

        assert "My Document" in content

    def test_handles_file_read_error_gracefully(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _setup_db(db_path)

        # File does not exist → open() raises FileNotFoundError
        with patch("db.DB_PATH", db_path), \
             patch("db.detect_language"), \
             patch("db.extract_keywords"):
            # Must not raise
            update_file_entry("/nonexistent/ghost.md", "ghost.md", 1.0)
