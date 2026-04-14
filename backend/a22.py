"""
a22.py — 一键启动脚本

启动顺序：
  1. LiveTalking 数字人后端（aiohttp, port 8010）
  2. FastAPI 主服务（uvicorn, port 12345）

使用：
  cd d:\self\a22\backend
  python a22.py
"""

import subprocess
import sys
import os
import time
import signal

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
LIVETALKING_DIR = os.path.join(BACKEND_DIR, "LiveTalking")

LIVETALKING_CMD = [
    sys.executable, "app.py",
    "--transport", "webrtc",
    "--model", "wav2lip",
    "--avatar_id", "wav2lip256_avatar1",
    "--listenport", "8010",
]

FASTAPI_CMD = [
    sys.executable, "-m", "uvicorn",
    "main:app",
    "--host", "0.0.0.0",
    "--port", "12345",
    "--reload",
]

processes = []

def shutdown(signum=None, frame=None):
    print("\n[a22] 正在关闭所有服务...")
    for p in processes:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

if __name__ == "__main__":
    lt_proc = subprocess.Popen(
        LIVETALKING_CMD,
        cwd=LIVETALKING_DIR,
    )
    processes.append(lt_proc)

    # 等待 LiveTalking 初始化（模型加载较慢）
    time.sleep(10)

    api_proc = subprocess.Popen(
        FASTAPI_CMD,
        cwd=BACKEND_DIR,
    )
    processes.append(api_proc)

    print("  - LiveTalking: http://localhost:8010")
    print("  - FastAPI:     http://localhost:12345")
    # 等待任一子进程退出
    while True:
        for p in processes:
            ret = p.poll()
            if ret is not None:
                print(f"[a22] 子进程 {p.pid} 已退出，返回码 {ret}，关闭所有服务...")
                shutdown()
        time.sleep(2)
