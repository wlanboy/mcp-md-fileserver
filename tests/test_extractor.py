# tests/test_extractor.py

from unittest.mock import patch, MagicMock

from extractor import _strip_markdown, _deduplicate_keywords, _token_keyword, detect_language


class TestStripMarkdown:
    def test_removes_h1_heading(self):
        result = _strip_markdown("# My Title")
        assert result.strip() == "My Title"

    def test_removes_h2_heading(self):
        result = _strip_markdown("## Subtitle")
        assert result.strip() == "Subtitle"

    def test_removes_multiple_heading_levels(self):
        result = _strip_markdown("# H1\n## H2\n### H3")
        assert "#" not in result

    def test_removes_fenced_code_block(self):
        result = _strip_markdown("Text\n```python\nprint('hello')\n```\nAfter")
        assert "```" not in result
        assert "print" not in result

    def test_removes_inline_code(self):
        result = _strip_markdown("Use `docker run` here")
        assert "`" not in result
        assert "docker run" not in result

    def test_replaces_links_with_text(self):
        result = _strip_markdown("[Click here](https://example.com)")
        assert "Click here" in result
        assert "https://example.com" not in result

    def test_removes_bold_double_asterisk(self):
        result = _strip_markdown("**important** text")
        assert "**" not in result
        assert "important" in result

    def test_removes_italic_single_asterisk(self):
        result = _strip_markdown("*emphasis* text")
        assert "*" not in result
        assert "emphasis" in result

    def test_removes_italic_underscore(self):
        result = _strip_markdown("_italic_ text")
        assert "_italic_" not in result
        assert "italic" in result

    def test_plain_text_unchanged(self):
        text = "Hello world, no markdown here."
        assert _strip_markdown(text) == text

    def test_empty_string(self):
        assert _strip_markdown("") == ""


class TestDeduplicateKeywords:
    def test_removes_short_prefix_duplicate(self):
        result = _deduplicate_keywords({"kubernet", "kubernetes"})
        assert "kubernet" not in result
        assert "kubernetes" in result

    def test_keeps_both_when_diff_too_large(self):
        # "docker" len=6, "dockercompose" len=13, diff=7 > 3 → both kept
        result = _deduplicate_keywords({"docker", "dockercompose"})
        assert "docker" in result
        assert "dockercompose" in result

    def test_does_not_remove_short_words(self):
        # "api" len=3 < 4, skip check → both kept
        result = _deduplicate_keywords({"api", "apis"})
        assert "api" in result

    def test_removes_four_char_prefix(self):
        # "test" len=4, "tests" starts with "test", diff=1 ≤ 3 → "test" removed
        result = _deduplicate_keywords({"test", "tests"})
        assert "test" not in result
        assert "tests" in result

    def test_empty_set(self):
        assert _deduplicate_keywords(set()) == set()

    def test_no_overlap_unchanged(self):
        keywords = {"python", "docker", "linux"}
        result = _deduplicate_keywords(keywords)
        assert result == keywords

    def test_keeps_longer_removes_shorter(self):
        result = _deduplicate_keywords({"contain", "container"})
        assert "contain" not in result
        assert "container" in result


class TestTokenKeyword:
    def _make_token(self, pos: str, text: str, lemma: str) -> MagicMock:
        token = MagicMock()
        token.pos_ = pos
        token.text = text
        token.lemma_ = lemma
        return token

    def test_propn_returns_original_text_lowercased(self):
        token = self._make_token("PROPN", "Kubernetes", "Kubernete")
        assert _token_keyword(token) == "kubernetes"

    def test_noun_returns_lemma_lowercased(self):
        token = self._make_token("NOUN", "Containers", "container")
        assert _token_keyword(token) == "container"

    def test_verb_returns_lemma_lowercased(self):
        token = self._make_token("VERB", "Running", "run")
        assert _token_keyword(token) == "run"

    def test_propn_preserves_case_conversion(self):
        token = self._make_token("PROPN", "DOCKER", "docker")
        assert _token_keyword(token) == "docker"


class TestDetectLanguage:
    def test_returns_language_code_on_success(self):
        with patch("extractor.detect", return_value="en"):
            assert detect_language("Hello world") == "en"

    def test_returns_de_for_german_text(self):
        with patch("extractor.detect", return_value="de"):
            assert detect_language("Hallo Welt") == "de"

    def test_returns_unknown_on_lang_detect_exception(self):
        from langdetect import LangDetectException
        with patch("extractor.detect", side_effect=LangDetectException(0, "")):
            assert detect_language("!!!") == "unknown"

    def test_empty_string_returns_unknown(self):
        from langdetect import LangDetectException
        with patch("extractor.detect", side_effect=LangDetectException(0, "")):
            assert detect_language("") == "unknown"
