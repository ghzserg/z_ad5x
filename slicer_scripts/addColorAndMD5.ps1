# Translated from Python file by Google Gemini AI. Tested by Namida Verasche (ninjamida).param([string]$filePath)

if (-not $filePath -or -not (Test-Path $filePath)) {
    Write-Error "Usage: .\addColorAndMD5.ps1 <file_path>"
    exit 1
}

# 1. Load file
$content = [System.Collections.Generic.List[string]]::new([System.IO.File]::ReadAllLines($filePath))

# 2. Remove leading MD5 if it exists
if ($content.Count -gt 0 -and $content[0].ToLower().StartsWith("; md5")) {
    $content.RemoveAt(0)
}

# 3. Initialize variables
$result_colors = @()
$highest_result_color = -1
$filament_color_line = ""
$filament_type_line = ""
$header_end_line = -1
$remove_existing_line = -1
$found_header_end_line = $false
$found_existing_line = $false

# 4. Process lines (Matching the logic of your working PS1 script)
for ($i = 0; $i -lt $content.Count; $i++) {
    $line_raw = $content[$i]
    $line = $line_raw.Trim().ToLower()

    if (-not $found_header_end_line) { $header_end_line++ }
    if (-not $found_existing_line) { $remove_existing_line++ }

    if ($line.Length -eq 0) { continue }

    # Detect Tool changes
    if ($line.StartsWith("t")) {
        if ($line -match '^t(\d+)') {
            $index = [int]$matches[1]
            if ($index -notin $result_colors) { $result_colors += $index }
            if ($index -gt $highest_result_color) { $highest_result_color = $index }
        }
    }

    # Detect Filament and Metadata lines
    if ($line.StartsWith(";")) {
        if ($line.StartsWith("; filament_colour =")) {
            $filament_color_line = $line_raw.Split('=', 2)[1].Trim()
        }
        elseif ($line.StartsWith("; filament_type =")) {
            $filament_type_line = $line_raw.Split('=', 2)[1].Trim()
        }
        elseif ($line.StartsWith("; zmod_color_data =")) {
            $found_existing_line = $true
        }
        elseif ($line.StartsWith("; header_block_end")) {
            $found_header_end_line = $true
            # Note: We continue to end to ensure we find the existing zmod line if it is after the header
        }
    }
}

# 5. Prepare data strings
$filament_colors = @()
if ($filament_color_line -ne "") { $filament_colors = $filament_color_line.Split(';') | ForEach-Object { $_.Trim() } }
$filament_types = @()
if ($filament_type_line -ne "") { $filament_types = $filament_type_line.Split(';') | ForEach-Object { $_.Trim() } }

if ($result_colors.Count -eq 0) {
    $result_colors = @(0)
    $highest_result_color = 0
}

# 6. Pad arrays
while ($filament_colors.Count -le $highest_result_color) { $filament_colors += "" }
while ($filament_types.Count -le $highest_result_color) { $filament_types += "" }

$tool_indexes_string = ($result_colors | Sort-Object) -join ","
$filament_color_string = $filament_colors[0..$highest_result_color] -join ","
$filament_type_string = $filament_types[0..$highest_result_color] -join ","

# 7. Apply modifications
if (-not $found_header_end_line) { $header_end_line = 0 }

$zmod_line = "; zmod_color_data = $tool_indexes_string|$filament_color_string|$filament_type_string"
$content.Insert($header_end_line, $zmod_line)

if ($found_existing_line) {
    $adjusted_remove = $remove_existing_line
    if ($remove_existing_line -ge $header_end_line) { $adjusted_remove++ }
    $content.RemoveAt($adjusted_remove)
}

# 8. MD5 Generation (Binary-Safe Bridge)
# Convert the content back to a string with Windows line endings, matching your Python join logic
$joined_content = ($content -join "`r`n") + "`r`n"
$content_bytes = [System.Text.Encoding]::UTF8.GetBytes($joined_content)

# Calculate MD5
$md5 = [System.Security.Cryptography.MD5]::Create()
$hash_bytes = $md5.ComputeHash($content_bytes)
$hash_string = ($hash_bytes | ForEach-Object { $_.ToString("x2") }) -join ""

# Prepend MD5 header
$md5_header = "; MD5:$hash_string`r`n"
$header_bytes = [System.Text.Encoding]::ASCII.GetBytes($md5_header)

# 9. Final Binary Save
$final_bytes = New-Object byte[] ($header_bytes.Length + $content_bytes.Length)
[Array]::Copy($header_bytes, 0, $final_bytes, 0, $header_bytes.Length)
[Array]::Copy($content_bytes, 0, $final_bytes, $header_bytes.Length, $content_bytes.Length)

[System.IO.File]::WriteAllBytes($filePath, $final_bytes)