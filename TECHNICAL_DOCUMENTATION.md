# 心理诊疗室 - 数字人全栈技术文档

## 项目概述

本项目是一个基于 AI 数字人的心理健康咨询系统，集成了实时语音识别（ASR）、大语言模型（LLM）、语音合成（TTS）和数字人渲染技术，为用户提供沉浸式的心理咨询服务体验。

### 核心功能

- **实时数字人交互**：通过 WebRTC 实现低延迟的视频流传输
- **语音对话**：支持语音输入识别和语音合成输出
- **AI 心理咨询**：基于大语言模型的智能对话系统
- **多数字人形象**：支持切换不同的数字人形象
- **RAG 知识增强**：可选的知识库检索增强生成

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户界面层                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    React Frontend (Vite + Tailwind)              │   │
│  │  - 欢迎页面 / 主界面                                              │   │
│  │  - WebRTC 视频播放                                                │   │
│  │  - 聊天面板 / 控制按钮                                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              后端服务层                                   │
│  ┌──────────────────────┐    ┌──────────────────────┐                  │
│  │   FastAPI Service    │    │   LiveTalking Service │                  │
│  │   (Port: 12345)      │    │   (Port: 8010)        │                  │
│  │                      │    │                       │                  │
│  │  - ASR WebSocket     │    │  - WebRTC Signaling   │                  │
│  │  - Chat Stream API   │    │  - Avatar Rendering   │                  │
│  │  - LLM Integration   │    │  - TTS Integration    │                  │
│  │  - RAG Service       │    │  - Session Management │                  │
│  └──────────────────────┘    └──────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              外部服务层                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │  Qwen LLM  │  │  Qwen TTS  │  │  Qwen ASR  │  │  DeepSeek  │       │
│  │  (通义千问) │  │ (语音合成)  │  │ (语音识别) │  │   (可选)   │       │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 技术栈

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.2.0 | UI 框架 |
| TypeScript | 5.2.2 | 类型安全 |
| Vite | 5.1.0 | 构建工具 |
| Tailwind CSS | 3.4.1 | 样式框架 |
| Lucide React | 0.330.0 | 图标库 |

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 后端语言 |
| FastAPI | - | Web 框架（主服务） |
| aiohttp | - | 异步 HTTP/WebRTC 服务 |
| aiortc | - | WebRTC 实现 |
| OpenAI SDK | - | LLM API 调用 |
| DashScope SDK | - | 阿里云 AI 服务 |

### AI 服务

| 服务 | 提供商 | 模型 |
|------|--------|------|
| LLM | 阿里云 DashScope | qwen-plus |
| TTS | 阿里云 DashScope | qwen3-tts-flash-realtime |
| ASR | 阿里云 DashScope | qwen3-asr-flash-realtime |

---

## 目录结构

```
a22/
├── frontend/                    # 前端项目
│   ├── src/
│   │   ├── App.tsx             # 主应用组件
│   │   ├── main.tsx            # 入口文件
│   │   └── index.css           # 全局样式
│   ├── dist/                    # 构建输出
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── backend/                     # 后端项目
│   ├── LiveTalking/            # 数字人核心服务
│   │   ├── app.py              # 主入口
│   │   ├── config.py           # 配置解析
│   │   ├── llm.py              # LLM 集成
│   │   ├── registry.py         # 插件注册
│   │   ├── avatars/            # 数字人模型
│   │   │   ├── base_avatar.py  # 基类
│   │   │   ├── wav2lip_avatar.py
│   │   │   ├── musetalk_avatar.py
│   │   │   └── ultralight_avatar.py
│   │   ├── server/             # 服务端模块
│   │   │   ├── routes.py       # API 路由
│   │   │   ├── rtc_manager.py  # WebRTC 管理
│   │   │   ├── session_manager.py
│   │   │   └── webrtc.py       # 视频播放器
│   │   ├── tts/                # TTS 插件
│   │   │   ├── base_tts.py
│   │   │   ├── qwentts.py      # 通义千问 TTS
│   │   │   └── ...
│   │   ├── utils/              # 工具函数
│   │   └── web/                # 静态文件
│   │
│   ├── main.py                 # FastAPI 主服务
│   ├── llm_service.py          # LLM 服务封装
│   ├── rag_service.py          # RAG 检索服务
│   ├── asr.py                  # ASR 语音识别
│   ├── local_asr.py            # 本地 ASR
│   ├── start_all.py            # 一键启动脚本
│   └── .env                    # 环境变量配置
│
├── data/
│   └── avatars/                # 数字人数据
│       └── avatar_x/
│           ├── face_imgs/      # 人脸图像序列
│           ├── full_imgs/      # 全身图像序列
│           └── coords.pkl      # 坐标数据
│
└── README.md
```

---

## 前端架构

### 组件结构

