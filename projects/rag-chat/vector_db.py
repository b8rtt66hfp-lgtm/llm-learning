# -*- coding: utf-8 -*-
"""ChromaDB 向量库 —— 基本 CRUD + 检索"""

import os
from pathlib import Path

import chromadb
from chromadb.config import Settings

from embedding_client import embed

# 本地持久化目录（.gitignore 里应该忽略）
DB_DIR = Path(__file__).parent / "chroma_data"
COLLECTION_NAME = "demo_docs"


def get_client() -> chromadb.ClientAPI:
    """拿到 ChromaDB 持久化客户端。数据存在 DB_DIR。"""
    return chromadb.PersistentClient(
        path=str(DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def get_or_create_collection(client: chromadb.ClientAPI, name: str = COLLECTION_NAME):
    """建 collection（如果不存在），返回 collection 对象。"""
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},  # 余弦相似度
    )


def add_documents(collection, ids: list[str], texts: list[str],
                  metadatas: list[dict] | None = None) -> None:
    """向 collection 里加文档。向量由 embed() 自动算。"""
    embeddings = [embed(t) for t in texts]
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def query(collection, text: str, top_k: int = 3) -> dict:
    """用一段文本查 collection，返回 top_k 条最相似的文档。"""
    q_vec = embed(text)
    return collection.query(query_embeddings=[q_vec], n_results=top_k)


if __name__ == "__main__":
    # === 手动跑一遍看效果 ===
    client = get_client()
    col = get_or_create_collection(client)

    # 如果已经有数据，先清掉再跑 demo
    col.delete(ids=col.get()["ids"]) if col.count() > 0 else None

    docs = [
        "番茄炒蛋是一道家常菜，用番茄和鸡蛋快炒即可。",
        "麻婆豆腐是川菜，主要食材豆腐、牛肉末、郫县豆瓣酱。",
        "红烧肉需要五花肉、冰糖、生抽、老抽，慢炖入味。",
        "鱼香肉丝属于川菜，有鱼香味道但不放鱼。",
    ]
    ids = [f"d{i}" for i in range(len(docs))]
    add_documents(col, ids, docs, metadatas=[{"source": "recipes"}] * len(docs))
    print(f"已入库 {col.count()} 条文档\n")

    # 查
    result = query(col, "有哪些川菜推荐？", top_k=2)
    for doc, dist in zip(result["documents"][0], result["distances"][0]):
        print(f"  [距离 {dist:.4f}] {doc}")
