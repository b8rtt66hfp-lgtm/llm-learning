# -*- coding: utf-8 -*-
"""
LLM 客户端工厂（已写好的参考代码，不用改）
==========================================
核心思想：Ollama 和 DeepSeek 都兼容 OpenAI 协议，
所以同一套 SDK 代码只换 base_url / api_key 就能切换后端。
类比 C：同一个函数指针接口，运行时换不同的实现。
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).parent


def get_client() -> tuple[OpenAI, str]:
    """返回 (client, 模型名)。根据 .env 里的 LLM_PROVIDER 决定连哪个后端。"""
    load_dotenv(HERE / ".env")
    load_dotenv(HERE.parent.parent / ".env")  # 根目录 .env 里的 DEEPSEEK_API_KEY

    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

    if provider == "deepseek":
        key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not key or key == "你的key粘贴在这里":
            raise RuntimeError("根目录 .env 里的 DEEPSEEK_API_KEY 还没填真实 key")
        return (
            OpenAI(api_key=key, base_url="https://api.deepseek.com"),
            os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        )

    # 默认走本地 Ollama。api_key 随便填，Ollama 不校验
    return (
        OpenAI(
            api_key="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ),
        os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
    )
