# Translated from Python file by Google Gemini AI. Tested by Namida Verasche (ninjamida).param([string]$filePath)

if (-not $filePath -or -not (Test-Path $filePath)) {
    Write-Error "Usage: .\addColorInfo.ps1 <file_path>"
    exit 1
}

# 1. Load file
$content = [System.IO.File]::ReadAllLines($filePath)

# 2. Initialize variables
$result_colors = @()
$highest_result_color = -1
$filament_color_line = ""
$filament_type_line = ""
$header_end_line = -1
$remove_existing_line = -1
$found_header_end_line = $false
$found_existing_line = $false

# 3. Process lines
for ($i = 0; $i -lt $content.Count; $i++) {
    $line_raw = $content[$i]
    $line = $line_raw.Trim().ToLower()

    if (-not $found_header_end_line) { $header_end_line++ }
    if (-not $found_existing_line) { $remove_existing_line++ }

    if ($line.Length -eq 0) { continue }

    # Detect Tool changes
    if ($line.StartsWith("t")) {
        try {
            $indexStr = $line.Substring(1)
            if ($indexStr -match '^\d+') {
                $index = [int]$matches[0]
                if ($index -notin $result_colors) { $result_colors += $index }
                if ($index -gt $highest_result_color) { $highest_result_color = $index }
            }
        } catch {}
    }

    # Detect Filament and Metadata lines
    if ($line.StartsWith(";")) {
        if ($line.StartsWith("; filament_colour =")) {
            $filament_color_line = $line.Split('=')[1].Trim()
        }
        if ($line.StartsWith("; filament_type =")) {
            $filament_type_line = $line.Split('=')[1].Trim()
        }
        if ($line.StartsWith("; zmod_color_data =")) {
            $found_existing_line = $true
        }
        if ($line.StartsWith("; header_block_end")) {
            $found_header_end_line = $true
        }
    }
}

# 4. Prepare data strings
$filament_colors = $filament_color_line.Split(';') | ForEach-Object { $_.Trim() }
$filament_types = $filament_type_line.Split(';') | ForEach-Object { $_.Trim() }

if ($filament_colors.Count -eq 1 -and $filament_colors[0] -eq "") { $filament_colors = @() }
if ($filament_types.Count -eq 1 -and $filament_types[0] -eq "") { $filament_types = @() }

if ($result_colors.Count -eq 0) {
    $result_colors = @(0)
    $highest_result_color = 0
}

# 5. Pad arrays
while ($filament_colors.Count -le $highest_result_color) { $filament_colors += "" }
while ($filament_types.Count -le $highest_result_color) { $filament_types += "" }

$tool_indexes_string = ($result_colors | Sort-Object) -join ","
$filament_color_string = $filament_colors[0..$highest_result_color] -join ","
$filament_type_string = $filament_types[0..$highest_result_color] -join ","

# 6. Apply modifications
if (-not $found_header_end_line) { $header_end_line = 0 }

$output_list = [System.Collections.Generic.List[string]]::new($content)
$zmod_line = "; zmod_color_data = $tool_indexes_string|$filament_color_string|$filament_type_string"
$output_list.Insert($header_end_line, $zmod_line)

if ($found_existing_line) {
    $adjusted_remove = $remove_existing_line
    if ($remove_existing_line -ge $header_end_line) { $adjusted_remove++ }
    $output_list.RemoveAt($adjusted_remove)
}

# 7. Save file
[System.IO.File]::WriteAllLines($filePath, $output_list)