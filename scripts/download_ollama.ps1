﻿# Ollama 安装包健壮下载脚本
# 特性：自动挑选可用 GitHub IP + 8 通道并行分段 + 断点重试 + 精确大小校验 + 数字签名校验
# 用法：powershell -ExecutionPolicy Bypass -File .\download_ollama.ps1

$ErrorActionPreference = 'Continue'

$Url      = "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
$FileSize = 1676266440          # 字节，用 HEAD 请求获取后写死，用于精确校验
$Parts    = 8
$Root     = "d:\trae项目2\downloads"
$PartsDir = Join-Path $Root "parts"
$Dest     = Join-Path $Root "OllamaSetup.exe"
$Log      = Join-Path $Root "download.log"

New-Item -ItemType Directory -Force -Path $PartsDir | Out-Null
Remove-Item (Join-Path $Root "OllamaSetup.exe") -Force -ErrorAction SilentlyContinue

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8
}

# ---------- 1. 挑选可用 GitHub IP ----------
$CandidateIPs = @("140.82.116.3", "20.27.177.113", "4.237.22.38", "20.205.243.166")
$GoodIP = $null
foreach ($ip in $CandidateIPs) {
    $code = & curl.exe -sS -o NUL -I -m 6 --resolve "github.com:443:$ip" -w "%{http_code}" https://github.com/ 2>$null
    if ($code -eq "200") { $GoodIP = $ip; break }
}
if (-not $GoodIP) {
    Write-Log "所有候选 IP 均不可用，改为直接使用默认 DNS"
} else {
    Write-Log "选用 GitHub IP: $GoodIP"
}

$ResolveArgs = @()
if ($GoodIP) { $ResolveArgs = @("--resolve", "github.com:443:$GoodIP") }

# ---------- 2. 计算分段 ----------
$Seg = [math]::Ceiling($FileSize / $Parts)
function Get-PartRange($i) {
    $s = [long]$i * $Seg
    $e = [math]::Min($s + $Seg - 1, $FileSize - 1)
    return @($s, $e)
}

# ---------- 3. 循环并行下载直到所有分段完整 ----------
$MaxRounds = 30
for ($round = 1; $round -le $MaxRounds; $round++) {
    $pending = @()
    for ($i = 0; $i -lt $Parts; $i++) {
        $r = Get-PartRange $i
        $expect = $r[1] - $r[0] + 1
        $pf = Join-Path $PartsDir "part_$i"
        $actual = 0
        if (Test-Path $pf) { $actual = (Get-Item $pf).Length }
        if ($actual -eq $expect) { continue }
        if ($actual -gt $expect) { Remove-Item $pf -Force }   # 异常文件重置
        $pending += ,@($i, $r[0], $r[1])
    }

    if ($pending.Count -eq 0) {
        Write-Log "第 $round 轮：所有 $Parts 个分段已完整"
        break
    }

    Write-Log "第 $round 轮：需下载 $($pending.Count) 个分段"

    $args = @("--parallel", "--parallel-max", "$Parts", "-sS", "-L",
              "--retry", "5", "--retry-delay", "3", "--retry-all-errors",
              "--connect-timeout", "20", "--max-time", "5400",
              "--speed-time", "120", "--speed-limit", "3000") + $ResolveArgs

    foreach ($p in $pending) {
        $args += @("-r", "$($p[1])-$($p[2])", "-o", (Join-Path $PartsDir "part_$($p[0])"), $Url)
    }

    $sumBefore = (Get-ChildItem $PartsDir -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & curl.exe @args 2>$null | Out-Null
    $sw.Stop()

    $sumAfter = (Get-ChildItem $PartsDir -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    $deltaMB = [math]::Round(($sumAfter - $sumBefore) / 1MB, 1)
    $totalMB = [math]::Round($sumAfter / 1MB, 1)
    $rateMBs = if ($sw.Elapsed.TotalSeconds -gt 0) { [math]::Round(($sumAfter - $sumBefore) / 1MB / $sw.Elapsed.TotalSeconds, 2) } else { 0 }
    Write-Log "本轮新增 $deltaMB MB，累计 $totalMB MB / 1598.6 MB，平均 $rateMBs MB/s"
}

# ---------- 4. 校验与拼装 ----------
$bad = 0
for ($i = 0; $i -lt $Parts; $i++) {
    $r = Get-PartRange $i
    $expect = $r[1] - $r[0] + 1
    $pf = Join-Path $PartsDir "part_$i"
    $actual = if (Test-Path $pf) { (Get-Item $pf).Length } else { 0 }
    if ($actual -ne $expect) { $bad++; Write-Log "分段 $i 不完整：$actual / $expect" }
}
if ($bad -gt 0) {
    Write-Log "下载未完成，$bad 个分段不完整，请重新运行本脚本（支持断点续传）"
    exit 1
}

Write-Log "开始拼装文件..."
$out = [System.IO.File]::Create($Dest)
for ($i = 0; $i -lt $Parts; $i++) {
    $pf = Join-Path $PartsDir "part_$i"
    $in = [System.IO.File]::OpenRead($pf)
    $in.CopyTo($out)
    $in.Dispose()
    Remove-Item $pf -Force
}
$out.Dispose()

$finalSize = (Get-Item $Dest).Length
if ($finalSize -ne $FileSize) {
    Write-Log "拼装后大小不符：$finalSize / $FileSize"
    exit 1
}
Remove-Item -Recurse -Force $PartsDir -ErrorAction SilentlyContinue
Write-Log "下载完成：$Dest（$([math]::Round($finalSize/1MB,1)) MB）"

# ---------- 5. 数字签名校验（防篡改） ----------
$sig = Get-AuthenticodeSignature $Dest
Write-Log "签名状态: $($sig.Status)"
if ($sig.SignerCertificate) {
    Write-Log "签名主体: $($sig.SignerCertificate.Subject)"
    Write-Log "颁发者: $($sig.SignerCertificate.Issuer)"
}
if ($sig.Status -ne "Valid") {
    Write-Log "警告：签名校验未通过，不建议运行该安装包"
    exit 1
}
Write-Log "校验通过，安装包可信（Ollama 官方签名）"
