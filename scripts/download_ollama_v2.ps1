# Robust parallel downloader for OllamaSetup.exe (ASCII only to avoid PS5 encoding issues)
# Strategy: gh-proxy mirror + 8 parallel range segments + resume + retry + size/signature verification

$ErrorActionPreference = 'Continue'

$Remotes = @(
    "https://gh-proxy.org/https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe",
    "https://gh-proxy.com/https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe",
    "https://ghproxy.net/https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
)
$FileSize = 1676266440
$Parts    = 8
$Root     = Join-Path $PSScriptRoot "..\downloads"
$PartsDir = Join-Path $Root "parts"
$Dest     = Join-Path $Root "OllamaSetup.exe"
$Log      = Join-Path $Root "download.log"

New-Item -ItemType Directory -Force -Path $PartsDir | Out-Null
Remove-Item $Dest -Force -ErrorAction SilentlyContinue

function Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8
}

$Seg = [math]::Ceiling($FileSize / $Parts)
function Range($i) {
    $s = [long]$i * $Seg
    $e = [math]::Min($s + $Seg - 1, $FileSize - 1)
    @($s, $e)
}

function PartPath($i) { Join-Path $PartsDir ("part_{0}" -f $i) }
function PartLen($i) {
    $p = PartPath $i
    if (Test-Path $p) { (Get-Item $p).Length } else { 0 }
}

Log "Start download: $FileSize bytes, $Parts segments"

$MaxRounds = 60
for ($round = 1; $round -le $MaxRounds; $round++) {
    $tasks = @()
    for ($i = 0; $i -lt $Parts; $i++) {
        $r = Range $i
        $expect = $r[1] - $r[0] + 1
        $have = PartLen $i
        if ($have -eq $expect) { continue }
        if ($have -gt $expect) {
            $fs = [System.IO.File]::Open((PartPath $i), 'Open', 'Write')
            $fs.SetLength(0); $fs.Close()
            $have = 0
        }
        $from = $r[0] + $have
        $to = $r[1]
        $tasks += , @($i, $from, $to, $have, $expect)
    }

    if ($tasks.Count -eq 0) { Log "Round ${round}: all segments complete"; break }

    $remote = $Remotes[($round - 1) % $Remotes.Count]
    Log ("Round {0}: {1} segment(s) pending from {2}" -f $round, $tasks.Count, ([uri]$remote).Host)

    $sumBefore = 0
    for ($i = 0; $i -lt $Parts; $i++) { $sumBefore += PartLen $i }

    $args = @("--parallel", "--parallel-max", "$Parts", "-sS", "-L",
              "--retry", "3", "--retry-delay", "3", "--retry-all-errors",
              "--connect-timeout", "20", "--max-time", "600",
              "--speed-time", "60", "--speed-limit", "8000")
    foreach ($t in $tasks) {
        $args += @("-r", ("{0}-{1}" -f $t[1], $t[2]), "-o", ((PartPath $t[0]) + ".chunk"), $remote)
    }
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & curl.exe @args 2>$null | Out-Null
    $sw.Stop()

    # append chunks to part files
    foreach ($t in $tasks) {
        $i = $t[0]; $chunk = (PartPath $i) + ".chunk"
        if (Test-Path $chunk) {
            $clen = (Get-Item $chunk).Length
            if ($clen -gt 0) {
                $outFs = [System.IO.File]::Open((PartPath $i), 'Append', 'Write')
                $inFs = [System.IO.File]::OpenRead($chunk)
                $inFs.CopyTo($outFs)
                $inFs.Close(); $outFs.Close()
            }
            Remove-Item $chunk -Force
        }
    }

    $sumAfter = 0
    for ($i = 0; $i -lt $Parts; $i++) { $sumAfter += PartLen $i }
    $delta = $sumAfter - $sumBefore
    $rate = if ($sw.Elapsed.TotalSeconds -gt 0) { $delta / 1MB / $sw.Elapsed.TotalSeconds } else { 0 }
    $totalMB = [math]::Round($sumAfter / 1MB, 1)
    $pct = [math]::Round($sumAfter / $FileSize * 100, 1)
    Log ("Progress {0} MB / 1598.6 MB ({1}%), this round +{2} MB, avg {3} MB/s" -f $totalMB, $pct, [math]::Round($delta/1MB,1), [math]::Round($rate,2))

    if ($delta -lt 1048576) { Start-Sleep -Seconds 5 }
}

# verify segments
$bad = 0
for ($i = 0; $i -lt $Parts; $i++) {
    $r = Range $i
    $expect = $r[1] - $r[0] + 1
    $have = PartLen $i
    if ($have -ne $expect) { $bad++; Log ("Segment {0} incomplete: {1}/{2}" -f $i, $have, $expect) }
}
if ($bad -gt 0) { Log "NOT FINISHED ($bad segments). Re-run this script to resume."; exit 1 }

Log "Assembling..."
$out = [System.IO.File]::Create($Dest)
for ($i = 0; $i -lt $Parts; $i++) {
    $in = [System.IO.File]::OpenRead((PartPath $i))
    $in.CopyTo($out)
    $in.Close()
    Remove-Item (PartPath $i) -Force
}
$out.Close()

$final = (Get-Item $Dest).Length
if ($final -ne $FileSize) { Log ("Size mismatch: {0} != {1}" -f $final, $FileSize); exit 1 }
Remove-Item -Recurse -Force $PartsDir -ErrorAction SilentlyContinue
Log ("Download complete: {0} MB" -f [math]::Round($final/1MB,1))

$sig = Get-AuthenticodeSignature $Dest
Log ("Signature status: " + $sig.Status)
if ($sig.SignerCertificate) {
    Log ("Signed by: " + $sig.SignerCertificate.Subject)
}
if ($sig.Status -ne "Valid") { Log "WARNING: signature invalid - do not run this installer"; exit 1 }
Log "VERIFIED: installer is authentic (valid Authenticode signature)"
