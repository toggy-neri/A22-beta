import os
import base64
import datetime
from dotenv import load_dotenv
from openai import OpenAI
# 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中 
# 初始化Ark客户端，从环境变量中读取您的API Key 
load_dotenv()
client = OpenAI( 
    # 此为默认路径，您可根据业务所在地域进行配置 
    base_url="https://ark.cn-beijing.volces.com/api/v3", 
    # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改 
    api_key=os.environ.get("ARK_API_KEY"), 
) 
 
imagesResponse = client.images.generate( 
    model="doubao-seedream-3-0-t2i-250415", 
    prompt="生成女孩和奶牛玩偶在游乐园开心地坐过山车的图片，涵盖早晨、中午、晚上",
    size="960*540",
    response_format="b64_json",  
) 
for event in imagesResponse:
    if event is None:
        continue
    elif event.type == "image_generation.partial_succeeded":
        if event.b64_json is not None:
            print(f"size={len(event.b64_json)}, base_64={event.b64_json}")
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_image_{timestamp}.png"
                filepath = os.path.join(script_dir, filename)
                image_data = base64.b64decode(event.b64_json)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                print(f"图片已成功保存为: {filepath}")
            except Exception as e:
                print(f"错误：保存图片时出错 - {e}")
    elif event.type == "image_generation.completed":
        if event.usage is not None:
            print("Final completed event:")
            print("recv.Usage:", event.usage)