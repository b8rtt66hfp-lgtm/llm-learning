# -*- coding: utf-8 -*-
"""
最小 RAG demo
=============
完整流程：
    1) 文档片段 → Embedding → 存入 ChromaDB
    2) 用户问题 → Embedding → ChromaDB 检索 top-k 相关片段
    3) 片段 + 问题 组装成 prompt → LLM 回答

运行：
    .\\venv\\Scripts\\python.exe rag_demo.py

注意：首次运行会自动拉 bge-m3 Embedding 模型 + 下载 Qwen 模型（如果你还没装的话）。
"""

import json
import sys
from pathlib import Path

from openai import OpenAI

# 让 llm-chat 的 get_client 可被复用
_LLM_CHAT = Path(__file__).parent.parent / "llm-chat"
if str(_LLM_CHAT) not in sys.path:
    sys.path.insert(0, str(_LLM_CHAT))

from embedding_client import EMBED_MODEL
from llm_client import get_client as get_llm_client  # noqa: E402
from vector_db import (
    COLLECTION_NAME,
    add_documents,
    get_client,
    get_or_create_collection,
    query,
)


# ============================================================
# 1. 准备一批"知识库"文档（真实项目里是 PDF/Word 解析来的）
# ============================================================
KNOWLEDGE_DOCS = [
    # 主题：Python 基础
    ("d1", "Python 的列表是可变序列，用 [] 创建，支持追加、插入、切片。",
     {"topic": "python", "difficulty": "easy"}),
    ("d2", "Python 的字典是键值对容器，键必须是不可变类型（str/int/tuple）。",
     {"topic": "python", "difficulty": "easy"}),
    # 主题：LLM
    ("d3", "LLM 的上下文窗口是它能一次处理的最大 Token 数。超过会截断。",
     {"topic": "llm", "difficulty": "medium"}),
    ("d4", "RAG = 检索增强生成：先从向量库检索相关文档，再喂给 LLM 让它基于文档回答。",
     {"topic": "llm", "difficulty": "medium"}),
    ("d5", "Embedding 模型负责把文本变成向量，LLM 负责根据向量检索结果组织成自然语言回答。",
     {"topic": "llm", "difficulty": "medium"}),
    # 主题：机械工程
    ("d6", "键连接通过键将轴与带轮/齿轮连接，实现周向固定并传递扭矩。",
     {"topic": "mech", "difficulty": "hard"}),
    ("d7", "V 带传动靠摩擦力工作，承载能力约为平带的 3 倍。",
     {"topic": "mech", "difficulty": "medium"}),
]


def build_index() -> None:
    """把知识库灌入向量库（幂等：重复跑会先清掉旧数据）。"""
    db = get_client()
    col = get_or_create_collection(db, COLLECTION_NAME)
    col.delete(ids=col.get()["ids"]) if col.count() > 0 else None

    ids = [d[0] for d in KNOWLEDGE_DOCS]
    texts = [d[1] for d in KNOWLEDGE_DOCS]
    metas = [d[2] for d in KNOWLEDGE_DOCS]
    add_documents(col, ids, texts, metas)
    print(f"[索引] 已存入 {col.count()} 条文档（Embedding 模型: {EMBED_MODEL}）")


def rag_answer(question: str, top_k: int = 3) -> None:
    """RAG 问答：检索 → 组装 prompt → 让 LLM 回答。"""
    db = get_client()
    col = get_or_create_collection(db, COLLECTION_NAME)

    # 1) 检索
    result = query(col, question, top_k=top_k)
    retrieved_docs = result["documents"][0]
    distances = result["distances"][0]

    print(f"\n问题：{question}")
    print("--- 检索到的 top-k ---")
    for doc, dist in zip(retrieved_docs, distances):
        print(f"  [距离 {dist:.4f}] {doc}")

    # 2) 组装 prompt（RAG 的核心：把检索结果作为上下文给 LLM）
    context = "\n".join(f"- {d}" for d in retrieved_docs)
    system = (
        "你是一个准确的问答助手。你只能基于给出的参考资料回答问题，"
        "如果参考资料里没有答案，就说'资料里没找到相关信息'。"
    )
    user = f"参考资料：\n{context}\n\n问题：{question}\n\n回答："

    # 3) 让 LLM 回答
    client, model = get_llm_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=512,
    )
    answer = resp.choices[0].message.content.strip()

    print(f"\n--- LLM 回答 ---\n{answer}\n")


def main() -> None:
    build_index()

    questions = [
        "什么是 RAG？",
        "Python 里字典的键有什么要求？",
        "键连接是用来做什么的？",
        "Python 列表和字典有什么区别？",  # 故意问一个会同时命中两条文档的问题
    ]
    for q in questions:
        rag_answer(q, top_k=3)


if __name__ == "__main__":
    main()
