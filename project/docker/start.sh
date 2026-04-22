#!/bin/bash
set -e

echo "=========================================="
echo "  心理诊疗室数字人系统 - 启动脚本"
echo "=========================================="

cd /app/backend

export PYTHONPATH=/app/backend:$PYTHONPATH

echo "[1/2] 启动 LiveTalking 服务 (端口 8010)..."
python LiveTalking/app.py \
    --transport webrtc \
    --model wav2lip \
    --avatar_id 贴心女医生 \
    --tts qwentts \
    --REF_FILE Cherry \
    --qwen_tts_model qwen3-tts-flash-realtime \
    --listenport 8010 &

LIVETALKING_PID=$!

sleep 5

echo "[2/2] 启动后端 API 服务 (端口 12345)..."
python main.py &

BACKEND_PID=$!

echo "=========================================="
echo "  所有服务已启动!"
echo "  - LiveTalking: http://localhost:8010"
echo "  - 后端API:    http://localhost:12345"
echo "=========================================="

trap "echo '正在停止服务...'; kill $LIVETALKING_PID $BACKEND_PID 2>/dev/null; exit 0" SIGTERM SIGINT

wait
