# 语音识别服务 (ASR Service)

## 功能说明

本模块提供独立的语音识别服务，支持多种 ASR 模型。

## 支持的模型

| 模型 | 说明 | 部署方式 |
|------|------|----------|
| FunASR | 阿里达摩院 Paraformer | 本地部署 |
| Whisper | OpenAI Whisper | 本地部署 |
| Qwen ASR | 通义千问 ASR | 云端 API |

## 安装

### 本地安装

```bash
pip install -r requirements.txt
```

### Docker 部署

```bash
docker build -t asr-service .
docker run -p 9000:9000 asr-service
```

## 使用方法

### 1. 启动服务

```bash
# FunASR (推荐，中文效果最好)
python asr_service.py --model funasr --model_name paraformer-large --device cuda

# Whisper
python asr_service.py --model whisper --model_name medium --device cuda

# Qwen ASR (云端)
export DASHSCOPE_API_KEY=your_key
python asr_service.py --model qwen --device cpu
```

### 2. API 调用

#### HTTP 接口

**上传音频文件识别**
```bash
curl -X POST "http://localhost:9000/transcribe" \
  -F "file=@audio.wav"
```

**Base64 音频识别**
```bash
curl -X POST "http://localhost:9000/transcribe_base64" \
  -H "Content-Type: application/json" \
  -d '{"audio": "base64_encoded_audio"}'
```

#### WebSocket 接口

```python
import websocket
import json
import base64

ws = websocket.create_connection("ws://localhost:9000/ws")

# 发送音频
with open("audio.wav", "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode()

ws.send(json.dumps({"type": "audio", "data": audio_base64}))

# 接收结果
result = ws.recv()
print(json.loads(result))

ws.send(json.dumps({"type": "end"}))
ws.close()
```

### 3. Python API

```python
from asr_service import ASRService, ASRConfig

config = ASRConfig(
    model_type="funasr",
    model_name="paraformer-large",
    device="cuda"
)

asr = ASRService(config)

# 识别文件
text = asr.transcribe_file("audio.wav")

# 识别 PCM 数据
text = asr.transcribe_pcm(pcm_bytes)

# 识别 Base64
text = asr.transcribe_base64(audio_base64)
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --model | funasr | 模型类型 (funasr/whisper/qwen) |
| --model_name | paraformer-large | 模型名称 |
| --device | cuda | 计算设备 (cuda/cpu) |
| --port | 9000 | 服务端口 |
| --host | 0.0.0.0 | 服务地址 |

## 音频格式要求

- 采样率: 16000 Hz
- 格式: PCM / WAV
- 声道: 单声道
- 位深: 16-bit

## 性能参考

| 模型 | 设备 | RTF |
|------|------|-----|
| FunASR paraformer-large | RTX 4090 | 0.02 |
| Whisper medium | RTX 4090 | 0.05 |
| Qwen ASR | 云端 | ~0.1 |
