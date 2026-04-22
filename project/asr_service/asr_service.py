"""
语音识别服务 (ASR Service)
支持多种 ASR 模型：FunASR、Whisper、Qwen ASR
"""

import os
import io
import json
import time
import base64
import logging
import asyncio
import numpy as np
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ASRModelType(Enum):
    FUNASR = "funasr"
    WHISPER = "whisper"
    QWEN = "qwen"


@dataclass
class ASRConfig:
    model_type: str = "funasr"
    model_name: str = "paraformer-large"
    device: str = "cuda"
    sample_rate: int = 16000
    language: str = "zh"
    use_punc: bool = True
    use_vad: bool = True


class BaseASR(ABC):
    """ASR 基类"""
    
    def __init__(self, config: ASRConfig):
        self.config = config
        self.model = None
    
    @abstractmethod
    def load_model(self):
        pass
    
    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> str:
        pass
    
    def preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        if audio.dtype != np.float32:
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.int32:
                audio = audio.astype(np.float32) / 2147483648.0
            else:
                audio = audio.astype(np.float32)
        
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        return audio


class FunASRModel(BaseASR):
    """FunASR 模型 (阿里达摩院)"""
    
    def load_model(self):
        try:
            from funasr import AutoModel
            
            model_map = {
                "paraformer-large": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                "paraformer": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                "streaming": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
            }
            
            model_path = model_map.get(
                self.config.model_name,
                self.config.model_name
            )
            
            vad_model = "fsmn_vad" if self.config.use_vad else None
            punc_model = "ct_punc" if self.config.use_punc else None
            
            self.model = AutoModel(
                model=model_path,
                vad_model=vad_model,
                punc_model=punc_model,
                device=self.config.device
            )
            
            logger.info(f"FunASR model loaded: {model_path}")
            
        except ImportError:
            raise ImportError("Please install funasr: pip install funasr")
    
    def transcribe(self, audio: np.ndarray) -> str:
        if self.model is None:
            self.load_model()
        
        audio = self.preprocess_audio(audio)
        
        result = self.model.generate(
            input=audio,
            batch_size_s=300
        )
        
        if result and len(result) > 0:
            return result[0]["text"]
        
        return ""


class WhisperModel(BaseASR):
    """OpenAI Whisper 模型"""
    
    def load_model(self):
        try:
            import whisper
            
            model_size = self.config.model_name.replace("whisper-", "")
            if model_size not in ["tiny", "base", "small", "medium", "large"]:
                model_size = "medium"
            
            self.model = whisper.load_model(model_size, device=self.config.device)
            logger.info(f"Whisper model loaded: {model_size}")
            
        except ImportError:
            raise ImportError("Please install openai-whisper: pip install openai-whisper")
    
    def transcribe(self, audio: np.ndarray) -> str:
        if self.model is None:
            self.load_model()
        
        audio = self.preprocess_audio(audio)
        
        result = self.model.transcribe(
            audio,
            language=self.config.language
        )
        
        return result.get("text", "")


class QwenASRModel(BaseASR):
    """通义千问 ASR 模型 (云端 API)"""
    
    def load_model(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")
        
        self.model_name = "qwen3-asr-flash-realtime"
        self.ws_url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        
        logger.info("Qwen ASR configured")
    
    def transcribe(self, audio: np.ndarray) -> str:
        import websocket
        import threading
        
        if self.model is None:
            self.load_model()
        
        audio = self.preprocess_audio(audio)
        audio_bytes = (audio * 32768).astype(np.int16).tobytes()
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        result_text = ""
        result_event = threading.Event()
        
        def on_message(ws, message):
            nonlocal result_text
            data = json.loads(message)
            if data.get("type") == "response.audio_transcript.done":
                result_text = data.get("transcript", "")
                result_event.set()
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
            result_event.set()
        
        def on_close(ws, close_status_code, close_msg):
            result_event.set()
        
        def on_open(ws):
            session_update = {
                "event_id": f"event_{int(time.time() * 1000)}",
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "input_audio_format": "pcm",
                    "sample_rate": 16000,
                }
            }
            ws.send(json.dumps(session_update))
            
            audio_append = {
                "event_id": f"event_{int(time.time() * 1000) + 1}",
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            ws.send(json.dumps(audio_append))
            
            commit = {
                "event_id": f"event_{int(time.time() * 1000) + 2}",
                "type": "input_audio_buffer.commit"
            }
            ws.send(json.dumps(commit))
        
        ws = websocket.WebSocketApp(
            f"{self.ws_url}?model={self.model_name}",
            header=[f"Authorization: Bearer {self.api_key}"],
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        result_event.wait(timeout=30)
        ws.close()
        
        return result_text


class ASRService:
    """ASR 服务主类"""
    
    MODELS = {
        "funasr": FunASRModel,
        "whisper": WhisperModel,
        "qwen": QwenASRModel,
    }
    
    def __init__(self, config: ASRConfig):
        self.config = config
        self.asr = self._create_asr()
    
    def _create_asr(self) -> BaseASR:
        model_class = self.MODELS.get(self.config.model_type)
        if model_class is None:
            raise ValueError(f"Unknown ASR type: {self.config.model_type}")
        return model_class(self.config)
    
    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        audio = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio = audio.astype(np.float32) / 32768.0
        return self.asr.transcribe(audio)
    
    def transcribe_file(self, file_path: str) -> str:
        import soundfile as sf
        
        audio, sr = sf.read(file_path)
        
        if sr != self.config.sample_rate:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=self.config.sample_rate)
        
        return self.asr.transcribe(audio)
    
    def transcribe_base64(self, audio_base64: str) -> str:
        audio_bytes = base64.b64decode(audio_base64)
        return self.transcribe_pcm(audio_bytes)


def create_fastapi_app(config: ASRConfig):
    """创建 FastAPI 服务"""
    from fastapi import FastAPI, WebSocket, UploadFile, File
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="ASR Service")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    asr_service = ASRService(config)
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    @app.post("/transcribe")
    async def transcribe(file: UploadFile = File(...)):
        audio_bytes = await file.read()
        text = asr_service.transcribe_pcm(audio_bytes)
        return {"text": text}
    
    @app.post("/transcribe_base64")
    async def transcribe_base64(data: dict):
        audio_base64 = data.get("audio")
        text = asr_service.transcribe_base64(audio_base64)
        return {"text": text}
    
    @app.websocket("/ws")
    async def websocket_transcribe(websocket: WebSocket):
        await websocket.accept()
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "audio":
                    audio_base64 = data.get("data")
                    text = asr_service.transcribe_base64(audio_base64)
                    await websocket.send_json({"type": "transcript", "text": text})
                
                elif data.get("type") == "end":
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await websocket.close()
    
    return app


def main():
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description="ASR 服务")
    parser.add_argument("--model", type=str, default="funasr", help="模型类型")
    parser.add_argument("--model_name", type=str, default="paraformer-large", help="模型名称")
    parser.add_argument("--device", type=str, default="cuda", help="计算设备")
    parser.add_argument("--port", type=int, default=9000, help="服务端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务地址")
    
    args = parser.parse_args()
    
    config = ASRConfig(
        model_type=args.model,
        model_name=args.model_name,
        device=args.device
    )
    
    app = create_fastapi_app(config)
    
    logger.info(f"Starting ASR service on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
