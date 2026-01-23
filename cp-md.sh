#!/bin/bash

SOURCE_DIR="/home/samuel"
TARGET_DIR="/markdowns"

# Zielverzeichnis erstellen, falls es nicht existiert
mkdir -p "$TARGET_DIR"

# Alle .md-Dateien rekursiv finden, versteckte Ordner ausschließen
find "$SOURCE_DIR" -type d -name ".*" -prune -o -type f -name "*.md" -print | while read -r file; do
  filename="$(basename "$file")"
  target_path="$TARGET_DIR/$filename"

  # Namenskonflikte vermeiden
  if [ -e "$target_path" ]; then
    timestamp=$(date +%s)
    target_path="$TARGET_DIR/${timestamp}_$filename"
    echo "⚠️ Datei existiert bereits – kopiere als: $target_path"
  fi

  cp "$file" "$target_path"
  echo "📄 Kopiert: $file → $target_path"
done

echo "✅ Alle Markdown-Dateien wurden erfolgreich nach $TARGET_DIR kopiert (ohne versteckte Ordner)."
