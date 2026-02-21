# tests/test_scanner.py

import sqlite3
from unittest.mock import patch

from scanner import scan_markdown_files, cleanup_deleted_files


def _make_db(path: str, filenames: list[str]):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE files (filename TEXT PRIMARY KEY)")
    for name in filenames:
        conn.execute("INSERT INTO files VALUES (?)", (name,))
    conn.commit()
    conn.close()


# ── scan_markdown_files ───────────────────────────────────────────────────────

class TestScanMarkdownFiles:
    def test_returns_only_md_files(self, tmp_path):
        (tmp_path / "notes.md").write_text("# Hello")
        (tmp_path / "readme.txt").write_text("ignore me")
        (tmp_path / "config.yaml").write_text("key: value")

        with patch("scanner.update_file_entry"):
            result = scan_markdown_files(str(tmp_path))

        assert "notes.md" in result
        assert "readme.txt" not in result
        assert "config.yaml" not in result

    def test_discovers_nested_md_files(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.md").write_text("# Deep")

        with patch("scanner.update_file_entry"):
            result = scan_markdown_files(str(tmp_path))

        assert "deep.md" in result

    def test_calls_update_file_entry_for_each_md(self, tmp_path):
        (tmp_path / "a.md").write_text("A")
        (tmp_path / "b.md").write_text("B")

        with patch("scanner.update_file_entry") as mock_update:
            scan_markdown_files(str(tmp_path))

        assert mock_update.call_count == 2

    def test_returns_empty_set_for_empty_folder(self, tmp_path):
        with patch("scanner.update_file_entry"):
            result = scan_markdown_files(str(tmp_path))
        assert result == set()

    def test_skips_file_on_error_without_crash(self, tmp_path):
        (tmp_path / "bad.md").write_text("X")

        with patch("scanner.update_file_entry", side_effect=Exception("fail")):
            result = scan_markdown_files(str(tmp_path))

        # Still returns the filename even if update_file_entry raises
        assert "bad.md" in result

    def test_update_called_with_correct_filename(self, tmp_path):
        (tmp_path / "example.md").write_text("content")

        with patch("scanner.update_file_entry") as mock_update:
            scan_markdown_files(str(tmp_path))

        args = mock_update.call_args
        assert args[0][1] == "example.md"


# ── cleanup_deleted_files ─────────────────────────────────────────────────────

class TestCleanupDeletedFiles:
    def test_removes_files_not_in_found_set(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _make_db(db_path, ["old.md", "existing.md"])

        with patch("scanner.DB_PATH", db_path):
            cleanup_deleted_files({"existing.md"})

        conn = sqlite3.connect(db_path)
        rows = {r[0] for r in conn.execute("SELECT filename FROM files").fetchall()}
        conn.close()

        assert "old.md" not in rows
        assert "existing.md" in rows

    def test_keeps_all_files_when_all_present(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _make_db(db_path, ["a.md", "b.md"])

        with patch("scanner.DB_PATH", db_path):
            cleanup_deleted_files({"a.md", "b.md"})

        conn = sqlite3.connect(db_path)
        rows = {r[0] for r in conn.execute("SELECT filename FROM files").fetchall()}
        conn.close()

        assert rows == {"a.md", "b.md"}

    def test_removes_multiple_deleted_files(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _make_db(db_path, ["x.md", "y.md", "z.md"])

        with patch("scanner.DB_PATH", db_path):
            cleanup_deleted_files(set())

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        conn.close()

        assert count == 0

    def test_noop_on_empty_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        _make_db(db_path, [])

        with patch("scanner.DB_PATH", db_path):
            cleanup_deleted_files({"some.md"})  # should not crash

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        conn.close()
        assert count == 0
