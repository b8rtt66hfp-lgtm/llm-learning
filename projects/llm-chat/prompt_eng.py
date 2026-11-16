# -*- coding: utf-8 -*-
"""
第 7 周练习：Prompt 工程核心技巧
=================================
三个任务：
    1. System Prompt 对比 —— 同一个问题，换 3 种 system prompt 看差异
    2. Zero-shot vs Few-shot —— 意图识别，给 vs 不给示例
    3. 结构化输出（JSON mode）—— 强制模型返回合法 JSON，用 json.loads 解析

运行：
    .\\venv\\Scripts\\python.exe prompt_eng.py
"""

import json

from llm_client import get_client


def ask(client, model, system: str, user: str, temperature: float = 0.3,
        response_format: dict | None = None) -> str:
    """给你封装好的底层调用，三个任务共用。直接用就行。"""
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=1024,
    )
    if response_format is not None:
        kwargs["response_format"] = response_format
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


# ============================================================
# 任务 1：System Prompt 对比
# ------------------------------------------------------------
# 同一个问题，换 3 种 system prompt 各问一次，观察输出差异。
# 体会：system prompt 是"给模型戴的眼镜"，最高优先级。
# ============================================================
def task1_system_prompt(client, model) -> None:
    question = "用一句话解释大语言模型（LLM）里的 Token 是什么"

    variants = {
        "啰嗦版":   "你是一个非常啰嗦的老师，回答时喜欢打比方、举例子，至少 5 句话。只能围绕 LLM 领域的 Token 展开。",
        "简洁版":   "你是一个极简主义助手，所有回答不超过 15 个字，且不能脱离 LLM 领域。",
        "专家版":   "你是大语言模型领域的专家。回答时严格按三步结构：1) 先给定义；2) 再讲上下游关联；3) 最后提一个最常见的误解。",
    }

    for name, system in variants.items():
        answer = ask(client, model, system, question)
        print(f"=== {name} ===\n{answer}\n")


# ============================================================
# 任务 2：Zero-shot vs Few-shot（意图识别）
# ------------------------------------------------------------
# 给模型一批"用户输入 → 意图"的示例，让它识别新输入的意图。
# 看不给示例时模型会自由发挥，给 3 个示例后输出会稳定在"只想一个意图标签"。
# ============================================================
def task2_few_shot(client, model) -> None:
    examples = [
        ("北京明天多少度？",            "查天气"),
        ("把这段中文翻译成英文",         "翻译"),
        ("帮我写一封请假邮件",          "写作"),
    ]
    new_inputs = [
        "上海后天会下雨吗",
        "把 Python 代码转成 C++",
        "给 HR 写一封辞职信",
    ]

    def build_user_prompt(shots: list[tuple[str, str]], target: str) -> str:
        """把 few-shot 示例 + 待识别输入拼成一个 user prompt。"""
        if not shots:
            return f'请判断下面用户输入的意图（只能从"查天气/翻译/写作"里选一个）：\n"{target}"\n意图：'
        lines = ["下面是一些输入 → 意图的示例："]
        for q, label in shots:
            lines.append(f'输入："{q}" → 意图：{label}')
        lines.append('现在请判断：')
        lines.append(f'输入："{target}" → 意图：')
        return "\n".join(lines)

    system = "你是意图分类器。只能从给定的标签中选择一个作为输出，绝对不能自己发明新标签，也不能做任何解释。"

    print("--- Zero-shot（不给示例）---")
    for text in new_inputs:
        user = build_user_prompt([], text)
        label = ask(client, model, system, user, temperature=0.0)
        print(f"  输入: {text:16} → {label.strip()}")

    print("\n--- Few-shot（给 3 个示例）---")
    for text in new_inputs:
        user = build_user_prompt(examples, text)
        label = ask(client, model, system, user, temperature=0.0)
        print(f"  输入: {text:16} → {label.strip()}")


# ============================================================
# 任务 3：结构化输出（JSON mode）
# ------------------------------------------------------------
# 让模型返回合法 JSON，直接可以用 json.loads 解析成 dict。
# 生产环境必用：后端要给前端一个稳定的字段，不想自己写正则抠。
# ============================================================
def task3_structured_output(client, model) -> None:
    system = (
        "你是一个菜谱解析器。用户给你一段自由文本描述的菜，"
        "你必须输出严格合法的 JSON，字段固定为："
        '{"name": str, "cuisine": str, "ingredients": list[str], "difficulty": "easy|medium|hard"}'
    )
    # Ollama 的 OpenAI 兼容接口支持 response_format={"type":"json_object"}
    json_mode = {"type": "json_object"}

    dish_texts = [
        "番茄炒蛋，家常菜，主要食材番茄和鸡蛋，很容易做",
        "麻婆豆腐，川菜，用到豆腐、牛肉末、郫县豆瓣酱，需要一定厨艺",
    ]

    for text in dish_texts:
        print(f"--- 输入：{text} ---")
        answer = ask(client, model, system, text,
                     response_format=json_mode, temperature=0.0)
        try:
            result = json.loads(answer)
            print(f"解析成功：{result}\n")
        except json.JSONDecodeError as e:
            print(f"[警告] 模型没返回合法 JSON：{answer}")
            print(f"       解析错误：{e}\n")


def main() -> None:
    client, model = get_client()
    print(f"当前后端模型：{model}\n")

    tasks = [
        ("任务1 System Prompt 对比", task1_system_prompt),
        ("任务2 Zero-shot vs Few-shot", task2_few_shot),
        ("任务3 结构化输出 JSON",        task3_structured_output),
    ]
    for title, func in tasks:
        print(f"\n{'=' * 50}\n===== {title} =====\n")
        try:
            func(client, model)
        except NotImplementedError as e:
            print(f"[跳过] {e}")
        print()


if __name__ == "__main__":
    main()
