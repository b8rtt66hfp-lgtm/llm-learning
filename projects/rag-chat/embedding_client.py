# -*- coding: utf-8 -*-
"""Ollama Embedding 客户端 —— 拿一段文本 → 返回向量(list[float])"""

import os
import requests

from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")


def embed(text: str) -> list[float]:
    """把一段文本变成向量。返回 list[float]。"""
    r = requests.post(
        f"{OLLAMA_BASE}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["embedding"]


if __name__ == "__main__":
    v = embed("你好世界")
    print(f"模型: {EMBED_MODEL}, 向量维度: {len(v)}, 前 3 个值: {v[:3]}")
