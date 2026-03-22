import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
import dashscope

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# DeepSeek 兼容 OpenAI 的 API 格式
client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com" # DeepSeek的官方API endpoint
)

# 这里是专门针对心理健康数字人定制的系统指令
SYSTEM_PROMPT = """你是一个充满共情力、专业且温暖的“心理健康数字人陪伴者”。
你的主要任务是倾听用户的困扰，针对常见的焦虑倾向、抑郁倾向、情绪波动等提供无评判的情感支持和心理引导。

核心要求：
1. 语言风格：必须像一个真正的心理关怀者一样，亲切、自然、低语速感。你的回答是要通过TTS念出来的，避免使用复杂的机器语言、无意义的列表或生僻字。
2. 交互逻辑：能够敏感捕捉用户上下文中隐藏的情绪，适时追问、澄清语义、总结问题。不可生搬硬套模板。
3. 安全准则：如果你评估用户有严重的心理危机或自伤自杀倾向，必须以极其温柔、坚定的态度建议其寻求线下专业的医疗与心理危机干预热线帮助。
4. 控制输出长度：为了降低数字人TTS合成延迟，你的单次回复不宜过长，尽量在50-150字左右，像日常对话一样有来有往。"""

async def generate_chat_response_stream(messages_history: list):
    """
    流式生成大模型回复，以减少等待时间
    """
    # 确保加入心理学System Prompt
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 将前端的 'ai' 角色映射为 'assistant'，'user' 还是 'user'
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
            top_p=0.9
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_text += content  

                yield f"data: {json.dumps({'content': content})}\n\n"

        tts_response = dashscope.MultiModalConversation.call(
            model="qwen3-tts-flash",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            text=full_text,   
            voice="Sunny",
            language_type="Chinese",
            stream=False
        )
        print(tts_response)
        try:
            tts_url = tts_response.output.audio.url
            yield f"data: {json.dumps({'audio_url': tts_url})}\n\n"
        except Exception as e:
            print("TTS解析失败:", e)
            yield f"data: {json.dumps({'error': 'TTS生成失败'})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        error_msg = f"发生错误: {str(e)}"
        yield f"data: {json.dumps({'error': error_msg})}\n\n"