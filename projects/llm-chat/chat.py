# -*- coding: utf-8 -*-
"""
第 6 周练习：LLM API 调用（本地 Ollama，免费）
=============================================
运行：
    .\\venv\\Scripts\\python.exe chat.py

规则：只要有一个 TODO 没写完，那个任务就会打印"未完成"，不影响其他任务。
全部写完后三个任务依次跑一遍。
"""

from llm_client import get_client

SYSTEM_PROMPT = "你是一个简洁的中文技术助手。回答不超过 3 句话，尽量用 C 语言类比。"


def task1_single_turn(client, model) -> str:
    """任务 1：单轮问答（非流式）—— 等模型全部生成完，一次性拿到字符串。"""
    # TODO 1
    # 1) 组装 messages：system + user
    #    question = "用一句话解释什么是 Token"
    # 2) resp = client.chat.completions.create(model=model, messages=messages)
    # 3) 返回 resp.choices[0].message.content
    question = "用一句话解释什么是 Token"
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question},]
    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content
    #raise NotImplementedError("TODO 1 未完成")


def task2_stream(client, model) -> None:
    """任务 2：流式输出 —— 像打字机一样边生成边打印。"""
    # TODO 2
    # 1) 同上组装 messages，但 create() 里加 stream=True
    # 2) for chunk in stream: 取 chunk.choices[0].delta.content（可能是 None）
    # 3) print(content, end="", flush=True)
    # 提示：为什么聊天界面必须用流式？想想 first-token 延迟
    question = "用两句话解释什么是上下文窗口"
    messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question},]
    stream = client.chat.completions.create(model=model, messages=messages, stream=True)
    for chunk in stream:
        content = chunk.choices[0].delta.content or ""
        print(content, end="", flush=True)
    print()
    #raise NotImplementedError("TODO 2 未完成")


def task3_multi_turn(client, model) -> None:
    """任务 3：多轮对话 —— 让模型记住前面说过的话。"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("多轮对话开始，输入 /exit 退出")
    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        if not user_input:
            continue
        if user_input == "/exit":
            print("再见！")
            break
        messages.append({"role": "user", "content": user_input})
        resp = client.chat.completions.create(model=model, messages=messages)
        reply = resp.choices[0].message.content
        print(f"助手: {reply}")
        messages.append({"role": "assistant", "content": reply})


def main() -> None:
    client, model = get_client()
    print(f"当前后端模型：{model}\n")

    tasks = [
        ("任务1 单轮问答", task1_single_turn),
        ("任务2 流式输出", task2_stream),
        ("任务3 多轮对话", task3_multi_turn),
    ]
    for title, func in tasks:
        print(f"===== {title} =====")
        try:
            result = func(client, model)
            if result:
                print(result)
        except NotImplementedError as e:
            print(f"[跳过] {e}")
        print()


if __name__ == "__main__":
    main()
