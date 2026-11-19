# 机械工程助手 — 本地部署

基于 **Ollama + qwen2.5:1.5b** 的轻量化机械工程助手，外加一个 FastAPI 网关统一 HTTP 接口。

```
┌─────────────────┐   ┌──────────────────────┐   ┌─────────────────┐
│  FastAPI 网关    │──▶│  Ollama /api/chat     │──▶│  mechatronics-  │
│  :8000          │   │  :11434              │   │  assistant      │
└─────────────────┘   └──────────────────────┘   └─────────────────┘
  /health                本地 HTTP                  (qwen2.5:1.5b +
  /chat                                            定制 system prompt)
  /chat/stream
```

## 一、前置

- Ollama 已安装并能跑（`ollama serve` 或桌面 App）
- Python 3.10+

## 二、本地跑通（3 步）

```powershell
# 1. 确保 Ollama 在跑（没拉过 qwen2.5 会自动拉取，~1GB）
ollama serve                         # 后台留着这个窗口
ollama list                          # 应该能看到 qwen2.5:1.5b

# 2. 构建定制模型（复用本地 qwen2.5:1.5b 权重，只是加一层 Modelfile）
ollama create mechatronics-assistant -f ollama/Modelfile

# 3. 启动网关
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 三、三个接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 本地 + Ollama 双层健康检查 |
| POST | `/chat` | 非流式，返回完整 JSON |
| POST | `/chat/stream` | SSE 流式，逐 token 输出 |

### 请求体（两个 POST 通用）

```json
{
  "message": "键连接的作用是什么？",
  "history": [
    {"role": "user", "content": "我叫小王"},
    {"role": "assistant", "content": "好的，记住了"}
  ],
  "system_override": "可选，覆盖默认 system prompt"
}
```

### 示例

```powershell
curl http://localhost:8000/health

curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"键连接的作用是什么？\"}"
```

## 四、环境变量（可覆盖默认）

| 变量 | 默认 | 说明 |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 地址（局域网/容器部署时改） |
| `MODEL_NAME` | `mechatronics-assistant` | Modelfile 构建出来的模型名 |
| `REQUEST_TIMEOUT` | `60` | 请求 Ollama 的超时秒数 |

```powershell
$env:MODEL_NAME="qwen2.5:1.5b"; .\venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

## 五、Docker 部署（可选）

前提：装了 Docker Desktop + WSL2。

```bash
# 构建镜像（约 200MB，基于 python:3.11-slim）
docker build -t mechatronics-api .

# 启动（同时要在另一个容器里跑 Ollama）
docker run -d --name ollama -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama
docker exec ollama ollama create mechatronics-assistant -f - < ollama/Modelfile
docker run -d --name api -p 8000:8000 --link ollama -e OLLAMA_URL=http://ollama:11434 mechatronics-api
```

或者用 docker-compose（如果你装了）：

```yaml
services:
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      OLLAMA_URL: http://ollama:11434
    depends_on: [ollama]
volumes:
  ollama_data:
```

## 六、面试怎么讲这个项目

1. **两层架构**：FastAPI 作为统一网关，屏蔽底层是 Ollama 还是云端模型；后续换 DeepSeek 只要改 OLLAMA_URL 和请求体格式，网关不用变。
2. **Modelfile 的意义**：Ollama 的 Modelfile 像 Dockerfile，FROM 复用已有权重，SYSTEM 写人格和规则，PARAMETER 控制采样参数。构建出来的模型可以 `ollama push` 分发，免掉传 1GB 权重文件。
3. **为什么本地部署**：Ollama 在消费级显卡/核显上就能跑 1.5B，数据不出机器，适合机械设计这种可能有图纸/工艺参数的敏感场景。
4. **为什么 API 层要单独做**：前端直接调 Ollama 原生接口有两个问题——Ollama 的 schema 和 OpenAI 不完全一致（没有 `/v1/chat/completions` 这一层），和前端解耦后后端可以自己加缓存、鉴权、限流。
5. **下一步可以加什么**：LangSmith/LangFuse 做 trace、Redis 做会话缓存、vLLM 替换 Ollama 提升吞吐（vLLM 有 PagedAttention，单卡并发能上）。
