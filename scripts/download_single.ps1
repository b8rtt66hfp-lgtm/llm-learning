# Single-stream download with resume + official SHA256 verification (ASCII only)
$ErrorActionPreference = 'Continue'

$Url      = "https://gh-proxy.org/https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
$UrlAlt   = "https://gh-proxy.com/https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
$FileSize = 1676266440
$ExpectSHA = "9e3c76e54e7184c68e88a2378b909bf59bbe454f83c076cb4f4a717e946ae719"
$Dest     = Join-Path $PSScriptRoot "..\downloads\OllamaSetup.exe"
$Log      = Join-Path $PSScriptRoot "..\downloads\download2.log"

function Log($m) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8
}

if (Test-Path $Dest) {
    $len = (Get-Item $Dest).Length
    if ($len -ne $FileSize) { Log ("Removing invalid existing file ({0} bytes)" -f $len); Remove-Item $Dest -Force }
}

$Attempt = 0
$MaxAttempts = 40
while ($Attempt -lt $MaxAttempts) {
    $Attempt++
    $have = if (Test-Path $Dest) { (Get-Item $Dest).Length } else { 0 }
    if ($have -eq $FileSize) { break }

    $url = if ($Attempt % 4 -eq 0) { $UrlAlt } else { $Url }
    Log ("Attempt {0}: resume from {1} MB via {2}" -f $Attempt, [math]::Round($have/1MB,1), ([uri]$url).Host)

    if ($have -gt 0) {
        & curl.exe -sS -L -C - -o $Dest --connect-timeout 20 --max-time 1500 --speed-time 45 --speed-limit 20000 --retry 2 --retry-delay 3 $url 2>>$null
    } else {
        & curl.exe -sS -L -o $Dest --connect-timeout 20 --max-time 1500 --speed-time 45 --speed-limit 20000 --retry 2 --retry-delay 3 $url 2>>$null
    }
    $code = $LASTEXITCODE
    $now = if (Test-Path $Dest) { (Get-Item $Dest).Length } else { 0 }
    Log ("Attempt {0} ended (curl={1}): {2} MB / 1598.6 MB" -f $Attempt, $code, [math]::Round($now/1MB,1))

    if ($code -eq 33 -and $now -lt $FileSize) {
        Log "Server does not support resume; restarting from scratch"
        Remove-Item $Dest -Force
    }
    if ($now -eq $FileSize) { break }
    Start-Sleep -Seconds 3
}

if (-not (Test-Path $Dest)) { Log "FAILED: no file"; exit 1 }
$final = (Get-Item $Dest).Length
if ($final -ne $FileSize) { Log ("FAILED: incomplete {0}/{1}" -f $final, $FileSize); exit 1 }

Log "Size OK, verifying SHA256..."
$sha = (Get-FileHash $Dest -Algorithm SHA256).Hash.ToLower()
Log ("SHA256 = " + $sha)
if ($sha -ne $ExpectSHA) {
    Log "HASH MISMATCH vs official sha256sum.txt - file is not authentic"
    exit 1
}
Log "HASH MATCH: file identical to official Ollama release"
