# extractor.py

import spacy
from functools import lru_cache
from config import NLP_MODEL


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    """Lädt und cached ein spaCy-Modell."""
    try:
        return spacy.load(model_name)
    except Exception as e:
        raise RuntimeError(f"[Fehler] spaCy-Modell '{model_name}' konnte nicht geladen werden: {e}")


# Standard-Modell beim Import laden
_default_nlp = _load_model(NLP_MODEL)


def extract_keywords(text: str, model: str | None = None) -> list[str]:
    """
    Extrahiert lemmatisierte Stichwörter (nur Subjekte & Verben) aus dem Text.
    Optional kann ein anderes spaCy-Modell übergeben werden.
    """
    nlp = _load_model(model) if model else _default_nlp
    doc = nlp(text)
    keywords = set()

    for token in doc:
        if token.pos_ in {"VERB", "NOUN"} and token.dep_ in {"nsubj", "ROOT"}:
            keywords.add(token.lemma_)

    return sorted(keywords)
