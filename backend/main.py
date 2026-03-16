from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi.responses import StreamingResponse
import uvicorn

# 引入独立服务
from llm_service import generate_chat_response_stream

app = FastAPI(title="Digital Avatar LLM Service")

# 解决跨域问题，允许React前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:12346"],  # 前端运行的默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str   # 'user' | 'ai'
    text: str

class ChatRequest(BaseModel):
    messages: List[Message]

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式请求，获取 DeepSeek 流响应
    这是为了减少系统的延迟，也就是“字字吐出”，方便前端TTS拼接或动画口型驱动
    """
    # 转换为 LLM Service 所需的格式
    messages_history = [{"role": msg.role, "content": msg.text} for msg in request.messages]
    
    # 包装 Generator 为 SSE 格式
    return StreamingResponse(
        generate_chat_response_stream(messages_history),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=12345, reload=True)