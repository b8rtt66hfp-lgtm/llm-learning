# -*- coding: utf-8 -*-
"""
DeepSeek API 聊天脚本（学习用）
================================
演示第二阶段核心技能：调用 LLM API + 多轮对话 + 流式输出。

用法：
    python deepseek_chat.py test   # 单次测试，验证 key 是否有效
    python deepseek_chat.py        # 进入交互式多轮对话（输入 /exit 退出）

密钥读取顺序：
    1. 系统环境变量 DEEPSEEK_API_KEY
    2. 项目根目录 .env 文件
"""

import os
import sys
from pathlib import Path

from openai import OpenAI

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"  # V3 通用模型；推理模型用 deepseek-reasoner


def load_api_key() -> str:
    """优先读环境变量，其次读 .env 文件"""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key and key != "你的key粘贴在这里":
        return key

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key and key != "你的key粘贴在这里":
                    return key

    print("[错误] 未找到有效的 DEEPSEEK_API_KEY")
    print("       请编辑 d:\\trae项目2\\.env 填入你的 key")
    sys.exit(1)


def chat(client: OpenAI, messages: list) -> str:
    """非流式调用，返回完整回答"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=2000,
    )
    return resp.choices[0].message.content


def chat_stream(client: OpenAI, messages: list):
    """流式调用，打字机效果"""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=2000,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)
    print()


def main():
    key = load_api_key()
    client = OpenAI(api_key=key, base_url=BASE_URL)

    # ---- 单次测试模式 ----
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("正在测试 DeepSeek API...")
        messages = [
            {"role": "system", "content": "你是一个简洁的中文助手，回答不超过50字。"},
            {"role": "user", "content": "用一句话介绍你自己"},
        ]
        print("回答:", chat(client, messages))
        print("✅ DeepSeek API 配置成功！")
        return

    # ---- 交互式多轮对话模式 ----
    print("=" * 50)
    print(f"DeepSeek 多轮对话 ({MODEL})   输入 /exit 退出")
    print("=" * 50)
    messages = [{"role": "system", "content": "你是一个乐于助人的中文AI助手。"}]
    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input == "/exit":
            break
        messages.append({"role": "user", "content": user_input})
        print("DeepSeek: ", end="")
        chat_stream(client, messages)
        messages.append({"role": "assistant", "content": "(见上一条流式回复)"})
    print("\n再见！")


if __name__ == "__main__":
    main()
