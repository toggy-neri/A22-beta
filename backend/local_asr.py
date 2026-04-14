import os
import numpy as np
import logging
from typing import Optional, Union
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("local_asr_logger")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler("local_asr.log", maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(console_formatter)
logger.addHandler(file_handler)

ASR_MODEL_NAME = "base"
ASR_DEVICE = "cuda"

class LocalASR:
    def __init__(self, model_name: str = ASR_MODEL_NAME, device: str = ASR_DEVICE):
        self.model_name = model_name
        self.device = device
        self.model = None
        self._initialized = False
        
        self._init_model()
    
    def _init_model(self):
        if self._initialized:
            return
        
        try:
            import whisper
            
            logger.info(f"[LocalASR] Initializing Whisper model: {self.model_name}")
            logger.info(f"[LocalASR] Target device: {self.device}")
            
            self.model = whisper.load_model(self.model_name, device=self.device)
            
            self._initialized = True
            logger.info("[LocalASR] Model initialized successfully")
            
        except ImportError as e:
            logger.error(f"[LocalASR] Whisper not installed. Please run: pip install openai-whisper")
            raise ImportError(
                "OpenAI Whisper is required for local ASR. Install with:\n"
                "pip install openai-whisper"
            ) from e
        except Exception as e:
            logger.error(f"[LocalASR] Failed to initialize model: {e}")
            raise
    
    def pcm_to_numpy(self, pcm_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
        audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32768.0
        return audio_float
    
    def transcribe(
        self, 
        audio_input: Union[bytes, np.ndarray, str],
        sample_rate: int = 16000,
        language: str = "zh"
    ) -> str:
        if not self._initialized:
            self._init_model()
        
        if isinstance(audio_input, bytes):
            audio_array = self.pcm_to_numpy(audio_input, sample_rate)
        elif isinstance(audio_input, np.ndarray):
            audio_array = audio_input
        elif isinstance(audio_input, str):
            audio_array = audio_input
        else:
            raise ValueError(f"Unsupported audio input type: {type(audio_input)}")
        
        try:
            if isinstance(audio_array, str):
                result = self.model.transcribe(audio_array, language=language)
            else:
                result = self.model.transcribe(audio_array, language=language)
            
            return result.get("text", "").strip()
            
        except Exception as e:
            logger.error(f"[LocalASR] Transcription error: {e}")
            return ""
    
    def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        return self.transcribe(pcm_bytes, sample_rate)
    
    def transcribe_file(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            logger.error(f"[LocalASR] File not found: {file_path}")
            return ""
        
        return self.transcribe(file_path)


_local_asr_instance: Optional[LocalASR] = None

def get_local_asr() -> LocalASR:
    global _local_asr_instance
    if _local_asr_instance is None:
        _local_asr_instance = LocalASR()
    return _local_asr_instance

def local_asr_decode_chunk(pcm_bytes: bytes) -> str:
    asr = get_local_asr()
    return asr.transcribe_pcm(pcm_bytes)


def check_gpu_memory():
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"[LocalASR] GPU detected: {gpu_name}, Total memory: {gpu_memory:.2f} GB")
            
            if gpu_memory < 4.0:
                logger.warning(f"[LocalASR] GPU memory ({gpu_memory:.2f} GB) may be insufficient for optimal performance")
                logger.warning("[LocalASR] Consider using CPU mode or a smaller model")
            
            return True, gpu_memory
        else:
            logger.warning("[LocalASR] No GPU detected, will use CPU (slower)")
            return False, 0
    except ImportError:
        logger.warning("[LocalASR] PyTorch not installed, cannot check GPU")
        return False, 0


if __name__ == "__main__":
    print("=" * 50)
    print("Local ASR Test (Whisper)")
    print("=" * 50)
    
    has_gpu, gpu_mem = check_gpu_memory()
    
    device = "cuda" if has_gpu else "cpu"
    print(f"\nUsing device: {device}")
    
    asr = LocalASR(device=device)
    
    test_pcm_file = os.path.join(os.path.dirname(__file__), "test.pcm")
    if os.path.exists(test_pcm_file):
        print(f"\nTesting with file: {test_pcm_file}")
        with open(test_pcm_file, 'rb') as f:
            pcm_data = f.read()
        result = asr.transcribe_pcm(pcm_data)
        print(f"Result: {result}")
    else:
        print(f"\nTest file not found: {test_pcm_file}")
        print("Creating a simple test...")
        
        silence = np.zeros(16000, dtype=np.float32)
        result = asr.transcribe(silence)
        print(f"Silence test result: '{result}'")
    
    print("\n" + "=" * 50)
    print("Test completed!")
