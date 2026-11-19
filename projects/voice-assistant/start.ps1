# 一键启动：确认 Ollama → 启动 FastAPI 服务
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root "venv\Scripts\python.exe"

# 1) Ollama 没起来就先拉起来
$ollamaUp = $false
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -UseBasicParsing | Out-Null
    $ollamaUp = $true
} catch { }

if (-not $ollamaUp) {
    Write-Host "[start] Ollama 未运行，正在启动 ..."
    $exe = "C:\Users\26870\AppData\Local\Programs\Ollama\ollama.exe"
    if (Test-Path $exe) {
        Start-Process $exe -ArgumentList "serve" -WindowStyle Hidden
    } else {
        Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    }
    Start-Sleep -Seconds 5
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -UseBasicParsing | Out-Null
        Write-Host "[start] Ollama 就绪"
    } catch {
        Write-Warning "[start] Ollama 仍未就绪，服务启动后 /health 会显示 ollama=false"
    }
} else {
    Write-Host "[start] Ollama 已在运行"
}

# 2) 启动 API 服务
Write-Host "[start] 打开 http://127.0.0.1:8000 使用"
& $python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
