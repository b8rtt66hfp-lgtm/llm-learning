"""
本地语音助手 — HTTP 服务层

把 voice_assistant.py 的 ASR / LLM 能力暴露成 HTTP 接口，方便前端、其他设备调用。

接口：
    GET  /health    健康检查（Ollama 是否可达、ASR 模型是否就绪）
    POST /chat      文字问答（带多轮上下文）
    POST /voice     上传 wav → ASR → LLM → 返回识别文本 + 回答
    GET  /          极简网页测试页（文字问答 + 上传音频）

启动（在 projects/voice-assistant 目录下）：
    .\\venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
或者直接：.\\start.ps1
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

# 让本文件能 import 上级目录的 voice_assistant.py
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from voice_assistant import clean_asr_text, find_asr_model_dir, llm_reply, tts_sapi  # noqa: E402

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mechatronics-assistant")


# ---------------------------------------------------------------------------
# ASR 模型路径查找 + 懒加载单例
# ---------------------------------------------------------------------------

ASR_MODEL_DIR = os.getenv("ASR_MODEL_DIR") or find_asr_model_dir()
_asr_model = None


def transcribe(audio_path: str) -> str:
    """同步 ASR：首次调用加载模型（~1s），后续复用单例。"""
    global _asr_model
    if not ASR_MODEL_DIR:
        raise RuntimeError("找不到 ASR 模型目录，请先下载模型或设置 ASR_MODEL_DIR")
    if _asr_model is None:
        from funasr_onnx import Paraformer
        _asr_model = Paraformer(ASR_MODEL_DIR, batch_size=1, quantize=True)
    result = _asr_model([audio_path])
    return result[0]["preds"][0].strip() if result else ""


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = Field(default_factory=list)


class ChatResponse(BaseModel):
    model: str
    reply: str


class VoiceResponse(BaseModel):
    asr_text: str
    reply: str


class TTSRequest(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="本地语音助手 API",
    description="ASR（funasr-onnx）+ LLM（Ollama）本地全链路服务",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as hc:
            r = await hc.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "ollama": ollama_ok,
        "ollama_url": OLLAMA_URL,
        "model": MODEL_NAME,
        "asr_ready": ASR_MODEL_DIR is not None,
        "asr_model_dir": ASR_MODEL_DIR,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    history = [m.model_dump() for m in req.history]
    try:
        # llm_reply 内部是同步 requests，放线程池避免阻塞事件循环
        reply = await run_in_threadpool(llm_reply, req.message, history)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{e}")
    return ChatResponse(model=MODEL_NAME, reply=reply)


@app.post("/voice", response_model=VoiceResponse)
async def voice(file: UploadFile = File(...)) -> VoiceResponse:
    suffix = Path(file.filename or "audio.wav").suffix.lower() or ".wav"
    if suffix != ".wav":
        raise HTTPException(status_code=400, detail="目前只支持 16kHz 单声道 .wav")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        text = await run_in_threadpool(transcribe, tmp_path)
        text = clean_asr_text(text)
        if not text:
            raise HTTPException(status_code=422, detail="ASR 没有识别出有效内容（可能是静音或噪声）")
        reply = await run_in_threadpool(llm_reply, text, None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"语音处理失败：{e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return VoiceResponse(asr_text=text, reply=reply)


@app.post("/tts")
async def tts(req: TTSRequest) -> FileResponse:
    """文字 → 离线语音合成，直接返回 wav 文件（pyttsx3 / Windows SAPI5）。"""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    def _cleanup() -> None:
        try:
            os.unlink(path)
        except OSError:
            pass

    try:
        await run_in_threadpool(tts_sapi, text, path)
    except Exception as e:
        _cleanup()
        raise HTTPException(status_code=502, detail=f"TTS 合成失败：{e}")

    if not os.path.exists(path) or os.path.getsize(path) == 0:
        _cleanup()
        raise HTTPException(status_code=502, detail="TTS 没有生成音频")

    return FileResponse(
        path, media_type="audio/wav", filename="reply.wav",
        background=BackgroundTask(_cleanup),
    )


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>本地语音助手</title>
<style>
  body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:760px;margin:40px auto;padding:0 16px;color:#1f2933}
  h1{font-size:22px}
  section{border:1px solid #e4e7eb;border-radius:10px;padding:16px;margin-bottom:20px}
  input[type=text]{width:100%;padding:10px;border:1px solid #cbd2d9;border-radius:6px;font-size:15px;box-sizing:border-box}
  button{margin-top:10px;padding:9px 18px;border:0;border-radius:6px;background:#2563eb;color:#fff;font-size:15px;cursor:pointer}
  button:disabled{background:#9aa5b1;cursor:default}
  pre{white-space:pre-wrap;background:#f5f7fa;padding:12px;border-radius:6px;min-height:20px;margin:12px 0 0}
</style>
</head>
<body>
<h1>本地语音助手</h1>
<section>
  <h3>文字问答</h3>
  <input id="q" type="text" placeholder="例如：键连接的作用是什么？">
  <button id="send">发送</button>
  <button id="play" disabled>朗读回答</button>
  <audio id="player" controls style="display:block;margin-top:10px;width:100%"></audio>
  <pre id="a1"></pre>
</section>
<section>
  <h3>语音问答</h3>
  <input id="f" type="file" accept=".wav,audio/wav">
  <button id="sendv">识别并回答</button>
  <pre id="a2"></pre>
</section>
<script>
async function post(url, body) {
  const r = await fetch(url, {method:'POST', body});
  return r.json();
}
let lastReply = '';
document.getElementById('send').onclick = async () => {
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  const out = document.getElementById('a1');
  out.textContent = '思考中...';
  try {
    const j = await post('/chat', JSON.stringify({message:q}));
    lastReply = j.reply || '';
    out.textContent = lastReply || JSON.stringify(j);
    document.getElementById('play').disabled = !lastReply;
  } catch (e) { out.textContent = '请求失败：' + e; }
};
document.getElementById('play').onclick = async () => {
  if (!lastReply) return;
  const btn = document.getElementById('play');
  btn.disabled = true;
  try {
    const r = await fetch('/tts', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: lastReply})
    });
    if (!r.ok) throw new Error(await r.text());
    const player = document.getElementById('player');
    player.src = URL.createObjectURL(await r.blob());
    player.play();
  } catch (e) { alert('朗读失败：' + e); }
  finally { btn.disabled = false; }
};
document.getElementById('sendv').onclick = async () => {
  const f = document.getElementById('f').files[0];
  if (!f) return;
  const out = document.getElementById('a2');
  out.textContent = '识别中...';
  const fd = new FormData(); fd.append('file', f);
  try {
    const j = await post('/voice', fd);
    out.textContent = j.asr_text ? ('识别：' + j.asr_text + '\\n\\n回答：' + j.reply) : JSON.stringify(j);
  } catch (e) { out.textContent = '请求失败：' + e; }
};
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return INDEX_HTML