```tsx
App.tsx
├── WelcomeScreen (欢迎页面)
│   ├── 动态背景 (渐变 + 浮动气泡)
│   ├── Logo (大脑图标)
│   ├── 标题 "心理诊疗室"
│   └── 进入按钮
│
└── MainInterface (主界面)
    ├── AvatarVideo (数字人视频区域)
    │   ├── WebRTC Video Player
    │   └── Connection Status
    │
    ├── ControlBar (控制栏)
    │   ├── MicButton (麦克风开关)
    │   ├── VideoButton (摄像头开关)
    │   └── AvatarSelector (数字人选择)
    │
    ├── UserCamera (用户摄像头小窗)
    │
    └── ChatPanel (聊天面板)
        ├── MessageList (消息列表)
        └── InputArea (输入框)
```

### 状态管理

```typescript
// 核心状态
const [showWelcome, setShowWelcome] = useState(true);     // 欢迎页显示
const [isEntering, setIsEntering] = useState(false);      // 进入动画
const [isRecording, setIsRecording] = useState(false);    // 录音状态
const [videoEnabled, setVideoEnabled] = useState(true);   // 摄像头状态
const [messages, setMessages] = useState<Message[]>([]);  // 聊天消息
const [avatars, setAvatars] = useState<AvatarInfo[]>([]); // 数字人列表
const [connectionState, setConnectionState] = useState('disconnected');
```

### WebRTC 连接流程

```typescript
// 1. 创建 RTCPeerConnection
const pc = new RTCPeerConnection({
  sdpSemantics: 'unified-plan',
  iceServers: []
});

// 2. 添加收发器
pc.addTransceiver('video', { direction: 'recvonly' });
pc.addTransceiver('audio', { direction: 'recvonly' });

// 3. 创建并发送 Offer
const offer = await pc.createOffer();
await pc.setLocalDescription(offer);

// 4. 发送到后端
const response = await fetch('http://localhost:12345/offer', {
  method: 'POST',
  body: JSON.stringify({ sdp: offer.sdp, type: offer.type })
});

// 5. 设置远程描述
const answer = await response.json();
await pc.setRemoteDescription(answer);
```

---

## 后端架构

### 服务架构

项目采用双服务架构：

1. **LiveTalking Service (端口 8010)**
   - 数字人渲染引擎
   - WebRTC 信令处理
   - TTS 语音合成
   - 实时视频流推送

2. **FastAPI Service (端口 12345)**
   - ASR 语音识别 WebSocket
   - LLM 对话流式接口
   - RAG 知识检索
   - 数字人切换 API

### LiveTalking 核心模块

#### 1. Avatar 基类 (base_avatar.py)

```python
class BaseAvatar:
    """数字人基类，定义通用接口"""
    
    def __init__(self, opt):
        self.sample_rate = 16000
        self.chunk = self.sample_rate // (opt.fps * 2)  # 320 samples
        self.res_frame_queue = Queue()
        
    def put_msg_txt(self, text: str, datainfo: dict):
        """接收文本，触发 TTS 和口型生成"""
        
    def process_frames(self):
        """处理视频帧，推送到 WebRTC"""
        
    def get_avatar_length(self):
        """获取数字人帧数"""
```

#### 2. Wav2Lip Avatar (wav2lip_avatar.py)

基于 Wav2Lip 模型的数字人实现：
- 音频驱动的口型同步
- 人脸区域检测和替换
- 支持自定义视频循环

#### 3. TTS 插件系统

```python
# 注册机制
@register("tts", "qwentts")
class QwenTTS(BaseTTS):
    def __init__(self, opt, parent):
        self.voice = opt.REF_FILE  # 音色
        self.model = 'qwen3-tts-flash-realtime'
        
    def push_text(self, text: str):
        """推送文本进行合成"""
        
    def get_audio_chunk(self):
        """获取音频块"""
```

支持的 TTS 引擎：
- `edgetts` - 微软 Edge TTS
- `qwentts` - 阿里云通义千问 TTS
- `gpt-sovits` - GPT-SoVITS
- `cosyvoice` - CosyVoice
- `fishtts` - Fish TTS

### FastAPI 服务模块

#### 1. ASR WebSocket (main.py)

```python
@app.websocket("/api/record")
async def record_ws(ws: WebSocket):
    await ws.accept()
    buffer = bytearray()
    
    while True:
        msg = await ws.receive_text()
        data = json.loads(msg)
        
        if data["type"] == "input_audio_buffer.append":
            buffer.extend(base64.b64decode(data["audio"]))
        elif data["type"] == "session.finish":
            transcript = asr_decode_chunk(buffer)
            await ws.send_text(json.dumps({
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": transcript
            }))
```

#### 2. Chat Stream API

```python
@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    messages = await request.json()
    
    async def generate():
        async for chunk in generate_chat_response_stream(messages):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

#### 3. RAG 服务

```python
class RAGService:
    def __init__(self):
        self.embedding_model = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        
    def add_documents(self, documents: List[str]):
        """添加文档到知识库"""
        
    def query(self, query_text: str, n_results: int = 5):
        """检索相关文档"""
