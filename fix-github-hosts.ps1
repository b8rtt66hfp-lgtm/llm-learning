# 修复 GitHub 网页打不开：把 github.com 指向可连通的官方 IP
#
# 用法（必须以管理员身份运行）：
#   1. Win+X 打开「终端(管理员)」
#   2. 执行： powershell -ExecutionPolicy Bypass -File "d:\trae项目2\fix-github-hosts.ps1"
#
# 说明：只改 hosts 里的 github.com 一条，自动备份原文件，可随时手动恢复 .bak

$ErrorActionPreference = "Stop"

# ---------- 1. 检查管理员权限 ----------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "需要管理员权限。请右键 PowerShell 选择「以管理员身份运行」后重试。" -ForegroundColor Red
    exit 1
}

$hosts = "$env:SystemRoot\System32\drivers\etc\hosts"

# ---------- 2. 依次测试候选 IP，选第一个可通的 ----------
$candidates = @("140.82.112.3", "140.82.113.3", "140.82.114.4", "20.205.243.166")
$working = $null

foreach ($ip in $candidates) {
    Write-Host "测试 $ip ... " -NoNewline
    $ok = Test-NetConnection -ComputerName $ip -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($ok) {
        Write-Host "可通" -ForegroundColor Green
        $working = $ip
        break
    }
    Write-Host "不通" -ForegroundColor DarkGray
}

if (-not $working) {
    Write-Host "所有候选 IP 都不通，可能需要代理/VPN，本次不修改 hosts。" -ForegroundColor Red
    exit 1
}

# ---------- 3. 备份 hosts ----------
Copy-Item -Path $hosts -Destination "$hosts.bak" -Force
Write-Host "已备份到 $hosts.bak"

# ---------- 4. 删除旧的 github.com 映射，写入新映射 ----------
$lines = Get-Content -Path $hosts |
    Where-Object { $_ -notmatch "^\s*[0-9\.]+\s+github\.com\s*$" }
Set-Content -Path $hosts -Value $lines -Encoding UTF8
Add-Content -Path $hosts -Value "`r`n# GitHub fix ($(Get-Date -Format 'yyyy-MM-dd'))`r`n$working github.com" -Encoding UTF8

# ---------- 5. 刷新 DNS 缓存 ----------
ipconfig /flushdns | Out-Null

Write-Host ""
Write-Host "完成：github.com -> $working" -ForegroundColor Green
Write-Host "浏览器重开即可访问 https://github.com"
Write-Host "若以后又打不开，重新运行本脚本即可（会自动重新挑 IP）"
