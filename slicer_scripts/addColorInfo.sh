#!/bin/bash

# Translated from Python file by Google Gemini AI. Tested by Namida Verasche (ninjamida).

FILE_PATH="$1"
if [ ! -f "$FILE_PATH" ]; then
    echo "Usage: $0 <file_path>"
    exit 1
fi

# 1. Extraction pass using awk
eval $(awk '
    BEGIN { IGNORECASE=1; highest=-1; header_end=0; existing=-1; found_end=0 }
    {
        line = tolower($0)
        if (!found_end) { header_end = NR }
        if (line ~ /^t[0-9]+/) {
            split(line, a, "t"); idx = a[2] + 0
            colors[idx] = idx
            if (idx > highest) highest = idx
        }
        if (line ~ /^; filament_colour =/) { split($0, a, "="); f_col = a[2] }
        if (line ~ /^; filament_type =/) { split($0, a, "="); f_typ = a[2] }
        if (line ~ /^; zmod_color_data =/) { existing = NR }
        if (line ~ /^; header_block_end/) { found_end = 1 }
    }
    END {
        printf "HIGHEST=%d; F_COL=\"%s\"; F_TYP=\"%s\"; HEADER_END=%d; EXISTING=%d; ", highest, f_col, f_typ, header_end, existing
        printf "RESULT_COLORS=\""; for (i in colors) printf "%s,", i; print "\""
    }
' "$FILE_PATH")

# 2. String formatting and padding
[ "$HIGHEST" -lt 0 ] && HIGHEST=0 && RESULT_COLORS="0,"
RESULT_COLORS=$(echo $RESULT_COLORS | sed 's/,$//' | tr ',' '\n' | sort -n | tr '\n' ',' | sed 's/,$//')

format_filament() {
    local input="$1"
    local count=$((HIGHEST + 1))
    IFS=';' read -r -a array <<< "$input"
    local output=""
    for ((i=0; i<count; i++)); do
        val=$(echo "${array[i]}" | xargs)
        output+="$val,"
    done
    echo "${output%,}"
}

F_COL_STR=$(format_filament "$F_COL")
F_TYP_STR=$(format_filament "$F_TYP")
ZMOD_LINE="; zmod_color_data = $RESULT_COLORS|$F_COL_STR|$F_TYP_STR"

# 3. Apply changes to file
TEMP_FILE=$(mktemp)
awk -v skip=$EXISTING -v ins=$HEADER_END -v txt="$ZMOD_LINE" '
    NR==skip { next }
    NR==ins { print txt }
    { print }
' "$FILE_PATH" > "$TEMP_FILE"

mv "$TEMP_FILE" "$FILE_PATH"
