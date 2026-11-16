# Python 快速入门（从 C 工程师视角）

> **写给你**：你有 C 语言基础，学 Python 会非常快。这份笔记用 C 做类比，帮你快速建立 Python 的心智模型。
> 预计时间：1 ~ 2 周（每天 2~3 小时）

---

## 一、Python vs C 速查对比

| 特性 | C | Python |
|------|---|--------|
| 类型声明 | `int a = 5;` | `a = 5` (动态类型) |
| 编译 | 需要 gcc 编译 | 解释执行 (CPython) 或 pyc 字节码 |
| 内存管理 | malloc / free | 自动 GC + 引用计数 |
| 头文件 | `#include <stdio.h>` | `import os` |
| 结构体 | `struct Point { int x; int y; };` | `{"x": 1, "y": 2}` (dict) 或 dataclass |
| 指针 | 有 | 没有 (一切皆引用) |
| 宏 | `#define PI 3.14` | `PI = 3.14` (常量约定全大写) |
| 输出 | `printf("%d\n", a);` | `print(a)` |
| 错误处理 | `if (ret != 0)` | try / except |

---

## 二、Python 核心语法（你只需这些）

### 2.1 数据结构

```python
# 列表 = C 的数组 (但可以动态扩容、混合类型)
fruits = ["apple", "banana", "cherry"]
fruits.append("date")        # 尾部添加，相当于 realloc
print(fruits[0])             # apple，索引从 0 开始 (和 C 一样)

# 字典 = C 的哈希表 / 简化版 struct
person = {"name": "张三", "age": 25}
person["age"] = 26
print(person.get("phone", "未知"))  # 类似条件访问，不会 KeyError

# 元组 = 不可变的列表
coords = (3, 4)
x, y = coords                 # 解包，类似 C 的结构体成员访问

# 集合 = 去重集合
tags = {"python", "ai", "embedded"}
tags.add("llm")
```

### 2.2 函数

```python
# 基本函数，比 C 简单太多
def add(a: int, b: int) -> int:
    return a + b

# 默认参数 + 关键字参数
def greet(name: str, greeting: str = "你好") -> str:
    return f"{greeting}，{name}！"

greet("张三")                 # 你好，张三！
greet("张三", greeting="Hi")  # Hi，张三！

# 多返回值 (C 里要返回 struct 或用指针参数)
def divide(a: int, b: int) -> tuple:
    quotient = a // b
    remainder = a % b
    return quotient, remainder  # 自动打包成元组

q, r = divide(17, 5)          # q=3, r=2
```

### 2.3 类

```python
class Motor:
    """电机类 — 对应 C 的 struct + 一组函数"""

    def __init__(self, power: float, voltage: float = 24.0):
        """构造函数，self 相当于 C++ 的 this 指针"""
        self.power = power      # 成员变量直接 self.xxx
        self.voltage = voltage
        self.running = False

    def start(self) -> None:
        """成员方法"""
        if not self.running:
            self.running = True
            print(f"电机启动，功率 {self.power}W")

    def stop(self) -> None:
        self.running = False

    @property
    def status(self) -> str:
        """属性装饰器，把方法变属性访问"""
        return "运行中" if self.running else "已停止"


# 使用
m = Motor(power=500.0)        # 实例化，不需要 new 关键字
m.start()
print(m.status)                # 运行中
```

### 2.4 控制流

```python
# if / elif / else — 和 C 类似但没有括号和大括号
temp = 45.0
if temp > 80:
    print("过热保护触发")
elif temp > 50:
    print("温度偏高")
else:
    print("正常")

# for 循环 — 比 C 灵活
for i in range(5):             # 类似 for(i=0; i<5; i++)
    print(i)

for fruit in ["苹果", "香蕉", "梨"]:  # 遍历容器
    print(fruit)

# enumerate 同时拿索引和值
for idx, val in enumerate(["a", "b", "c"]):
    print(idx, val)            # 0 a, 1 b, 2 c

# while — 和 C 差不多
count = 0
while count < 3:
    print(count)
    count += 1
```

### 2.5 文件与 IO

```python
# 文本文件 (类似 C 的 fopen/fgets/fclose)
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()          # 自动关闭，不用手动 fclose

# 写文件
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("Hello\n")
    print("World", file=f)      # print 也能写文件

# 读 CSV (做数据处理常用)
import csv
with open("sensors.csv", "r") as f:
    reader = csv.DictReader(f)  # 按列名读
    for row in reader:
        print(row["temperature"])
```

