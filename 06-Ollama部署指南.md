# Ollama 本地部署指南

> **部署日期**：2026-10-29
> **部署方式**：官方安装包静默安装 + 模型存储重定向到 D 盘

---

## 一、部署信息总览（磁盘占用位置）

| 内容 | 位置 | 磁盘 | 预计占用 |
|------|------|------|----------|
| Ollama 程序本体 | `C:\Users\26870\AppData\Local\Programs\Ollama` | **C 盘** ⚠️ | 约 1~4 GB（含 GPU 运行库） |
| Ollama 配置/日志 | `C:\Users\26870\.ollama` | **C 盘** ⚠️ | 几十 MB（很小） |
| **模型存储** | `d:\trae项目2\ollama\models` | **D 盘** ✅ | 每个模型 0.4~5 GB |
| 安装包下载缓存 | `d:\trae项目2\downloads`（安装后已清理） | D 盘 | 0（已删除） |

> **说明**：Ollama 安装程序不支持自定义安装目录，程序本体必须装在 C 盘的 `%LOCALAPPDATA%\Programs\Ollama`，这是无法更改的。但**模型文件（最大的空间开销）已通过 `OLLAMA_MODELS` 环境变量重定向到 D 盘**，以后拉取再多模型都不会占用 C 盘。

---

## 二、环境变量配置（已完成）

```powershell
# 用户级环境变量（重启后依然生效）
OLLAMA_MODELS = d:\trae项目2\ollama\models
```

验证方法：

```powershell
[System.Environment]::GetEnvironmentVariable("OLLAMA_MODELS", "User")
```

> 如果以后想把模型挪到别处（比如 `D:\ollama_models`），改这个环境变量后重启 Ollama 服务即可，已下载的模型把整个 `models` 文件夹剪切过去就行。

---

## 三、常用命令速查

```powershell
# 查看 ollama 版本
ollama --version

# 查看已下载的模型
ollama list

# 查看正在运行的模型（显存/内存占用）
ollama ps

# 拉取模型
ollama pull qwen2.5:7b

# 运行模型（交互式对话，输入 /bye 退出）
ollama run qwen2.5:1.5b

# 单次提问（不进入交互模式）
ollama run qwen2.5:1.5b "用一句话介绍什么是嵌入式系统"

# 删除模型（释放磁盘空间）
ollama rm 模型名

# 停止后台服务
Get-Process ollama* | Stop-Process -Force

# 启动后台服务
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
```

---

## 四、REST API 调用（服务地址：http://localhost:11434）

### 4.1 原生 API（PowerShell 测试）

```powershell
$body = '{"model":"qwen2.5:1.5b","prompt":"你好","stream":false}'
Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType "application/json" | Select-Object -ExpandProperty response
```

### 4.2 OpenAI 兼容 API（重点！）

Ollama 提供 OpenAI 兼容接口，这意味着你以后学的所有 OpenAI SDK 代码都能直接连本地模型：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",  # 指向本地 Ollama
    api_key="ollama",                       # 随便填，不校验
)

resp = client.chat.completions.create(
    model="qwen2.5:1.5b",
    messages=[
        {"role": "system", "content": "你是一个简洁的中文助手"},
        {"role": "user", "content": "用一句话解释什么是 RAG"},
    ],
)
print(resp.choices[0].message.content)
```

> **学习价值**：这就是你路线图第二阶段"LLM API 调用实战"的本地免费练习环境 —— 把 `base_url` 换成 `https://api.deepseek.com`、加个真实 key，同样的代码就切换到了云端模型。

### 4.3 Python 聊天脚本（多轮对话）

见 [test_ollama.py](./test_ollama.py)，已放在本项目 `scripts` 相关位置，运行方式：

```powershell
pip install requests
python test_ollama.py
```

---

## 五、本次部署的模型清单

| 模型 | 大小 | 用途 | 命令 |
|------|------|------|------|
| qwen2.5:0.5b | ~400 MB | 极速测试、低配机器 | `ollama run qwen2.5:0.5b` |
| qwen2.5:1.5b | ~1 GB | 验证部署、日常小任务 | `ollama run qwen2.5:1.5b` |
| qwen2.5:7b | ~4.7 GB | **主力模型**，质量与速度平衡 | `ollama run qwen2.5:7b` |

### 后续推荐补充的模型（按学习进度）

| 阶段 | 模型 | 说明 |
|------|------|------|
| RAG 实验 | `bge-m3`（embedding 模型） | `ollama pull bge-m3`，做向量检索用 |
| 微调后部署 | 自己微调的 GGUF 模型 | 配合 LLaMA-Factory 导出后 `ollama create` 导入 |
| 多模态 | `qwen2.5vl:7b` | 图片理解 |
| 代码辅助 | `qwen2.5-coder:7b` | 写代码、解释代码 |

---

## 六、故障排查

| 问题 | 排查方法 |
|------|----------|
| `ollama` 命令找不到 | 重开一个 PowerShell 窗口（安装后 PATH 需要新会话才生效）；或用完整路径 `& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" ...` |
| 连接 `localhost:11434` 失败 | 服务没启动：`Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve"` |
| 模型下载很慢 | Ollama 模型托管在 Cloudflare CDN，国内速度波动正常；可挂代理或换时段重试，`ollama pull` 支持断点续传 |
| 拉取的模型跑到 C 盘了 | 检查 `OLLAMA_MODELS` 环境变量是否生效：`[System.Environment]::GetEnvironmentVariable("OLLAMA_MODELS","User")`，改完后必须重启 Ollama 服务 |
| 内存不足（8GB 以下机器跑 7b） | 换小模型 `qwen2.5:1.5b`，或关掉大程序再试 |
| 端口 11434 被占用 | `netstat -ano | findstr 11434` 找到占用进程 PID，`taskkill /PID xxx /F`（PowerShell: `Stop-Process -Id xxx -Force`） |

---

## 七、卸载方法（如果以后需要）

```powershell
# 1. Windows 设置 → 应用 → 搜索 Ollama → 卸载
# 2. 删除模型目录（释放 D 盘空间）
Remove-Item -Recurse -Force "d:\trae项目2\ollama"
# 3. 删除残留配置（可选）
Remove-Item -Recurse -Force "$env:USERPROFILE\.ollama"
# 4. 删除环境变量（可选）
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $null, "User")
```
