# 数字人面部驱动模块

## 功能说明

本模块提供独立的数字人面部驱动功能，支持从音频生成口型同步的视频。

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 生成数字人数据

从视频生成数字人数据：

```bash
python gen_avatar.py --video your_video.mp4 --output ./data/avatar_1 --img_size 192 --fps 25
```

参数说明：
- `--video`: 输入视频文件
- `--output`: 输出目录
- `--img_size`: 人脸图像尺寸（默认 192）
- `--fps`: 采样帧率（默认 25）

### 2. 驱动数字人

使用音频驱动数字人：

```bash
python avatar_driver.py --avatar ./data/avatar_1 --audio speech.wav --output result.mp4
```

参数说明：
- `--avatar`: 数字人数据目录
- `--audio`: 音频文件
- `--output`: 输出视频路径
- `--model`: 驱动模型（wav2lip/musetalk）
- `--device`: 计算设备（cuda/cpu）

## 支持的模型

### Wav2Lip
- 音频驱动的口型同步
- 首次运行自动下载模型

### MuseTalk
- 更高质量的口型生成
- 需要手动下载模型

## 目录结构

```
avatar_driver/
├── avatar_driver.py    # 主驱动模块
├── gen_avatar.py       # 头像生成工具
├── requirements.txt    # 依赖列表
└── models/             # 模型文件目录
    └── wav2lip.pth
```

## API 使用

```python
from avatar_driver import AvatarDriver, AvatarConfig

# 配置
config = AvatarConfig(
    avatar_id="avatar_1",
    model_type="wav2lip",
    img_size=192,
    fps=25
)

# 创建驱动器
driver = AvatarDriver(config)

# 加载数字人
driver.load_avatar("./data/avatar_1")

# 从音频生成视频
frames = driver.drive_from_audio("speech.wav")
driver.generate_video(frames, "output.mp4")
```