```

---

## API 接口文档

### WebRTC 信令

#### POST /offer
建立 WebRTC 连接

**请求：**
```json
{
  "sdp": "...",
  "type": "offer"
}
```

**响应：**
```json
{
  "sdp": "...",
  "type": "answer",
  "sessionid": 123456
}
```

### 数字人管理

#### GET /api/avatars
获取可用数字人列表

**响应：**
```json
{
  "code": 0,
  "avatars": [
    {
      "id": "avatar_1",
      "name": "贴心女医生",
      "has_full_imgs": true,
      "has_face_imgs": true,
      "frame_count": 200
    }
  ]
}
```

#### POST /api/switch_avatar
切换数字人

**请求：**
```json
{
  "sessionid": 123456,
  "avatar_id": "avatar_2"
}
```

### 对话接口

#### POST /api/chat/stream
流式对话

**请求：**
```json
{
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "sessionid": 123456
}
```

**响应（SSE）：**
```
data: {"content": "你"}
data: {"content": "好"}
data: {"audio_url": "http://..."}
data: [DONE]
```

#### WebSocket /api/record
语音识别

**发送：**
```json
{
  "type": "input_audio_buffer.append",
  "audio": "base64_encoded_pcm"
}
```

**接收：**
```json
{
  "type": "conversation.item.input_audio_transcription.completed",
  "transcript": "识别的文字"
}
```

---

## 配置说明

### 环境变量 (.env)

```bash
# 阿里云 DashScope API Key
DASHSCOPE_API_KEY=your_api_key_here

# DeepSeek API Key (可选)
DEEPSEEK_API_KEY=your_deepseek_key

# 是否启用本地 ASR
USE_LOCAL_ASR=false

# 是否启用 RAG
ENABLE_RAG=false
```

### 命令行参数

```bash
python app.py \
  --transport webrtc \        # 传输方式
  --model wav2lip \           # 数字人模型
  --avatar_id 贴心女医生 \     # 数字人 ID
  --tts qwentts \             # TTS 引擎
  --REF_FILE Cherry \         # TTS 音色
  --qwen_tts_model qwen3-tts-flash-realtime
```

---

## 部署指南

### 开发环境

1. **安装依赖**
```bash
# 前端
cd frontend
npm install

# 后端
cd backend
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
cp backend/.env.example backend/.env
# 编辑 .env 填入 API Key
```

3. **启动服务**
```bash
cd backend
python start_all.py
```

4. **启动前端开发服务器**
```bash
cd frontend
npm run dev
```

### 生产环境

1. **构建前端**
```bash
cd frontend
npm run build
```

2. **启动后端服务**
```bash
cd backend
python start_all.py
```

3. **访问应用**
打开 `frontend/dist/index.html` 或配置 Nginx 反向代理

---

## 数据流

### 语音对话流程

```
用户语音 → 浏览器采集 → WebSocket → ASR 服务 → 文字
                                                    ↓
数字人视频 ← WebRTC ← 视频帧 ← 口型合成 ← TTS 音频 ← LLM
```

### 文本对话流程

```
用户输入 → HTTP POST → LLM Service → 流式响应
                                    ↓
                         TTS 合成 → 数字人口型 → WebRTC 推流
```

---

## 扩展开发

### 添加新的数字人

1. 准备视频素材
2. 运行头像生成脚本：
```bash
python avatars/wav2lip/genavatar.py --video your_video.mp4 --img_size 192
```
3. 数据会保存到 `data/avatars/` 目录

### 添加新的 TTS 引擎

1. 创建 `tts/your_tts.py`：
```python
from .base_tts import BaseTTS
from registry import register

@register("tts", "your_tts")
class YourTTS(BaseTTS):
    def __init__(self, opt, parent):
        super().__init__(opt, parent)
        
    def push_text(self, text: str):
        # 实现文本推送
        
    def get_audio_chunk(self):
        # 返回音频数据
```

2. 使用：`--tts your_tts`

### 添加知识库文档

```python
from rag_service import get_rag_service

rag = get_rag_service()
rag.add_documents([
    "心理健康知识条目1",
    "心理健康知识条目2",
])
```

---

## 性能优化

### 前端优化

- 使用 WebRTC 实现低延迟视频传输
- 音频采集使用 16kHz 采样率
- 消息列表虚拟滚动（大量消息时）

### 后端优化

- 异步处理（asyncio）
- TTS 音频流式输出
- 数字人帧预加载和缓存
- 多进程/多线程处理

---

## 常见问题

### Q: WebRTC 连接失败？
A: 检查后端服务是否启动，端口 8010 和 12345 是否被占用。

### Q: TTS 没有声音？
A: 确认 DASHSCOPE_API_KEY 已正确配置，检查网络连接。

### Q: 数字人切换失败？
A: 确认目标数字人数据存在，检查 `data/avatars/` 目录。

### Q: ASR 识别不准确？
A: 检查麦克风权限，确保音频采样率为 16kHz。

---

## 版本历史

- **v1.0** - 初始版本，基础数字人功能
- **v1.1** - 添加欢迎页面，白色主题
- **v1.2** - 集成 Qwen TTS 实时语音合成
- **v1.3** - 添加 RAG 知识库支持

---

## 许可证

本项目基于 Apache License 2.0 开源协议。
