"""模拟传感器数据生成器

模拟一块 STM32 采集板 7 天的温湿度/压力日志：
- 每 10 分钟一条记录，共 1008 条
- 温度：25°C 基准 + 昼夜波动 + 随机噪声
- 压力：101.3 kPa 基准 + 随机噪声
- 随机注入 5 个异常点（模拟传感器故障跳变）

运行：python generate_data.py
输出：sensor_log.csv
"""
import csv
import math
import random
from datetime import datetime, timedelta

random.seed(42)  # 固定随机种子，每次生成的数据一样（方便对答案）

def generate():
    start = datetime(2026, 10, 23, 0, 0, 0)
    rows = []
    for i in range(7 * 24 * 6):  # 7天 * 24小时 * 6条/小时
        ts = start + timedelta(minutes=10 * i)
        hour = ts.hour + ts.minute / 60
        # 昼夜温度波动：凌晨 4 点最冷，下午 14 点最热，振幅 8°C
        temp = 25 + 8 * math.sin((hour - 10) * math.pi / 12) + random.gauss(0, 0.5)
        pressure = 101.3 + random.gauss(0, 0.3)
        rows.append([ts.strftime("%Y-%m-%d %H:%M:%S"), round(temp, 2), round(pressure, 2)])

    # 注入异常值（模拟传感器偶发故障）
    for idx in random.sample(range(len(rows)), 5):
        rows[idx][1] = round(random.uniform(70, 90), 2)  # 温度跳到 70~90°C

    with open("sensor_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "temperature", "pressure"])
        writer.writerows(rows)
    print(f"生成完成: sensor_log.csv ({len(rows)} 条记录)")

if __name__ == "__main__":
    generate()
