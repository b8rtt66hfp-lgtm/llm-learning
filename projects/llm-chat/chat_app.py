# -*- coding: utf-8 -*-
"""
第 8 周练习：Streamlit 聊天应用
================================
运行（必须先启动 Ollama）：
    Start-Process "$env:LOCALAPPDATA\\Programs\\Ollama\\ollama app.exe"
    .\\venv\\Scripts\\python.exe -m streamlit run chat_app.py --server.port 8501
"""

import streamlit as st

from llm_client import get_client

DEFAULT_SYSTEM = "你是一个简洁的中文技术助手。回答不超过 3 句话。"


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": DEFAULT_SYSTEM}]
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = DEFAULT_SYSTEM
    if "backend_info" not in st.session_state:
        client, model = get_client()
        st.session_state.client = client
        st.session_state.model = model
        st.session_state.backend_info = model


def render_history() -> None:
    """把 session_state 里除了 system 之外的消息全部渲染成气泡。"""
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        with st.chat_message(msg["role"]):
            st.write(msg["content"])


def generate_stream() -> str:
    """流式生成并把完整回复 append 回 messages。"""
    client = st.session_state.client
    model = st.session_state.model

    # system prompt 可能被用户改过 → 重建 messages 的第一条
    msgs = st.session_state.messages.copy()
    msgs[0] = {"role": "system", "content": st.session_state.system_prompt}

    stream = client.chat.completions.create(
        model=model,
        messages=msgs,
        stream=True,
        max_tokens=2048,
    )
    full_text = []
    with st.chat_message("assistant"):
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            full_text.append(delta)
        reply = "".join(full_text).strip()
        st.write(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    return reply


def main() -> None:
    st.set_page_config(page_title="LLM 聊天小应用", page_icon="🤖")
    init_state()

    st.title("🤖 LLM 聊天小应用")
    st.caption(f"后端：本地 Ollama / {st.session_state.model}   （想切 DeepSeek 去 .env 改 LLM_PROVIDER）")

    with st.sidebar:
        st.header("设置")
        new_system = st.text_area(
            "System Prompt",
            value=st.session_state.system_prompt,
            height=120,
        )
        if new_system != st.session_state.system_prompt:
            st.session_state.system_prompt = new_system
            # system prompt 换了，把历史里的第一条同步更新
            st.session_state.messages[0] = {"role": "system", "content": new_system}

        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = [{"role": "system", "content": new_system}]
            st.rerun()

        st.divider()
        st.write(f"消息总数：{len(st.session_state.messages)}")

    render_history()

    # chat_input 返回用户输入的字符串，回车提交
    user_input = st.chat_input("说点什么…")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        generate_stream()


if __name__ == "__main__":
    main()
