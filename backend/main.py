from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import base64
import asyncio
import json
import httpx
from typing import List, Dict, Any, Optional
import os
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_env_path)

USE_LOCAL_ASR = os.getenv("USE_LOCAL_ASR", "false").lower() == "true"
ENABLE_RAG = os.getenv("ENABLE_RAG", "false").lower() == "true"

app = FastAPI(title="Digital Avatar LLM Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_asr_instance = None
_local_asr_instance = None
_rag_service_instance = None

def get_asr_instance():
    global _asr_instance
    if _asr_instance is None:
        from asr import RealtimeASR
        _asr_instance = RealtimeASR
    return _asr_instance

def get_local_asr_instance():
    global _local_asr_instance
    if _local_asr_instance is None:
        from local_asr import get_local_asr
        _local_asr_instance = get_local_asr()
    return _local_asr_instance

def get_rag_service():
    global _rag_service_instance
    if _rag_service_instance is None:
        from rag_service import get_rag_service as _get_rag
        _rag_service_instance = _get_rag()
    return _rag_service_instance

def asr_decode_chunk(pcm_bytes: bytes) -> str:
    if USE_LOCAL_ASR:
        try:
            asr = get_local_asr_instance()
            return asr.transcribe_pcm(pcm_bytes)
        except Exception as e:
            print(f"[ASR] Local ASR failed, falling back to cloud: {e}")
            from asr import asr_decode_chunk as cloud_asr
            return cloud_asr(pcm_bytes)
    else:
        from asr import asr_decode_chunk as cloud_asr
        return cloud_asr(pcm_bytes)

@app.websocket("/api/record")
async def record_ws(ws: WebSocket):
    await ws.accept()
    print("WebSocket connected for recording")
    
    buffer = bytearray()
    
    try:
        while True:
            msg = await ws.receive_text()
            data = eval(msg) if isinstance(msg, str) else msg
            event_type = data.get("type")

            if event_type == "input_audio_buffer.append":
                audio_base64 = data.get("audio")
                audio_bytes = base64.b64decode(audio_base64)
                buffer.extend(audio_bytes)
            
            elif event_type == "input_audio_buffer.commit":
                pass

            elif event_type == "session.finish":
                transcript = asr_decode_chunk(buffer)
                print(transcript)
                await ws.send_text(
                    json.dumps({
                        "type": "conversation.item.input_audio_transcription.completed",
                        "transcript": transcript
                    })
                )
                buffer.clear()
                await ws.close()
                print("WebSocket closed after session finish")
                break

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("WebSocket error:", e)
        await ws.close()

class Message(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    messages: List[Message]
    sessionid: int = 0
    use_rag: Optional[bool] = None

from llm_service import generate_chat_response_stream

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    messages_history = [{"role": msg.role, "content": msg.text} for msg in request.messages]
    
    use_rag = request.use_rag if request.use_rag is not None else ENABLE_RAG
    
    return StreamingResponse(
        generate_chat_response_stream(messages_history, request.sessionid, use_rag=use_rag),
        media_type="text/event-stream"
    )

class RAGQueryRequest(BaseModel):
    query: str
    n_results: int = 3

class RAGAddRequest(BaseModel):
    documents: List[str]
    metadatas: Optional[List[Dict]] = None

@app.get("/api/rag/status")
async def rag_status():
    try:
        rag = get_rag_service()
        return {
            "status": "ok",
            "document_count": rag.get_document_count(),
            "enabled": ENABLE_RAG
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "enabled": False}

@app.post("/api/rag/query")
async def rag_query(request: RAGQueryRequest):
    try:
        rag = get_rag_service()
        results = rag.query(request.query, request.n_results)
        return {"status": "ok", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/add")
async def rag_add(request: RAGAddRequest):
    try:
        rag = get_rag_service()
        count = rag.add_documents(request.documents, request.metadatas)
        return {"status": "ok", "added": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/documents")
async def rag_list_documents(limit: int = 100):
    try:
        rag = get_rag_service()
        docs = rag.list_documents(limit)
        return {"status": "ok", "documents": docs, "count": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/rag/documents/{doc_id}")
async def rag_delete_document(doc_id: str):
    try:
        rag = get_rag_service()
        success = rag.delete_document(doc_id)
        return {"status": "ok" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/rag/clear")
async def rag_clear():
    try:
        rag = get_rag_service()
        rag.clear_collection()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/asr/status")
async def asr_status():
    return {
        "mode": "local" if USE_LOCAL_ASR else "cloud",
        "model": "OpenAI/Whisper-base" if USE_LOCAL_ASR else "qwen3-asr-flash-realtime"
    }

LIVETALKING_URL = "http://localhost:8010"

@app.post("/offer")
async def offer_proxy(request: Request):
    body = await request.json()
    print(f"[Offer] Received offer request, body keys: {list(body.keys()) if body else 'empty'}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{LIVETALKING_URL}/offer",
                json=body,
                timeout=30.0
            )
            print(f"[Offer] LiveTalking response status: {resp.status_code}")
            result = resp.json()
            print(f"[Offer] LiveTalking response sessionid: {result.get('sessionid', 'N/A')}")
            return JSONResponse(content=result)
    except httpx.ConnectError as e:
        print(f"[Offer] ConnectError: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": "LiveTalking 服务未启动，请先运行 LiveTalking/app.py"}
        )
    except Exception as e:
        print(f"[Offer] Error: {type(e).__name__}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/avatars")
async def list_avatars():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{LIVETALKING_URL}/avatars", timeout=10.0)
            return JSONResponse(content=resp.json())
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={"error": "LiveTalking 服务未启动"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class SwitchAvatarRequest(BaseModel):
    sessionid: int = 0
    avatar_id: str

@app.post("/api/switch_avatar")
async def switch_avatar(request: SwitchAvatarRequest):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{LIVETALKING_URL}/switch_avatar",
                json={"sessionid": request.sessionid, "avatar_id": request.avatar_id},
                timeout=10.0
            )
            return JSONResponse(content=resp.json())
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={"error": "LiveTalking 服务未启动"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.on_event("startup")
async def startup_event():
    print(f"[Main] ASR Mode: {'Local (FunASR)' if USE_LOCAL_ASR else 'Cloud (Qwen)'}")
    print(f"[Main] RAG Enabled: {ENABLE_RAG}")
    
    if USE_LOCAL_ASR:
        try:
            print("[Main] Pre-loading local ASR model...")
            get_local_asr_instance()
            print("[Main] Local ASR model loaded successfully")
        except Exception as e:
            print(f"[Main] Warning: Failed to load local ASR model: {e}")
    
    if ENABLE_RAG:
        try:
            print("[Main] Initializing RAG service...")
            rag = get_rag_service()
            print(f"[Main] RAG service initialized, {rag.get_document_count()} documents loaded")
        except Exception as e:
            print(f"[Main] Warning: Failed to initialize RAG service: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=12345, reload=True)
