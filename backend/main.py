from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import base64
import asyncio
import json
from typing import List, Dict, Any
from asr import asr_decode_chunk  # 自己实现的 PCM16->文本函数

app = FastAPI(title="Digital Avatar LLM Service")

# 解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React 前端端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# WebSocket 实时录音接口
# ----------------------------
@app.websocket("/api/record")
async def record_ws(ws: WebSocket):
    await ws.accept()
    print("WebSocket connected for recording")
    
    buffer = bytearray()
    
    try:
        while True:
            msg = await ws.receive_text()
            data = eval(msg) if isinstance(msg, str) else msg  # JSON 字符串
            event_type = data.get("type")

            # ----------------------
            # 音频块追加
            # ----------------------
            if event_type == "input_audio_buffer.append":
                audio_base64 = data.get("audio")
                audio_bytes = base64.b64decode(audio_base64)
                buffer.extend(audio_bytes)
            
            # ----------------------
            # 音频提交
            # ----------------------
            elif event_type == "input_audio_buffer.commit":
                # 可以在这里做 chunk ASR 或缓存标记
                pass

            # ----------------------
            # 会话结束
            # ----------------------
            elif event_type == "session.finish":
                # 把 buffer 传给 ASR Service
                transcript = asr_decode_chunk(buffer)  # PCM16 -> 文本
                print(transcript)
                # 返回给前端
                await ws.send_text(
                    json.dumps({
                        "type": "conversation.item.input_audio_transcription.completed",
                        "transcript": transcript
                    })
                )#返回给前端的格式
                buffer.clear()
                await ws.close()
                print("WebSocket closed after session finish")
                break

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("WebSocket error:", e)
        await ws.close()


# ----------------------------
# 原有 Chat 流式接口
# ----------------------------
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

class Message(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    messages: List[Message]

# 假设你已有 generate_chat_response_stream
from llm_service import generate_chat_response_stream

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    messages_history = [{"role": msg.role, "content": msg.text} for msg in request.messages]
    return StreamingResponse(
        generate_chat_response_stream(messages_history),
        media_type="text/event-stream"
    )

# ----------------------------
# 启动
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=12345, reload=True)