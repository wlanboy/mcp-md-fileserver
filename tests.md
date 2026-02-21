tests/test_extractor.py – 23 Tests

TestStripMarkdown (11): Headings, Code-Blöcke, Inline-Code, Links, Bold/Italic
TestDeduplicateKeywords (7): Prefix-Duplikate, Mindestlänge, keine Überschneidung
TestTokenKeyword (4): PROPN vs. NOUN/VERB, Großschreibung
TestDetectLanguage (4): Erfolg, LangDetectException, leerer String
tests/test_tools.py – 21 Tests via MockApp-Pattern (fängt die registrierten Closures ab)

TestSearchByKeywords (6): Match, kein Match, Sprachfilter, URI, Case-insensitiv
TestListAllFiles (4): alle Dateien, Sprachfilter, URI, Keywords
TestListAllKeywords (3): Zählung, Sprachfilter, Sortierung
TestFulltextSearch (8): Match, Preview, Sprach­filter, Sortierung nach Trefferzahl
TestGetFileByName (4): Inhalt aus DB, nicht gefunden, leerer Name, Fallback-Fehler
tests/test_scanner.py – 10 Tests

TestScanMarkdownFiles (6): nur .md-Dateien, Rekursion, Aufrufzählung, Fehlertoleranz
TestCleanupDeletedFiles (4): Löschen, Behalten, alle löschen, leere DB
tests/test_db.py – 12 Tests

TestMigrateColumns (3): fehlende Spalten, Idempotenz
TestInitDb (4): Tabelle, alle Spalten, Idempotenz, Parent-Dir erstellen
TestUpdateFileEntry (5): Einfügen, Update bei mtime-Änderung, Überspringen, Content speichern, Fehlertoleranz