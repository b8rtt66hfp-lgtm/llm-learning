"""
机械工程助手 — 统一 API 网关

用法：
    # 先确保 Ollama 跑着（默认 http://localhost:11434）
    ollama serve            # 或启动 ollama app.exe
    ollama create mechatronics-assistant -f ollama/Modelfile

    # 启动网关
    .\\venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

接口：
    GET  /health                        健康检查（同时探测 Ollama 是否可达）
    POST /chat                          非流式，返回完整回答 JSON
    POST /chat/stream                   流式，SSE 格式逐 token 输出

请求体（/chat 和 /chat/stream 通用）：
    {
        "message": "键连接的作用是什么？",
        "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
        "system_override": "可选，覆盖默认 system prompt"
    }
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mechatronics-assistant")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "60"))

DEFAULT_SYSTEM = (
    "你是一名资深机械电子工程师助手。"
    "回答范围包括机械设计、机械原理、公差配合、材料与热处理、液压/气动、PLC/传感器。"
    "风格简洁直接，必要时分点列出，优先国际单位制与主流标准代号。"
    "涉及安全/强度/寿命计算时提醒仅供参考。不确定的地方明确说不确定。"
)


# ---------------------------------------------------------------------------
# 生命周期：启动时探活一次 Ollama
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=5.0) as hc:
        try:
            r = await hc.get(f"{OLLAMA_URL}/api/tags")
            app.state.ollama_ok = (r.status_code == 200)
        except Exception:
            app.state.ollama_ok = False
    yield


app = FastAPI(
    title="机械工程助手 API",
    description="基于 Ollama 的本地 LLM 网关",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = Field(default_factory=list)
    system_override: str | None = None


class ChatResponse(BaseModel):
    model: str
    reply: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    """本地 + Ollama 双层健康检查。"""
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as hc:
            r = await hc.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = (r.status_code == 200)
    except Exception:
        pass

    local = True
    return {
        "local": local,
        "ollama": ollama_ok,
        "ollama_url": OLLAMA_URL,
        "model": MODEL_NAME,
    }


def _build_messages(req: ChatRequest) -> list[dict]:
    msgs: list[dict] = []
    system = req.system_override or DEFAULT_SYSTEM
    msgs.append({"role": "system", "content": system})
    for m in req.history:
        msgs.append({"role": m.role, "content": m.content})
    msgs.append({"role": "user", "content": req.message})
    return msgs


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    msgs = _build_messages(req)
    payload = {
        "model": MODEL_NAME,
        "messages": msgs,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as hc:
            r = await hc.post(f"{OLLAMA_URL}/api/chat", json=payload)
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Ollama 不可达，先执行 `ollama serve`")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Ollama 错误：{e}")

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ollama {r.status_code}: {r.text[:300]}")

    body = r.json()
    reply = body.get("message", {}).get("content", "").strip()
    # Ollama 非流式把 usage 平铺在顶层，不是嵌套在 usage 里
    return ChatResponse(
        model=body.get("model", MODEL_NAME),
        reply=reply,
        prompt_tokens=body.get("prompt_eval_count"),
        completion_tokens=body.get("eval_count"),
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    msgs = _build_messages(req)
    payload = {
        "model": MODEL_NAME,
        "messages": msgs,
        "stream": True,
    }

    async def gen() -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as hc:
                async with hc.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as r:
                    if r.status_code != 200:
                        err = await r.aread()
                        yield f"data: {json.dumps({'error': err.decode()[:300]})}\n\n"
                        return
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            body = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        chunk = body.get("message", {}).get("content", "")
                        if chunk:
                            yield f"data: {json.dumps({'content': chunk})}\n\n"
                        if body.get("done"):
                            usage = body.get("usage") or {}
                            yield f"data: {json.dumps({'done': True, 'usage': usage})}\n\n"
        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': 'Ollama 不可达'})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
