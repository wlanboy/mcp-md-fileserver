# extractor.py

import re
import spacy
import spacy.cli
from functools import lru_cache
from langdetect import detect, LangDetectException
from config import SPACY_MODELS

FALLBACK_MODEL = SPACY_MODELS[0]


def ensure_models():
    """Prüft ob alle konfigurierten spaCy-Modelle installiert sind und lädt fehlende herunter."""
    for model_name in SPACY_MODELS:
        if spacy.util.is_package(model_name):
            print(f"[OK] spaCy-Modell '{model_name}' vorhanden")
            continue
        print(f"[Download] spaCy-Modell '{model_name}' wird heruntergeladen...")
        try:
            spacy.cli.download(model_name)  # type: ignore[attr-defined]
            print(f"[Download] '{model_name}' erfolgreich installiert")
        except SystemExit:
            print(f"[Warnung] spaCy-Modell '{model_name}' konnte nicht installiert werden, überspringe")


@lru_cache(maxsize=8)
def _load_model(model_name: str):
    """Lädt und cached ein spaCy-Modell. Gibt None zurück, wenn das Modell nicht installiert ist."""
    try:
        return spacy.load(model_name)
    except OSError:
        return None


def _get_nlp(language: str | None = None):
    """Gibt das passende spaCy-Modell für die Sprache zurück, mit Fallback.
    Durchsucht alle konfigurierten Modelle nach passendem Sprachprefix.
    """
    if language and language != "unknown":
        for model_name in SPACY_MODELS:
            if model_name.startswith(f"{language}_"):
                model = _load_model(model_name)
                if model:
                    return model
    model = _load_model(FALLBACK_MODEL)
    if not model:
        raise RuntimeError(f"[Fehler] Fallback-Modell '{FALLBACK_MODEL}' konnte nicht geladen werden")
    return model


def detect_language(text: str) -> str:
    """Erkennt die Sprache des Textes. Gibt den ISO-639-1-Code zurück (z.B. 'en', 'de')."""
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def _strip_markdown(text: str) -> str:
    """Entfernt Markdown-Syntax, die die NLP-Verarbeitung stört."""
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # Heading-Marker
    text = re.sub(r"```[\s\S]*?```", "", text)  # Code-Blöcke
    text = re.sub(r"`[^`]+`", "", text)  # Inline-Code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Links → nur Text
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)  # Bold/Italic
    return text


def _token_keyword(token) -> str:
    """Gibt das normalisierte Keyword für einen Token zurück.
    Eigennamen (PROPN) behalten die Originalform,
    da Lemmatisierung bei Fachbegriffen oft fehlerhaft ist.
    """
    if token.pos_ == "PROPN":
        return token.text.lower()
    return token.lemma_.lower()


def _deduplicate_keywords(keywords: set[str]) -> set[str]:
    """Entfernt fehlerhafte Kurz-Lemmata, wenn eine längere Variante existiert.
    Z.B. 'kubernet' wird entfernt wenn 'kubernetes' vorhanden ist.
    """
    to_remove = set()
    sorted_kw = sorted(keywords, key=len)
    for i, short in enumerate(sorted_kw):
        if len(short) < 4:
            continue
        for long in sorted_kw[i + 1:]:
            if long.startswith(short) and len(long) - len(short) <= 3:
                to_remove.add(short)
                break
    return keywords - to_remove


def extract_keywords(text: str, language: str | None = None) -> list[str]:
    """
    Extrahiert Stichwörter aus dem Text:
    - Alle Nomen und Eigennamen (NOUN, PROPN) aus dem gesamten Text
    - Alle bedeutungstragenden Wörter aus Markdown-Überschriften
    - ROOT-Verben für Hauptaktionen
    Wählt automatisch das passende spaCy-Modell anhand der Sprache.
    """
    nlp = _get_nlp(language)
    keywords = set()

    # 1. Wörter aus Markdown-Überschriften extrahieren (hohe Relevanz)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip()
            if not heading_text:
                continue
            heading_doc = nlp(heading_text)
            for token in heading_doc:
                if token.is_stop or token.is_punct or token.is_space or len(token.text) <= 1:
                    continue
                if token.pos_ in {"NOUN", "PROPN", "VERB", "ADJ"}:
                    keywords.add(_token_keyword(token))

    # 2. Stichwörter aus dem gesamten Text extrahieren (Markdown-Syntax bereinigt)
    doc = nlp(_strip_markdown(text))
    for token in doc:
        if token.is_stop or token.is_punct or token.is_space or len(token.text) <= 1:
            continue
        # Alle Nomen und Eigennamen (ohne Dependency-Filter)
        if token.pos_ in {"NOUN", "PROPN"}:
            keywords.add(_token_keyword(token))
        # Nur ROOT-Verben (Hauptverben)
        elif token.pos_ == "VERB" and token.dep_ == "ROOT":
            keywords.add(_token_keyword(token))

    return sorted(_deduplicate_keywords(keywords))
