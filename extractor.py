# extractor.py

import spacy
from config import NLP_MODEL

# Lade das spaCy-Modell aus der Konfiguration
try:
    nlp = spacy.load(NLP_MODEL)
except Exception as e:
    raise RuntimeError(f"[Fehler] spaCy-Modell '{NLP_MODEL}' konnte nicht geladen werden: {e}")

def extract_keywords(text, model=None):
    """
    Extrahiert lemmatisierte Stichwörter (nur Subjekte & Verben) aus dem Text.
    Optional kann ein anderes spaCy-Modell übergeben werden.
    """
    doc = (spacy.load(model)(text) if model else nlp(text))
    keywords = set()

    for token in doc:
        if token.pos_ in {"VERB", "NOUN"} and token.dep_ in {"nsubj", "ROOT"}:
            keywords.add(token.lemma_)

    return sorted(keywords)
