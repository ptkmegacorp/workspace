#!/bin/bash
# rename-images.sh - Renames image files in a directory with a sequential prefix
# Usage: ./rename-images.sh <directory> [prefix]
# Example: ./rename-images.sh ./photos vacation

set -euo pipefail

DIR="${1:-.}"
PREFIX="${2:-img}"

if [[ ! -d "$DIR" ]]; then
    echo "Error: Directory '$DIR' does not exist"
    exit 1
fi

# Find images, sort them, and rename with sequential numbers
# Supports: jpg, jpeg, png, gif, webp, bmp
find "$DIR" -type f \( \
    -iname "*.jpg" -o \
    -iname "*.jpeg" -o \
    -iname "*.png" -o \
    -iname "*.gif" -o \
    -iname "*.webp" -o \
    -iname "*.bmp" \
\) | sort | while read -r file; do
    ext="${file##*.}"
    newname="${PREFIX}_$(date +%Y%m%d_%H%M%S)_$(basename "$file" ".$ext").$ext"
    mv -v "$file" "$(dirname "$file")/$newname"
    echo "Renamed: $(basename "$file") -> $newname"
done

echo "Done! Renamed image files in $DIR"
