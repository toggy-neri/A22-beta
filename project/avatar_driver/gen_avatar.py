"""
数字人头像生成工具
从视频生成数字人数据
"""

import os
import cv2
import numpy as np
import pickle
import argparse
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AvatarGenerator:
    """数字人头像生成器"""
    
    def __init__(
        self,
        img_size: int = 192,
        face_detector: str = "dlib",
        device: str = "cuda"
    ):
        self.img_size = img_size
        self.device = device
        self.detector = None
        self._init_detector(face_detector)
    
    def _init_detector(self, detector_type: str):
        if detector_type == "dlib":
            try:
                import dlib
                self.detector = dlib.get_frontal_face_detector()
                self.predictor = dlib.shape_predictor(
                    "shape_predictor_68_face_landmarks.dat"
                )
                logger.info("Dlib detector initialized")
            except ImportError:
                logger.warning("Dlib not installed, using OpenCV")
                self._init_opencv_detector()
        else:
            self._init_opencv_detector()
    
    def _init_opencv_detector(self):
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.predictor = None
        logger.info("OpenCV detector initialized")
    
    def detect_face(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        if frame is None:
            return None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if hasattr(self.detector, 'detectMultiScale'):
            faces = self.detector.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                x, y, w, h = faces[0]
                return (x, y, x + w, y + h)
        else:
            dets = self.detector(gray, 1)
            if len(dets) > 0:
                d = dets[0]
                return (d.left(), d.top(), d.right(), d.bottom())
        
        return None
    
    def extract_face(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        padding: float = 0.2
    ) -> np.ndarray:
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        
        pad_w = int((x2 - x1) * padding)
        pad_h = int((y2 - y1) * padding)
        
        x1 = max(0, x1 - pad_w)
        y1 = max(0, y1 - pad_h)
        x2 = min(w, x2 + pad_w)
        y2 = min(h, y2 + pad_h)
        
        face = frame[y1:y2, x1:x2]
        face = cv2.resize(face, (self.img_size, self.img_size))
        
        return face
    
    def generate_from_video(
        self,
        video_path: str,
        output_dir: str,
        sample_fps: int = 25
    ) -> bool:
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        
        if not video_path.exists():
            logger.error(f"Video not found: {video_path}")
            return False
        
        output_dir.mkdir(parents=True, exist_ok=True)
        face_dir = output_dir / "face_imgs"
        full_dir = output_dir / "full_imgs"
        face_dir.mkdir(exist_ok=True)
        full_dir.mkdir(exist_ok=True)
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return False
        
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_interval = max(1, int(video_fps / sample_fps))
        
        logger.info(f"Video: {video_fps} fps, {total_frames} frames")
        logger.info(f"Sampling every {sample_interval} frames")
        
        coords = []
        frame_idx = 0
        saved_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % sample_interval == 0:
                bbox = self.detect_face(frame)
                
                if bbox is not None:
                    face = self.extract_face(frame, bbox)
                    
                    face_path = face_dir / f"{saved_idx:06d}.jpg"
                    full_path = full_dir / f"{saved_idx:06d}.jpg"
                    
                    cv2.imencode('.jpg', face)[1].tofile(str(face_path))
                    cv2.imencode('.jpg', frame)[1].tofile(str(full_path))
                    
                    coords.append(bbox)
                    saved_idx += 1
            
            frame_idx += 1
        
        cap.release()
        
        coords_path = output_dir / "coords.pkl"
        with open(coords_path, "wb") as f:
            pickle.dump(coords, f)
        
        logger.info(f"Generated {saved_idx} frames")
        logger.info(f"Output: {output_dir}")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="数字人头像生成工具")
    parser.add_argument("--video", type=str, required=True, help="输入视频路径")
    parser.add_argument("--output", type=str, required=True, help="输出目录")
    parser.add_argument("--img_size", type=int, default=192, help="人脸图像尺寸")
    parser.add_argument("--fps", type=int, default=25, help="采样帧率")
    parser.add_argument("--detector", type=str, default="opencv", help="人脸检测器")
    
    args = parser.parse_args()
    
    generator = AvatarGenerator(
        img_size=args.img_size,
        face_detector=args.detector
    )
    
    generator.generate_from_video(
        args.video,
        args.output,
        args.fps
    )


if __name__ == "__main__":
    main()
