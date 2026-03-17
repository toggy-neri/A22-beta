# asr.py
import base64
import json
import threading
import time
import websocket
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

# ----------------------------
# 初始化日志
# ----------------------------
logger = logging.getLogger("asr_logger")
logger.setLevel(logging.DEBUG)

# 控制台输出
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 文件输出（循环日志，最大 10MB，保留 5 个备份）
file_handler = RotatingFileHandler("asr.log", maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(console_formatter)
logger.addHandler(file_handler)

# ----------------------------
# 配置 WebSocket 连接大模型的 ASR 模型
# ----------------------------
API_KEY = "sk-24ec33f2eca840bca6f3ae07429f69f9"  # 你的 DashScope/DeepSeek API Key
QWEN_MODEL = "qwen3-asr-flash-realtime"
BASE_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
URL = f"{BASE_URL}?model={QWEN_MODEL}"

HEADERS = [
    "Authorization: Bearer " + API_KEY,
    "OpenAI-Beta: realtime=v1"
]

# ----------------------------
# ASR 转写主类
# ----------------------------
class RealtimeASR:
    def __init__(self):
        self.ws: Optional[websocket.WebSocketApp] = None
        self.final_transcript = ""
        self.is_running = False

    def start_session(self):
        """建立 WebSocket 连接"""
        self.ws = websocket.WebSocketApp(
            URL,
            header=HEADERS,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.is_running = True
        thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        thread.start()

        logger.info("⏳ Waiting for WebSocket connection...")
        while not self.ws.sock or not self.ws.sock.connected:
            time.sleep(0.1)
        logger.info("✅ WebSocket connection established.")

    def on_open(self, ws):
        logger.info("✅ Connected to ASR server")
        session_event = {
            "event_id": f"event_{int(time.time() * 1000)}",
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "input_audio_format": "pcm",
                "sample_rate": 16000,
                "input_audio_transcription": {"language": "zh"},
                "turn_detection": {"type": "server_vad", "threshold": 0.0, "silence_duration_ms": 400}
            }
        }
        ws.send(json.dumps(session_event))
        logger.info(f"📩 Sent session.update")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            event_type = data.get("type")
            if event_type == "conversation.item.input_audio_transcription.completed":
                transcript = data.get("transcript")
                if transcript:
                    self.final_transcript += transcript
                    logger.info(f"📝 Partial transcript: {transcript}")
            elif event_type == "session.finished":
                logger.info(f"✅ Final transcript: {self.final_transcript}")
                self.is_running = False
                ws.close()
        except Exception as e:
            logger.error(f"Failed to parse message: {message} | Error: {e}")

    def on_error(self, ws, error):
        logger.error(f"ASR WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"ASR WebSocket closed: {close_status_code} - {close_msg}")

    def send_pcm_chunk(self, pcm_bytes: bytes):
        """发送 PCM16 音频块给模型"""
        if not self.ws or not self.ws.sock or not self.ws.sock.connected:
            logger.warning("WebSocket 未连接，无法发送音频")
            return
        b64_data = base64.b64encode(pcm_bytes).decode("utf-8")
        event = {
            "event_id": f"event_{int(time.time() * 1000)}",
            "type": "input_audio_buffer.append",
            "audio": b64_data
        }
        self.ws.send(json.dumps(event))
        logger.debug(f"PCM bytes length: {len(pcm_bytes)}")

    def finish_session(self):
        """结束会话"""
        if not self.ws or not self.ws.sock or not self.ws.sock.connected:
            return
        commit_event = {"event_id": f"event_{int(time.time() * 1000)}", "type": "input_audio_buffer.commit"}
        finish_event = {"event_id": f"event_{int(time.time() * 1000)}", "type": "session.finish"}
        self.ws.send(json.dumps(commit_event))
        self.ws.send(json.dumps(finish_event))
        logger.info("📩 Sent session.finish")

# ----------------------------
# 兼容旧接口
# ----------------------------
def asr_decode_chunk(pcm_bytes: bytes) -> str:
    asr = RealtimeASR()
    asr.start_session()

    chunk_size = 3200  # 约 0.1s 音频
    for i in range(0, len(pcm_bytes), chunk_size):
        asr.send_pcm_chunk(pcm_bytes[i:i+chunk_size])
        time.sleep(0.05)  # 模拟实时发送

    asr.finish_session()
    while asr.is_running:
        time.sleep(0.1)

    logger.info("✅ asr_decode_chunk completed")
    return asr.final_transcript