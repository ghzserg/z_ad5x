# Translated from Python file by Google Gemini AI. Tested by Namida Verasche (ninjamida).

param([string]$filePath)

if (-not $filePath -or -not (Test-Path $filePath)) {
    Write-Error "Usage: .\addMD5.ps1 <file_path>"
    exit 1
}

try {
    # 1. Read file as binary bytes to preserve formatting
    $bytes = [System.IO.File]::ReadAllBytes($filePath)
    
    # 2. Check for existing "; MD5:" header (hex: 3b 20 4d 44 35 3a)
    if ($bytes.Count -ge 6 -and 
        $bytes[0] -eq 0x3b -and $bytes[1] -eq 0x20 -and 
        $bytes[2] -eq 0x4d -and $bytes[3] -eq 0x44 -and 
        $bytes[4] -eq 0x35 -and $bytes[5] -eq 0x3a) {
        
        # Find the first newline character (0x0A) and strip the header
        $newlineIdx = [Array]::IndexOf($bytes, [byte]10)
        if ($newlineIdx -ne -1) {
            $bytes = $bytes[($newlineIdx + 1)..($bytes.Count - 1)]
        }
    }

    # 3. Calculate MD5 hash
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $hashBytes = $md5.ComputeHash($bytes)
    $hashString = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""

    # 4. Construct the new header bytes ("; MD5:<hash>\r\n")
    $headerText = "; MD5:$($hashString)`r`n"
    $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($headerText)

    # 5. Combine header and content
    $newBytes = New-Object byte[] ($headerBytes.Count + $bytes.Count)
    [Array]::Copy($headerBytes, 0, $newBytes, 0, $headerBytes.Count)
    [Array]::Copy($bytes, 0, $newBytes, $headerBytes.Count, $bytes.Count)

    # 6. Save back to disk in binary mode
    [System.IO.File]::WriteAllBytes($filePath, $newBytes)

} catch {
    # Exit silently on error to match Python script behavior
    exit 1
}