### 2.6 错误处理

```python
# try / except — 比 C 的错误码优雅
def read_config(path: str) -> dict:
    try:
        with open(path, "r") as f:
            import json
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件不存在: {path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return {}
```

---

## 三、AI 生态必会的 Python 库

### 3.1 数据处理三件套

```python
# NumPy — 数值计算 (C 底层，快)
import numpy as np
arr = np.array([1, 2, 3, 4, 5])
print(arr * 2)                 # [2 4 6 8 10]，向量化操作，比 C for 循环还快
print(arr.mean())              # 3.0

# Pandas — 表格数据处理 (Excel/CSV 杀手)
import pandas as pd
df = pd.read_csv("sensors.csv")
print(df.head())               # 前 5 行
print(df["temperature"].mean()) # 列统计

# Matplotlib — 绑图
import matplotlib.pyplot as plt
plt.plot([1, 2, 3], [4, 5, 6])
plt.savefig("chart.png")
```

### 3.2 HTTP / Web

```python
# requests — 调 API 必备 (类似 curl)
import requests
resp = requests.get("https://api.example.com/data")
data = resp.json()             # 自动解析 JSON

# FastAPI — 写后端 API (比 Flask 现代，类型提示友好)
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

# 启动: uvicorn main:app --reload
```

### 3.3 异步编程

```python
# async / await — 写 LLM 流式输出、高并发 API 必备
import asyncio

async def fetch_data(url: str) -> str:
    print(f"开始请求 {url}")
    await asyncio.sleep(1)      # 模拟异步等待
    return f"来自 {url} 的数据"

async def main():
    # 并发执行，比串行快 N 倍
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3"),
    )
    print(results)

asyncio.run(main())
```

---

## 四、环境配置

### 4.1 Python 版本
- 用 **Python 3.11+**（不要用 3.12 以下，一些 AI 库可能有兼容问题）
- 下载：https://www.python.org/downloads/ 或用 Anaconda

### 4.2 虚拟环境（重要！）
```bash
# 创建虚拟环境
python -m venv venv

# 激活 (Windows)
venv\Scripts\activate

# 激活 (Linux/Mac)
# source venv/bin/activate

# 安装包
pip install fastapi uvicorn requests pandas

# 导出依赖清单
pip freeze > requirements.txt
```

### 4.3 推荐的第一个项目结构
```
my-ai-app/
├── venv/                  # 虚拟环境
├── requirements.txt       # 依赖清单
├── README.md              # 项目说明
├── src/
│   ├── main.py            # 入口
│   ├── api/               # API 路由
│   ├── services/          # 业务逻辑
│   └── utils/             # 工具函数
└── tests/                 # 测试
```

---

## 五、推荐学习资源

| 资源 | 类型 | 链接 | 适合 |
|------|------|------|------|
| Python 官方教程 | 文档 | https://docs.python.org/zh-cn/3/ | 查语法 |
| 廖雪峰 Python 教程 | 中文博客 | https://www.liaoxuefeng.com/wiki/1016959663602400 | 入门快 |
| Real Python | 英文教程 | https://realpython.com/ | 系统学习 |
| Pandas 官方 10 分钟 | 文档 | https://pandas.pydata.org/docs/user_guide/10min.html | 速查 |
| FastAPI 官方教程 | 文档 | https://fastapi.tiangolo.com/zh/ | 写 API |

---

## 六、练习项目（动手才是王道）

### 练习 1：传感器数据处理脚本
你有嵌入式基础，模拟你熟悉的场景：
- 读取一个 CSV 格式的传感器日志文件（时间戳 + 温度 + 压力）
- 统计最大值、最小值、平均值
- 画出温度变化曲线
- 检测异常值（超过阈值的记录）

### 练习 2：串口数据采集 + Web 展示
结合你的嵌入式背景：
- 用 `pyserial` 从串口读取 Arduino/STM32 发送的传感器数据
- 实时存入 CSV 或 SQLite
- 用 FastAPI 暴露一个 `/api/current` 接口返回最新数据
- 用 Streamlit 做一个实时监控仪表盘

### 练习 3：API 调用工具
- 调用一个公开 API（如天气 API、股票 API）
- 用 `requests` + 异步批量查询
- 结果存成 CSV / Excel

> **以上三个小项目做完，你的 Python 基础就够用了。** 后面学 LLM 应用开发基本就是在这些基础之上"搭积木"。
