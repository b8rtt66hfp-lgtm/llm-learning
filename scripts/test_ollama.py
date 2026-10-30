# -*- coding: utf-8 -*-
"""
Ollama 本地模型测试脚本
========================
用途：验证 Ollama 部署是否成功，并演示三种最常见的调用方式。

运行前提：
    1. Ollama 服务已启动（默认 http://localhost:11434）
    2. 已拉取模型：ollama pull qwen2.5:1.5b
    3. 安装 requests：pip install requests

运行方式：
    python test_ollama.py
"""

import json
import sys

import requests

BASE_URL = "http://localhost:11434"
MODEL = "qwen2.5:1.5b"  # 没有这个模型就改成 ollama list 里已有的名字


def check_server() -> bool:
    """方式 0：检查 Ollama 服务是否在运行"""
    try:
        r = requests.get(f"{BASE_URL}/api/version", timeout=5)
        print(f"[OK] Ollama 服务正常，版本: {r.json()['version']}")
        return True
    except requests.ConnectionError:
        print("[失败] 连不上 Ollama 服务，请先启动：")
        print('    Start-Process "$env:LOCALAPPDATA\\Programs\\Ollama\\ollama.exe" -ArgumentList "serve"')
        return False


def native_generate(prompt: str) -> str:
    """方式 1：原生 /api/generate 接口（单轮补全）"""
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    r = requests.post(f"{BASE_URL}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["response"]


def openai_style_chat(messages: list) -> str:
    """方式 2：OpenAI 兼容接口 /v1/chat/completions（重点掌握！）"""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }
    # 注意：api_key 随便填，Ollama 不校验；base_url 是 /v1
    headers = {"Authorization": "Bearer ollama", "Content-Type": "application/json"}
    r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def stream_chat(messages: list):
    """方式 3：流式输出（打字机效果，聊天应用必备）"""
    payload = {"model": MODEL, "messages": messages, "stream": True}
    with requests.post(f"{BASE_URL}/api/chat", json=payload, stream=True, timeout=180) as r:
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line.decode("utf-8"))
            content = chunk.get("message", {}).get("content", "")
            print(content, end="", flush=True)
            if chunk.get("done"):
                break
    print()


def main():
    if not check_server():
        sys.exit(1)

    print("\n===== 测试 1：原生 generate 接口 =====")
    answer = native_generate("用一句话解释什么是大语言模型")
    print(f"模型回答: {answer}")

    print("\n===== 测试 2：OpenAI 兼容 chat 接口 =====")
    messages = [
        {"role": "system", "content": "你是一个简洁的中文技术助手，回答不超过两句话。"},
        {"role": "user", "content": "什么是 RAG？"},
    ]
    answer = openai_style_chat(messages)
    print(f"模型回答: {answer}")

    print("\n===== 测试 3：流式输出（打字机效果）=====")
    stream_chat(messages + [{"role": "user", "content": "再详细一点介绍 RAG 的流程"}])

    print("\n===== 全部测试通过！Ollama 部署成功 =====")


if __name__ == "__main__":
    main()
