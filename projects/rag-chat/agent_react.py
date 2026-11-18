# -*- coding: utf-8 -*-
"""
手写版 ReAct Agent（不依赖 LangGraph）
=====================================
Agent 最核心的 4 行代码：

    while True:
        thought = LLM()                   # 思考下一步
        action, args = parse(thought)     # 决定调用哪个工具
        if action == "finish": break      # 任务完成则退出
        observation = tools[action](args) # 真的去调工具
        history += (thought, observation) # 历史追加

把这个循环图结构化 = LangGraph。
先手写一遍，跑通了再看 LangGraph 版。
"""

import json
import math
import sys
from pathlib import Path

# 复用 llm-chat 的客户端
_LLM_CHAT = Path(__file__).parent.parent / "llm-chat"
if str(_LLM_CHAT) not in sys.path:
    sys.path.insert(0, str(_LLM_CHAT))

from llm_client import get_client  # noqa: E402


# ============================================================
# 第 0 步：注册工具（tool）
# ============================================================
def calculator(expression: str) -> str:
    """安全计算器：用 eval 算一个纯算术表达式。"""
    try:
        result = eval(expression, {"__builtins__": {"abs": abs, "min": min, "max": max,
                                                    "round": round, "math": math}}, {})
        return f"计算器结果: {result}"
    except Exception as e:
        return f"计算器错误: {e}"


def get_current_time(_unused: str = "") -> str:
    """获取当前时间。参数忽略。"""
    import datetime
    now = datetime.datetime.now()
    return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def lookup_capital(country: str) -> str:
    """查国家首都（用一个很小的字典模拟"联网搜索"）。"""
    CAPITALS = {
        "中国": "北京", "美国": "华盛顿", "日本": "东京",
        "法国": "巴黎", "英国": "伦敦", "德国": "柏林",
        "意大利": "罗马", "韩国": "首尔", "俄罗斯": "莫斯科",
        "澳大利亚": "堪培拉", "加拿大": "渥太华",
    }
    return CAPITALS.get(country, f"没查到 {country} 的首都，可能不在我的小字典里。")


# 工具注册表：name → dict{desc, fn}
TOOLS = {
    "calculator": {
        "desc": "calculator(expression: str) — 计算数学表达式，比如 '2*(3+4)/2'",
        "fn": calculator,
    },
    "get_time": {
        "desc": "get_time() — 获取当前时间（不需要参数）",
        "fn": lambda _="": get_current_time(),
    },
    "lookup_capital": {
        "desc": "lookup_capital(country: str) — 查国家首都，参数是中文国名",
        "fn": lookup_capital,
    },
}


# ============================================================
# 第 1 步：构造 ReAct 格式的 Prompt
# ============================================================
def _build_tool_section() -> str:
    lines = []
    for t in TOOLS.values():
        lines.append(f"- {t['desc']}")
    return "\n".join(lines)


SYSTEM = f"""你是一个智能体。你有以下工具可用：

{_build_tool_section()}

你必须用严格 JSON 格式输出，二选一：
1) 调用工具：{{"action": "<工具名>", "args": "<工具参数，字符串>"}}
2) 任务完成：{{"action": "finish", "args": "最终回答的自然语言"}}

注意：
- 没调用到工具之前，action 只能是上面三个工具名之一
- 拿到工具返回的 observation 后，可能还要继续调别的工具，也可能直接 finish
- 最终回答要用中文，尽量简洁
"""


# ============================================================
# 第 2 步：ReAct 主循环
# ============================================================
def run_agent(question: str, max_steps: int = 6) -> None:
    client, model = get_client()
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": question}]

    print(f"\n👤 你好，我是 ReAct Agent，请输入: {question}\n")
    for step in range(1, max_steps + 1):
        print(f"--- Step {step} ---")
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0.0, max_tokens=256,
        )
        raw = resp.choices[0].message.content.strip()
        print(f"  🧠 LLM 原始输出:\n  {raw}")

        # 解析 JSON
        try:
            parsed = json.loads(raw)
            action = parsed.get("action", "")
            args = parsed.get("args", "")
        except json.JSONDecodeError:
            print(f"  [警告] LLM 没返回合法 JSON，把它当最终回答")
            print(f"  ✅ 最终回答: {raw}\n")
            return

        # 记录 assistant 的这次决定
        messages.append({"role": "assistant", "content": raw})

        if action == "finish":
            print(f"  ✅ Agent 完成: {args}\n")
            return

        if action not in TOOLS:
            obs = f"工具 {action} 不存在，请从 {list(TOOLS.keys())} 里选"
            print(f"  ❌ 工具不存在: {action}")
        else:
            obs = TOOLS[action]["fn"](args)
            print(f"  🔧 调工具 {action}({args!r}) → {obs}")

        # 把 observation 反馈给 LLM
        messages.append({"role": "user", "content": f"observation: {obs}"})

    print("⚠️ 达到最大步数，强制结束")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        run_agent(q)
    else:
        # 自动挑几个问题演示
        demo_questions = [
            "北京和东京的时差是多少小时？",          # 查时间 + 查首都 + 简单算
            "法国首都是哪里，用首字母大写告诉我",      # lookup_capital 一次就够
            "算一下 123 * 456 等于多少",             # calculator
        ]
        for q in demo_questions:
            run_agent(q)
