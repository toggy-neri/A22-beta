import os
import json
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import Optional

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_env_path)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LIVETALKING_URL = "http://localhost:8010"

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

async def send_text_to_avatar(text: str, sessionid: int = 0):
    try:
        async with httpx.AsyncClient() as http:
            await http.post(
                f"{LIVETALKING_URL}/human",
                json={
                    "sessionid": sessionid,
                    "type": "echo",
                    "text": text,
                    "interrupt": True,
                },
                timeout=10.0,
            )
    except Exception as e:
        print(f"[llm_service] 发送文字给数字人失败: {e}")

SYSTEM_PROMPT = """你是一个充满共情力、专业且温暖的"心理健康数字人陪伴者"。
你的主要任务是倾听用户的困扰，针对常见的焦虑倾向、抑郁倾向、情绪波动等提供无评判的情感支持和心理引导。

核心要求：
1. 语言风格：必须像一个真正的心理关怀者一样，亲切、自然、低语速感。你的回答是要通过TTS念出来的，避免使用复杂的机器语言、无意义的列表或生僻字。
2. 交互逻辑：能够敏感捕捉用户上下文中隐藏的情绪，适时追问、澄清语义、总结问题。不可生搬硬套模板。
3. 安全准则：如果你评估用户有严重的心理危机或自伤自杀倾向，必须以极其温柔、坚定的态度建议其寻求线下专业的医疗与心理危机干预热线帮助。
4. 控制输出长度：为了降低数字人TTS合成延迟，你的单次回复不宜过长，尽量在50-150字左右，像日常对话一样有来有往。"""

SYSTEM_PROMPT_WITH_RAG = """你是一个充满共情力、专业且温暖的"心理健康数字人陪伴者"。
你的主要任务是倾听用户的困扰，针对常见的焦虑倾向、抑郁倾向、情绪波动等提供无评判的情感支持和心理引导。

核心要求：
1. 语言风格：必须像一个真正的心理关怀者一样，亲切、自然、低语速感。你的回答是要通过TTS念出来的，避免使用复杂的机器语言、无意义的列表或生僻字。
2. 交互逻辑：能够敏感捕捉用户上下文中隐藏的情绪，适时追问、澄清语义、总结问题。不可生搬硬套模板。
3. 安全准则：如果你评估用户有严重的心理危机或自伤自杀倾向，必须以极其温柔、坚定的态度建议其寻求线下专业的医疗与心理危机干预热线帮助。
4. 控制输出长度：为了降低数字人TTS合成延迟，你的单次回复不宜过长，尽量在50-150字左右，像日常对话一样有来有往。

当有参考资料时，请优先参考其中的专业知识来回答问题，但要自然地融入对话中，不要直接引用或提及"参考资料"。"""

def get_rag_context(query: str, n_results: int = 3) -> Optional[str]:
    try:
        from rag_service import get_rag_service
        rag = get_rag_service()
        if rag.get_document_count() > 0:
            context = rag.get_context_for_query(query, n_results)
            if context and context.strip():
                return context
    except Exception as e:
        print(f"[llm_service] RAG query failed: {e}")
    return None

async def generate_chat_response_stream(messages_history: list, sessionid: int = 0, use_rag: bool = True):
    messages = []
    
    rag_context = None
    if use_rag and messages_history:
        last_user_msg = None
        for msg in reversed(messages_history):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        if last_user_msg:
            rag_context = get_rag_context(last_user_msg)
    
    if rag_context:
        messages.append({"role": "system", "content": SYSTEM_PROMPT_WITH_RAG})
        messages.append({
            "role": "system", 
            "content": f"以下是与用户问题相关的参考资料，请参考这些内容来回答：\n\n{rag_context}"
        })
    else:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    
    for msg in messages_history:
        role = "assistant" if msg["role"] == "ai" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})

    try:
        full_text = ""

        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
            max_tokens=512,
            temperature=0.6,
            top_p=0.9,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_text += content
                yield f"data: {json.dumps({'content': content})}\n\n"

        if full_text.strip():
            await send_text_to_avatar(full_text, sessionid)

        yield "data: [DONE]\n\n"

    except Exception as e:
        error_msg = f"发生错误: {str(e)}"
        yield f"data: {json.dumps({'error': error_msg})}\n\n"
