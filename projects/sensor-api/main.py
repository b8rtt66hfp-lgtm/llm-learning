"""传感器 Web API —— 第二课：把你的数据变成"网络上的函数"

核心概念（对照 C 语言）：
- REST API = 把函数暴露到网络上，浏览器/手机/curl 都能调用
- @app.get("/api/current") = 路由注册，类似中断向量表：URL -> 处理函数
- uvicorn = Web 服务器，相当于工程的 main() + while(1)，监听端口收请求
- 返回 dict = FastAPI 自动转成 JSON，不用你手写 sprintf

运行（在本目录下）：
    venv\\Scripts\\python.exe -m uvicorn main:app --reload --port 8000
然后浏览器打开：
    http://127.0.0.1:8000/docs      <- FastAPI 自动生成的接口文档（杀手锏）
    http://127.0.0.1:8000/api/current
"""
import math
import random
import threading
import time
from collections import deque
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="传感器监控 API", version="1.0")

THRESHOLD = 60.0  # 温度报警阈值 (°C)

# 环形缓冲区：deque(maxlen=100) 满了自动丢最旧的
# 就是你在 STM32 里写的 ring buffer，Python 一行搞定
history = deque(maxlen=100)


def read_sensor() -> dict:
    """模拟读一次传感器（相当于你的 ADC 采样函数）"""
    now = datetime.now()
    hour = now.hour + now.minute / 60
    temp = 25 + 8 * math.sin((hour - 10) * math.pi / 12) + random.gauss(0, 0.5)
    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "temperature": round(temp, 2),
        "pressure": round(101.3 + random.gauss(0, 0.3), 2),
    }


def sampler_loop():
    """后台采样线程 —— 相当于定时器中断 ISR，每 2 秒采一次"""
    while True:
        history.append(read_sensor())
        time.sleep(2)


# daemon=True：主程序退出时线程自动结束，不用 join
threading.Thread(target=sampler_loop, daemon=True).start()


# ============ 已完成的接口（先跑起来看看） ============

@app.get("/")
def root():
    """根路径：返回 API 说明"""
    return {"message": "传感器 API 运行中，打开 /docs 查看接口文档"}


@app.get("/api/current")
def get_current():
    """获取最新一条传感器数据"""
    if not history:
        return {"error": "暂无数据，采样线程刚启动，等 2 秒再试"}
    return history[-1]  # 环形缓冲区最新位置，相当于 *(write_ptr - 1)


@app.get("/api/history")
def get_history(limit: int = 10):
    """获取最近 N 条历史数据

    limit 是查询参数：/api/history?limit=20
    C 类比：函数的默认参数 int limit = 10
    """
    data = list(history)
    return {"count": len(data[-limit:]), "data": data[-limit:]}


# ============ TODO：轮到你了 ============

# TODO 1 答案：GET /api/stats —— 统计历史数据的温度
@app.get("/api/stats")
def get_stats():
    if not history:
        return {"error": "暂无数据"}
    # 列表推导：从缓冲区取出温度列，相当于 C 里 for 循环遍历数组
    temps = [r["temperature"] for r in history]
    return {
        "count": len(temps),
        "max": max(temps),
        "min": min(temps),
        "avg": round(sum(temps) / len(temps), 2),
    }


# TODO 2 答案：GET /api/alarm —— 返回所有温度超过 THRESHOLD 的记录
@app.get("/api/alarm")
def get_alarm():
    # 带条件的列表推导 = 第一课 pandas 布尔索引的原生 Python 写法
    alarms = [r for r in history if r["temperature"] > THRESHOLD]
    return {"count": len(alarms), "threshold": THRESHOLD, "data": alarms}


# TODO 3 答案（进阶）：POST /api/threshold —— 运行时修改报警阈值
#
# 新知识点 1：BaseModel = 请求体的"结构体定义"
#   相当于 C 的:  typedef struct { float value; } ThresholdIn;
#   FastAPI 会自动校验：客户端发来的 JSON 里必须有 value 且是数字，
#   否则自动返回 422 错误 —— 不用你写 if 检查，这是 FastAPI 第二大杀手锏。
class ThresholdIn(BaseModel):
    value: float


# 新知识点 2：@app.post = 处理 POST 请求（GET 是"读取"，POST 是"修改/提交"）
# 参数 body: ThresholdIn 表示"把请求体 JSON 解析成 ThresholdIn 对象"
@app.post("/api/threshold")
def set_threshold(body: ThresholdIn):
    global THRESHOLD  # 声明要用全局变量，和 C 直接改全局变量效果一样
    THRESHOLD = body.value
    return {"message": "阈值已更新", "threshold": THRESHOLD}


# 测试方法（/docs 里点 Try it out，或者命令行）：
#   curl -X POST http://127.0.0.1:8000/api/threshold -H "Content-Type: application/json" -d "{\"value\": 30.0}"
# 然后再访问 /api/alarm，看看报警记录是不是变多了（阈值从 60 降到 30）
