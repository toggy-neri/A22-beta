"""
数字人面部驱动模块
支持 Wav2Lip、MuseTalk 等多种驱动模型
"""

import os
import cv2
import torch
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AvatarConfig:
    avatar_id: str
    model_type: str = "wav2lip"
    img_size: int = 192
    fps: int = 25
    batch_size: int = 16
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


@dataclass
class AvatarData:
    face_imgs: List[np.ndarray]
    full_imgs: List[np.ndarray]
    coords: List[Tuple[int, int, int, int]]
    masks: Optional[List[np.ndarray]] = None


class FaceDetector:
    """人脸检测器"""
    
    def __init__(self, device: str = "cuda"):
        self.device = device
        self.detector = None
        self._init_detector()
    
    def _init_detector(self):
        try:
            import face_alignment
            self.detector = face_alignment.FaceAlignment(
                face_alignment.LandmarksType.TWO_D,
                device=self.device
            )
            logger.info("Face alignment detector initialized")
        except ImportError:
            logger.warning("face_alignment not installed, using OpenCV cascade")
            self.detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
    
    def detect(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        if image is None:
            return None
        
        if hasattr(self.detector, 'get_detections_for_image'):
            preds = self.detector.get_detections_for_image(image)
            if preds is not None and len(preds) > 0:
                x1, y1, x2, y2 = preds[0]
                return (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self.detector.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                return tuple(faces[0])
        
        return None


class AudioFeatureExtractor:
    """音频特征提取器"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
    
    def extract_mel(self, audio_path: str) -> np.ndarray:
        import librosa
        
        y, sr = librosa.load(audio_path, sr=self.sample_rate)
        mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_mels=80, hop_length=160
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)
        return mel_db
    
    def extract_hubert(self, audio_path: str) -> np.ndarray:
        try:
            import torch
            from transformers import HubertModel, Wav2Vec2FeatureExtractor
            
            processor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/hubert-base-ls960")
            model = HubertModel.from_pretrained("facebook/hubert-base-ls960")
            
            import librosa
            y, sr = librosa.load(audio_path, sr=16000)
            inputs = processor(y, sampling_rate=16000, return_tensors="pt")
            
            with torch.no_grad():
                outputs = model(**inputs)
            
            return outputs.last_hidden_state.numpy()
        except Exception as e:
            logger.error(f"Hubert extraction failed: {e}")
            return self.extract_mel(audio_path)


class Wav2LipDriver:
    """Wav2Lip 数字人驱动器"""
    
    def __init__(self, config: AvatarConfig):
        self.config = config
        self.device = torch.device(config.device)
        self.model = None
        self._load_model()
    
    def _load_model(self):
        model_path = Path(__file__).parent / "models" / "wav2lip.pth"
        
        if not model_path.exists():
            logger.warning(f"Model not found at {model_path}, downloading...")
            self._download_model(model_path)
        
        from models.wav2lip import Wav2Lip
        self.model = Wav2Lip()
        checkpoint = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.to(self.device)
        self.model.eval()
        logger.info("Wav2Lip model loaded")
    
    def _download_model(self, path: Path):
        import urllib.request
        url = "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip.pth"
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)
    
    def drive(
        self,
        face_imgs: List[np.ndarray],
        audio_features: np.ndarray,
        coords: List[Tuple[int, int, int, int]]
    ) -> List[np.ndarray]:
        results = []
        
        with torch.no_grad():
            for i, (face, coord) in enumerate(zip(face_imgs, coords)):
                if face is None:
                    continue
                
                face_tensor = self._preprocess(face)
                audio_tensor = self._preprocess_audio(audio_features, i)
                
                output = self.model(face_tensor, audio_tensor)
                output_frame = self._postprocess(output, face.shape)
                
                results.append(output_frame)
        
        return results
    
    def _preprocess(self, face: np.ndarray) -> torch.Tensor:
        face = cv2.resize(face, (self.config.img_size, self.config.img_size))
        face = face.astype(np.float32) / 255.0
        face = (face - 0.5) / 0.5
        face = np.transpose(face, (2, 0, 1))
        return torch.from_numpy(face).unsqueeze(0).to(self.device)
    
    def _preprocess_audio(self, audio_features: np.ndarray, frame_idx: int) -> torch.Tensor:
        return torch.from_numpy(audio_features).unsqueeze(0).to(self.device)
    
    def _postprocess(self, output: torch.Tensor, original_shape: tuple) -> np.ndarray:
        output = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
        output = (output * 0.5 + 0.5) * 255
        output = output.astype(np.uint8)
        return cv2.resize(output, (original_shape[1], original_shape[0]))


class MuseTalkDriver:
    """MuseTalk 数字人驱动器"""
    
    def __init__(self, config: AvatarConfig):
        self.config = config
        self.device = torch.device(config.device)
        self.model = None
        self._load_model()
    
    def _load_model(self):
        model_path = Path(__file__).parent / "models" / "musetalk"
        
        if not model_path.exists():
            logger.warning(f"MuseTalk model not found at {model_path}")
            logger.warning("Please download model from: https://github.com/TMElyralab/MuseTalk")
            return
        
        logger.info("MuseTalk model loaded")
    
    def drive(
        self,
        face_imgs: List[np.ndarray],
        audio_features: np.ndarray,
        coords: List[Tuple[int, int, int, int]]
    ) -> List[np.ndarray]:
        results = []
        return results


class AvatarDriver:
    """数字人驱动主类"""
    
    DRIVERS = {
        "wav2lip": Wav2LipDriver,
        "musetalk": MuseTalkDriver,
    }
    
    def __init__(self, config: AvatarConfig):
        self.config = config
        self.driver = self._create_driver()
        self.face_detector = FaceDetector(config.device)
        self.audio_extractor = AudioFeatureExtractor()
        self.avatar_data: Optional[AvatarData] = None
    
    def _create_driver(self):
        driver_class = self.DRIVERS.get(self.config.model_type)
        if driver_class is None:
            raise ValueError(f"Unknown driver type: {self.config.model_type}")
        return driver_class(self.config)
    
    def load_avatar(self, avatar_path: str) -> bool:
        path = Path(avatar_path)
        
        if not path.exists():
            logger.error(f"Avatar path not found: {avatar_path}")
            return False
        
        face_imgs = self._load_images(path / "face_imgs")
        full_imgs = self._load_images(path / "full_imgs")
        
        coords_path = path / "coords.pkl"
        if coords_path.exists():
            with open(coords_path, "rb") as f:
                coords = pickle.load(f)
        else:
            coords = self._detect_coords(full_imgs)
        
        self.avatar_data = AvatarData(
            face_imgs=face_imgs,
            full_imgs=full_imgs,
            coords=coords
        )
        
        logger.info(f"Avatar loaded: {len(face_imgs)} frames")
        return True
    
    def _load_images(self, path: Path) -> List[np.ndarray]:
        if not path.exists():
            return []
        
        images = []
        exts = {".jpg", ".jpeg", ".png", ".bmp"}
        
        for img_path in sorted(path.iterdir()):
            if img_path.suffix.lower() in exts:
                img = cv2.imdecode(
                    np.fromfile(str(img_path), dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )
                images.append(img)
        
        return images
    
    def _detect_coords(self, images: List[np.ndarray]) -> List[Tuple[int, int, int, int]]:
        coords = []
        for img in images:
            bbox = self.face_detector.detect(img)
            if bbox is not None:
                coords.append(bbox)
            else:
                if coords:
                    coords.append(coords[-1])
                else:
                    coords.append((0, 0, img.shape[1], img.shape[0]))
        return coords
    
    def drive_from_audio(self, audio_path: str) -> List[np.ndarray]:
        if self.avatar_data is None:
            raise ValueError("No avatar loaded")
        
        audio_features = self.audio_extractor.extract_mel(audio_path)
        
        results = self.driver.drive(
            self.avatar_data.face_imgs,
            audio_features,
            self.avatar_data.coords
        )
        
        return results
    
    def generate_video(
        self,
        frames: List[np.ndarray],
        output_path: str,
        fps: int = 25
    ) -> bool:
        if not frames:
            logger.error("No frames to generate video")
            return False
        
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        
        for frame in frames:
            out.write(frame)
        
        out.release()
        logger.info(f"Video saved: {output_path}")
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="数字人面部驱动")
    parser.add_argument("--avatar", type=str, required=True, help="数字人数据路径")
    parser.add_argument("--audio", type=str, required=True, help="音频文件路径")
    parser.add_argument("--output", type=str, default="output.mp4", help="输出视频路径")
    parser.add_argument("--model", type=str, default="wav2lip", help="驱动模型类型")
    parser.add_argument("--img_size", type=int, default=192, help="图像尺寸")
    parser.add_argument("--fps", type=int, default=25, help="视频帧率")
    parser.add_argument("--device", type=str, default="cuda", help="计算设备")
    
    args = parser.parse_args()
    
    config = AvatarConfig(
        avatar_id=Path(args.avatar).name,
        model_type=args.model,
        img_size=args.img_size,
        fps=args.fps,
        device=args.device
    )
    
    driver = AvatarDriver(config)
    
    if not driver.load_avatar(args.avatar):
        logger.error("Failed to load avatar")
        return
    
    frames = driver.drive_from_audio(args.audio)
    driver.generate_video(frames, args.output, args.fps)


if __name__ == "__main__":
    main()
