#!/bin/bash

# Gemini AI translation of addColorAndMD5.py to Bash

FILE_PATH="$1"

# Ensure a file was provided
if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
    echo "Usage: $0 <gcode_file>"
    exit 1
fi

# 1. Load content and remove existing MD5/zmod lines
# We use a temporary file to hold the intermediate state
TEMP_CONTENT=$(mktemp)

# Filter out existing MD5 and zmod_color_data lines (case-insensitive)
# We also ensure the line endings match the CRLF expected in G-code
grep -viE '^; (MD5:|zmod_color_data =)' "$FILE_PATH" > "$TEMP_CONTENT"

# 2. Extract Tool Numbers (Lines starting with T followed by digits)
# Note: Python script looks for lines starting with 't'
TOOL_IDS=$(grep -iE '^T[0-9]+' "$TEMP_CONTENT" | sed -E 's/^[Tt]([0-9]+).*/\1/' | sort -nu | paste -sd "," -)

# Default to 0 if no tools are found (per Python logic)
if [[ -z "$TOOL_IDS" ]]; then TOOL_IDS="0"; fi

# 3. Extract Filament Colors and Types
# Python splits by ';' and then joins by ','
FILAMENT_COLOURS=$(grep -i "^; filament_colour =" "$TEMP_CONTENT" | cut -d'=' -f2- | tr -d ' ' | tr ';' ',')
FILAMENT_TYPES=$(grep -i "^; filament_type =" "$TEMP_CONTENT" | cut -d'=' -f2- | tr -d ' ' | tr ';' ',')

# 4. Construct the zmod_color_data line
# Format: ; zmod_color_data = tools|colors|types
ZMOD_LINE="; zmod_color_data = ${TOOL_IDS}|${FILAMENT_COLOURS}|${FILAMENT_TYPES}"

# 5. Insert the zmod line before the Header End
# Python logic: if header_block_end exists, insert before it; otherwise append.
FINAL_TEMP=$(mktemp)
if grep -qi "; HEADER_BLOCK_END" "$TEMP_CONTENT"; then
    # Insert before the line containing HEADER_BLOCK_END
    sed "/; HEADER_BLOCK_END/i $ZMOD_LINE" "$TEMP_CONTENT" > "$FINAL_TEMP"
else
    cat "$TEMP_CONTENT" > "$FINAL_TEMP"
    echo "$ZMOD_LINE" >> "$FINAL_TEMP"
fi

# 6. Calculate MD5 of the content and prepend it
# Use md5sum (Linux) or md5 -q (macOS)
if command -v md5sum >/dev/null; then
    MD5_HASH=$(md5sum "$FINAL_TEMP" | awk '{print $1}')
else
    MD5_HASH=$(md5 -q "$FINAL_TEMP")
fi

# 7. Overwrite the original file
echo "; MD5:${MD5_HASH}" > "$FILE_PATH"
cat "$FINAL_TEMP" >> "$FILE_PATH"

# Cleanup
rm "$TEMP_CONTENT" "$FINAL_TEMP"