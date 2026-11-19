# 本地语音助手（Local Voice Assistant）

全本地、零外网依赖的语音问答系统：**语音 → ASR → LLM → 回答**。

```
        ┌─────────┐    ┌──────────────────┐    ┌────────────────────────┐
 wav ──▶│  ASR    │───▶│  LLM             │───▶│  TTS（占位）           │───▶ 回答文本
        │funasr-  │    │Ollama            │    │ tts_mock / ChatTTS     │
        │onnx     │    │mechatronics-     │    └────────────────────────┘
        │paraformer│   │assistant         │
        └─────────┘    │(qwen2.5:1.5b)    │
                       └────────────────────────┘
```

- **ASR**：FunASR paraformer-large 中文模型（ONNX 量化版，约 226MB），用 `funasr-onnx` 加载
- **LLM**：本地 Ollama，模型 `mechatronics-assistant`（qwen2.5:1.5b + 机械电子工程 system prompt）
- **TTS**：当前为占位实现（输出 txt），真实合成代码已备好（ChatTTS）

## 目录结构

```
projects/voice-assistant/
├── voice_assistant.py     # CLI 骨架（--text / --audio / --chat）
├── app/
│   └── main.py            # FastAPI 服务（/health /chat /voice / 网页）
├── requirements.txt
├── start.ps1              # 一键启动（拉起 Ollama + uvicorn）
├── models/                # ASR 模型（gitignore，不入库）
└── venv/                  # 虚拟环境（不入库）
```

## 环境要求

| 组件 | 版本/说明 |
|---|---|
| Python | 3.11 |
| Ollama | 已安装并拉取 `qwen2.5:1.5b` |
| ASR 模型 | FunASR paraformer ONNX，放在 `models/models/iic--speech_paraformer-*` |

## 安装

```powershell
# 1. 虚拟环境
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. 下载 ASR 模型（ModelScope，国内可达）
.\venv\Scripts\python.exe -c "from modelscope import snapshot_download; snapshot_download('iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx')"

# 3. 构建 Ollama 定制模型
ollama create mechatronics-assistant -f ..\llm-deploy\ollama\Modelfile
```

## 启动

```powershell
# 一键：自动检查/拉起 Ollama，再启动 API
.\start.ps1

# 或者手动
ollama serve                       # 另开一个终端（若未运行）
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开 <http://127.0.0.1:8000> 即为测试页，<http://127.0.0.1:8000/docs> 为自动生成的接口文档。

## 接口

### `GET /health`

```json
{"ollama": true, "ollama_url": "http://127.0.0.1:11434",
 "model": "mechatronics-assistant", "asr_ready": true, "asr_model_dir": "..."}
```

### `POST /chat` — 文字问答

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"键连接的作用是什么？\"}"
```

```json
{"model": "mechatronics-assistant", "reply": "..."}
```

支持多轮上下文：`{"message": "...", "history": [{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}`

### `POST /voice` — 语音问答（上传 16kHz 单声道 wav）

```bash
curl -X POST http://127.0.0.1:8000/voice -F "file=@test.wav"
```

```json
{"asr_text": "键连接的作用是什么", "reply": "..."}
```

## CLI 用法（不走 HTTP）

```powershell
.\venv\Scripts\python.exe voice_assistant.py --text "轴承代号 6208 表示什么意思？"
.\venv\Scripts\python.exe voice_assistant.py --audio test.wav --real-asr
.\venv\Scripts\python.exe voice_assistant.py --chat
```

## 部署说明与局限

- 当前为**单机本地部署**：Ollama 与 API 服务同机，仅监听本机端口。
- 对局域网开放：`--host 0.0.0.0`（`start.ps1` 已默认），注意无鉴权，仅限可信内网。
- 未接入鉴权、限流、HTTPS；生产化需要额外加反向代理（Nginx/Caddy）。
- 226MB 的 ONNX 模型不入仓库，部署机需按上文步骤单独下载。
- Docker 不是首选：容器内跑 Ollama 需要 GPU/大内存透传，ONNX 模型需 volume 挂载；如需容器化，建议 Ollama 留在宿主机、只把 API 打进镜像，并挂载 `models/`。
- TTS 目前是占位实现（把回答写成 txt）；真实合成装 `ChatTTS + soundfile` 后调用 `tts_chattts()` 即可。

## 面试讲法

> 我做了一个全本地的语音问答系统，链路是 ASR → LLM → TTS，跑在单机上、零外网依赖。
> ASR 用阿里开源的 FunASR paraformer ONNX 量化模型，通过 funasr-onnx 加载，首次加载约 1 秒，之后常驻内存复用单例。
> LLM 是本机 Ollama 上的 qwen2.5:1.5b，用 Modelfile 定制了机械电子工程的 system prompt。
> 服务层用 FastAPI 暴露三个接口：健康检查、文字问答、语音上传问答；因为 ASR 和 Ollama 调用都是同步阻塞的，我把它们放进线程池，避免阻塞事件循环。
> 踩过的坑：Python requests 把 localhost 解析成 IPv6 ::1 而 Ollama 只绑 IPv4，统一改成 127.0.0.1；还有 Ollama 多进程抢端口导致启动 bind 失败，要先清理残留进程。
