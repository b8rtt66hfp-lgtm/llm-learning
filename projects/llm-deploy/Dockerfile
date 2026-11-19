FROM python:3.11-slim

WORKDIR /app

# 先装依赖层（利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制代码（代码变了不影响依赖缓存）
COPY app ./app
COPY ollama ./ollama

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# 启动时 Ollama 可能还没起来——uvicorn 自己能等（health 接口会探测）
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
