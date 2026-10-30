"""练习 3：API 调用工具 —— 角色反转，这次你是"客户端"

核心概念（对照 C 语言）：
- 上节课你用 FastAPI "提供"接口（服务端），这节课用代码"调用"接口（客户端）
- requests.get(url) = 发 HTTP GET 请求，相当于你在单片机上用 AT 指令发请求
- resp.json() = 把返回的 JSON 字符串解析成 dict，不用手写 cJSON 那一套
- 异步并发 = 一个线程里"轮流"等所有网络响应，像 RTOS 任务切换，但开销几乎为零

运行：venv\\Scripts\\python.exe api_client.py
前置：第二课的 sensor-api 服务要在 8000 端口跑着（我们要调自己写的接口！）
"""
import asyncio
import time

import httpx
import pandas as pd
import requests

# ============================================================
# 第一部分：调用自己写的 sensor-api（已完成，先跑通找感觉）
# ============================================================

def get_sensor_stats() -> dict:
    """调用本地 sensor-api 的 /api/stats 接口"""
    try:
        resp = requests.get("http://127.0.0.1:8000/api/stats", timeout=5)
        # status_code = HTTP 状态码：200 成功 / 404 路径不存在 / 500 服务器崩了
        if resp.status_code == 200:
            return resp.json()  # JSON 字符串 -> dict，一行搞定
        return {"error": f"请求失败，状态码 {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        # 服务没启动 = 串口打不开，属于"硬件不在线"类错误
        return {"error": "连不上 8000 端口，sensor-api 没启动吧？"}


# ============================================================
# 第二部分：调用公开 API（Open-Meteo 免费天气接口，无需注册/key）
# ============================================================

# 城市坐标表：(纬度, 经度)，dict 相当于 C 的结构体数组查表
CITIES = {
    "北京": (39.90, 116.41),
    "上海": (31.23, 121.47),
    "深圳": (22.54, 114.06),
    "哈尔滨": (45.80, 126.53),
    "乌鲁木齐": (43.83, 87.62),
}

API_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(city: str, lat: float, lon: float) -> dict:
    """查一个城市的当前天气（同步版）"""
    # params = 查询参数，requests 自动拼成 ?latitude=...&longitude=...
    # 等价于你上节课接口里的 ?limit=10
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "timezone": "Asia/Shanghai",
    }
    resp = requests.get(API_URL, params=params, timeout=10)
    data = resp.json()

    # ========================================================
    # TODO 1: 从 data 里解析出天气数据，返回整理好的 dict
    # 返回格式: {"city": city, "temperature": 温度, "humidity": 湿度, "wind_speed": 风速}
    #
    # 提示：真实返回结构长这样 —
    #   {"current": {"time": "...", "temperature_2m": 15.2,
    #                "relative_humidity_2m": 60, "wind_speed_10m": 8.3}}
    # 取法: cur = data["current"]  然后 cur["temperature_2m"] 等
    # 建议先取消下面这行注释，print 看看真实结构再写：
    
    cur=data["current"] #提取currunt的值到cur内
    tem=cur["temperature_2m"] #分别提取到对应的函数内（tem）
    hun=cur["relative_humidity_2m"]
    win=cur["wind_speed_10m"]
    
    # ========================================================
    return {"city": city, "temperature": tem, "humidity": hun, "wind_speed": win}


# ============================================================
# 第三部分：串行批量查询 + 计时（体验"慢"，才能理解异步的价值）
# ============================================================

def fetch_all_serial() -> tuple[list, float]:
    """一个城市一个城市地查，返回 (结果列表, 总耗时秒数)

    time.perf_counter() = 高精度秒表，相当于你在单片机上读 DWT 计数器算耗时
    """
    start = time.perf_counter()
    results = []
    # ========================================================
    # TODO 2: 遍历 CITIES，对每个城市调用 fetch_weather，结果 append 到 results
    # 提示：
    #   for city, (lat, lon) in CITIES.items():
    #       results.append( ... )
    # CITIES.items() 同时取出 key 和 value，类似遍历结构体数组
    # ========================================================
    for city,(lat,lon)in CITIES.items():
        results.append(fetch_weather(city,lat,lon))
      
    elapsed = time.perf_counter() - start
    return results, elapsed


# ============================================================
# 第四部分：异步并发批量查询（进阶）—— 同时发出所有请求
# ============================================================

async def fetch_weather_async(client: httpx.AsyncClient, city: str, lat: float, lon: float) -> dict:
    """异步版查天气：await = "等响应的时候，线程先去干别的" """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "timezone": "Asia/Shanghai",
    }
    resp = await client.get(API_URL, params=params)
    cur = resp.json()["current"]
    return {
        "city": city,
        "temperature": cur["temperature_2m"],
        "humidity": cur["relative_humidity_2m"],
        "wind_speed": cur["wind_speed_10m"],
    }


async def fetch_all_concurrent() -> tuple[list, float]:
    """同时发出全部请求，总耗时 ≈ 最慢的那一个，而不是全部相加"""
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=10) as client:
        # ====================================================
        # TODO 3（进阶）: 用 asyncio.gather 并发执行所有城市的查询
        # 提示：
        tasks = [fetch_weather_async(client, city, lat, lon)
        for city, (lat, lon) in CITIES.items()]
        results = await asyncio.gather(*tasks)
        # gather(*tasks) 的 * 是解包，相当于把列表铺开成一个个参数
        # ====================================================
    
      #results = []  # 删掉这行，换成你的实现
    elapsed = time.perf_counter() - start
    return results, elapsed


# ============================================================
# 主流程
# ============================================================

if __name__ == "__main__":
    print("=== 1. 调用自己的 sensor-api ===")
    print(get_sensor_stats())

    print("\n=== 2. 串行查询 5 个城市天气 ===")
    serial_data, serial_time = fetch_all_serial()
    for row in serial_data:
        print(row)
    print(f"串行总耗时: {serial_time:.2f} 秒")

    print("\n=== 3. 异步并发查询（TODO 3 完成后才有数据）===")
    concurrent_data, concurrent_time = asyncio.run(fetch_all_concurrent())
    for row in concurrent_data:
        print(row)
    print(f"并发总耗时: {concurrent_time:.2f} 秒")

    # 存 CSV（第一课的 pandas 复习）
    if serial_data and serial_data[0].get("temperature") is not None:
        df = pd.DataFrame(serial_data)
        df.to_csv("weather.csv", index=False, encoding="utf-8-sig")
        print(f"\n已保存 weather.csv（{len(df)} 行）")
    else:
        print("\n完成 TODO 1 后才会生成 weather.csv")
