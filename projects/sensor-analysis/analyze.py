"""传感器数据分析 —— 你的第一个 Python 数据处理脚本

任务：读取 sensor_log.csv，完成下面 3 个 TODO
运行：venv\\Scripts\\python.exe analyze.py

对照 C 语言想一想：
- pandas 的 DataFrame 就像一张"带列名的二维数组"
- df["temperature"] 取出一整列，类似 C 里遍历数组但不用写 for 循环
"""
import pandas as pd
import matplotlib.pyplot as plt

# matplotlib 中文显示必备配置（默认字体不含中文字形，会显示成方块）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]  # 微软雅黑
plt.rcParams["axes.unicode_minus"] = False  # 负号正常显示

THRESHOLD = 60.0  # 温度报警阈值 (°C)，类似 C 的 #define

# ============================================================
# TODO 1: 用 pandas 读取 sensor_log.csv，赋值给变量 df
# 提示：pd.read_csv("sensor_log.csv")
# ============================================================
df = pd.read_csv("sensor_log.csv")

if df is not None:
    print(f"读取成功，共 {len(df)} 条记录")
    print(df.head())  # 预览前 5 行，类似 C 里打印数组前几个元素

    # TODO 2 答案：三个独立操作，分别打印
    print(f"\n最高温度: {df['temperature'].max()} °C")
    print(f"最低温度: {df['temperature'].min()} °C")
    print(f"平均温度: {df['temperature'].mean():.2f} °C")  # :.2f 保留两位小数

    # TODO 3 答案：布尔索引筛选 + print 输出
    abnormal = df[df["temperature"] > THRESHOLD]
    print(f"\n发现 {len(abnormal)} 条超温异常记录:")
    print(abnormal)
    # ========================================================
    # TODO 2: 打印温度列的最大值、最小值、平均值
    # 提示：df["temperature"].max()  .min()  .mean()
    # 用 f-string 打印，例如: print(f"最高温度: {...} °C")
    # ========================================================


    # ========================================================
    # TODO 3: 找出温度超过 THRESHOLD 的所有异常行并打印
    # 提示：df[df["temperature"] > THRESHOLD]
    # 这叫"布尔索引"，C 里要写 if 循环筛选，这里一行搞定
    # ========================================================


    # === 完成后取消下面注释，画出温度曲线（奖励环节 🎁）===
    plt.figure(figsize=(12, 4))
    plt.plot(pd.to_datetime(df["timestamp"]), df["temperature"], linewidth=0.8)
    plt.axhline(THRESHOLD, color="red", linestyle="--", label=f"报警线 {THRESHOLD}°C")
    plt.title("7 天温度变化曲线")
    plt.legend()
    plt.tight_layout()
    plt.savefig("temperature_curve.png", dpi=150)
    print("图已保存: temperature_curve.png")
else:
    print("df 还是 None，先完成 TODO 1 吧！")
