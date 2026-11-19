"""
本地语音助手 — 完整骨架

数据流：
    (麦克风/音频文件) → ASR → 文本 → Ollama LLM → 文本 → TTS → (扬声器/wav 文件)

当前 ASR/TTS 用 mock（CLI 读文字 / 保存占位 wav），替换成真实本地模型只改两行。

用法：
    # 模式 A：命令行直接输入文字（最方便验证）
    python voice_assistant.py --text "键连接的作用是什么？"

    # 模式 B：给一段 wav 文件，用真实 ASR 识别（需要先装好 ASR 模型）
    python voice_assistant.py --audio input.wav

    # 模式 C：持续对话（用文字输入，带多轮上下文）
    python voice_assistant.py --chat

    # 模式 D：麦克风录音 → ASR → LLM → TTS 出声（真正的端到端闭环）
    python voice_assistant.py --mic 5 --real-tts

依赖：
    # ASR：funasr-onnx + FunASR paraformer ONNX 模型
    # TTS：pyttsx3（Windows SAPI5，离线、零模型下载）
    # 麦克风：sounddevice
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mechatronics-assistant")

DEFAULT_SYSTEM = (
    "你是一名资深机械电子工程师助手。"
    "回答范围：机械设计、机械原理、公差配合、材料与热处理、液压/气动、PLC/单片机/传感器。"
    "风格简洁直接，必要时分点列出。"
)


# ---------------------------------------------------------------------------
# ASR：语音 → 文字
# ---------------------------------------------------------------------------

def asr_mock(audio_path: str) -> str:
    """占位实现：等真实模型装好后替换成 sherpa_onnx / funasr_onnx。"""
    print(f"[ASR mock] 请把这段话替换成真实识别 → 输入音频: {audio_path}")
    # 临时：从 wav 文件名猜问题（方便演示）
    name = Path(audio_path).stem.lower()
    mapping = {
        "jian": "键连接的作用是什么？",
        "zhoucheng": "轴承代号 6208 表示什么意思？",
        "vband": "V带传动为什么比平带承载能力高？",
    }
    return mapping.get(name, f"(我没听清，你说的 '{name}' 是什么？)")


def asr_funasr_onnx(audio_path: str, model_dir: str) -> str:
    """
    真实实现：funasr-onnx，直接加载 ModelScope 下载的 FunASR paraformer 模型。
    model_dir 应包含 model_quant.onnx + decoder_quant.onnx + tokens.json。
    首次调用会触发模型加载（~1s），后续复用。
    """
    from funasr_onnx import Paraformer
    _model = Paraformer(model_dir, batch_size=1, quantize=True)
    result = _model([audio_path])
    return result[0]["preds"][0].strip() if result else ""


def clean_asr_text(text: str, max_len: int = 200) -> str:
    """
    清洗 ASR 输出：
    - 截断过长内容
    - 同一字符占比过高（静音/噪声导致的 "峰峰峰..." 重复幻觉）视为无效，返回空串
    """
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) > max_len:
        text = text[:max_len]
    if len(text) >= 8:
        from collections import Counter
        top = Counter(text).most_common(1)[0][1]
        if top / len(text) > 0.5:
            return ""
    return text


# ---------------------------------------------------------------------------
# LLM：文字 → 文字（调 Ollama）
# ---------------------------------------------------------------------------

def llm_reply(text: str, history: list[dict] | None = None) -> str:
    messages: list[dict] = [{"role": "system", "content": DEFAULT_SYSTEM}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": text})

    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            # 限制生成长度，防止噪声输入触发超长输出把 CPU 跑满
            "options": {"num_predict": 512},
        },
        timeout=120,
    )
    r.raise_for_status()
    body = r.json()
    return body.get("message", {}).get("content", "").strip()


# ---------------------------------------------------------------------------
# TTS：文字 → 语音文件
# ---------------------------------------------------------------------------

def tts_mock(text: str, out_path: str) -> None:
    """占位实现：写一个 txt 文件，代替真实 TTS 输出。"""
    Path(out_path).with_suffix(".txt").write_text(text, encoding="utf-8")
    print(f"[TTS mock] 已保存回答文字 → {Path(out_path).with_suffix('.txt')}")
    print("[TTS mock] 请把这里替换成 ChatTTS / pyttsx3 的真实合成。")


def tts_chattts(text: str, out_path: str) -> None:
    """真实实现：ChatTTS 本地合成（pip install ChatTTS soundfile）。"""
    import ChatTTS
    import soundfile as sf

    chat = ChatTTS.Chat()
    chat.load()  # 第一次会自动下载模型（~200MB）
    wav, sr = chat.infer([text])[0]
    sf.write(out_path, wav, sr)


def tts_sapi(text: str, out_path: str) -> None:
    """Windows SAPI5 离线合成（pyttsx3），显式优先选中文语音包。"""
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 180)
    for v in engine.getProperty("voices") or []:
        langs = [
            l.decode() if isinstance(l, bytes) else str(l)
            for l in (getattr(v, "languages", []) or [])
        ]
        if any("zh" in l.lower() for l in langs) or "chinese" in v.name.lower():
            engine.setProperty("voice", v.id)
            break
    engine.save_to_file(text, out_path)
    engine.runAndWait()
    engine.stop()  # 释放 COM 对象，服务里反复调用更稳


# ---------------------------------------------------------------------------
# 麦克风：录音 → 16kHz 单声道 wav（ASR 要求的格式）
# ---------------------------------------------------------------------------

def record_mic(seconds: float = 5.0, out_path: str = "mic.wav", sr: int = 16000) -> str:
    import sounddevice as sd
    import soundfile as sf

    print(f"[MIC] 开始录音 {seconds:.0f} 秒，请说话 ...")
    audio = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    sf.write(out_path, audio, sr)
    print(f"[MIC] 已保存 → {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def voice_to_voice(audio_in: str, wav_out: str = "reply.wav",
                   real_asr: bool = False, real_tts: bool = False) -> str:
    """端到端：音频文件 → ASR → LLM → TTS → wav 文件。"""
    t0 = time.time()

    # 1) ASR
    t1 = time.time()
    text = asr_funasr_onnx(audio_in, MODEL_DIR) if real_asr else asr_mock(audio_in)
    text = clean_asr_text(text)
    print(f"[ASR]  {text or '(无有效语音)'}  ({time.time()-t1:.1f}s)")
    if not text:
        print("[ASR] 没有识别到有效内容（静音/噪声），跳过 LLM 和 TTS。")
        return ""

    # 2) LLM
    t2 = time.time()
    reply = llm_reply(text)
    print(f"[LLM]  {reply}  ({time.time()-t2:.1f}s)")

    # 3) TTS
    t3 = time.time()
    if real_tts:
        tts_sapi(reply, wav_out)
    else:
        tts_mock(reply, wav_out)
    print(f"[TTS]  done  ({time.time()-t3:.1f}s)")

    print(f"\n总耗时: {time.time()-t0:.1f}s")
    return reply


def chat_loop() -> None:
    """持续文字对话，带多轮上下文。"""
    history: list[dict] = []
    print("=== 语音助手（文字模式）===")
    print("输入 `/quit` 退出\n")
    while True:
        try:
            text = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("/quit", "/exit"):
            break

        reply = llm_reply(text, history)
        print(f"助手: {reply}\n")

        # 维护上下文（Ollama 自己会拼 system prompt）
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 12:
            history = history[-8:]  # 只保留最近 4 轮


# ---------------------------------------------------------------------------
# 模型目录查找（离线版优先；online 流式模型与离线 Paraformer 类不兼容）
# ---------------------------------------------------------------------------

def find_asr_model_dir() -> str | None:
    base = Path(__file__).parent
    candidates: list[str] = []
    for pattern in (
        base / "models" / "models" / "*paraformer*" / "snapshots" / "*",
        base / "models" / "*paraformer*",
    ):
        candidates = glob.glob(str(pattern))
        if candidates:
            break
    # 按完整路径过滤，排除 -online 流式模型（快照目录名是 master/v2.0.4，不能只看 basename）
    offline = [p for p in candidates if "online" not in p.lower()]
    return (offline or candidates or [None])[0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    MODEL_DIR = os.getenv("ASR_MODEL_DIR") or find_asr_model_dir() or "./models/paraformer"
    print(f"[ASR model] {MODEL_DIR}")

    p = argparse.ArgumentParser()
    p.add_argument("--audio", help="输入 wav 文件")
    p.add_argument("--text", help="直接输入文字（跳过 ASR）")
    p.add_argument("--chat", action="store_true", help="持续对话模式（文字）")
    p.add_argument("--real-asr", action="store_true", help="用真实 ASR（需要先装好）")
    p.add_argument("--mic", type=float, metavar="秒", help="录音 N 秒 → ASR → LLM → TTS（端到端闭环）")
    p.add_argument("--real-tts", action="store_true", help="用真实 TTS 合成 wav（pyttsx3 / Windows SAPI5）")
    p.add_argument("--out", default="reply.wav", help="TTS 输出文件")

    args = p.parse_args()

    if args.chat:
        chat_loop()
    elif args.mic:
        audio = record_mic(args.mic)
        voice_to_voice(audio, args.out, real_asr=True, real_tts=args.real_tts)
    elif args.text:
        reply = llm_reply(args.text)
        print(f"助手: {reply}")
        if args.real_tts:
            tts_sapi(reply, args.out)
        else:
            tts_mock(reply, args.out)
    elif args.audio:
        voice_to_voice(args.audio, args.out, real_asr=args.real_asr, real_tts=args.real_tts)
    else:
        p.print_help()
        sys.exit(1)
