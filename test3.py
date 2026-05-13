from openai import OpenAI
import json
import re

# 配置
API_URL = "http://localhost:8000/v1"
API_KEY = "sk-your-api-key-here"  # 使用 .env 中配置的 API Key

# 创建 OpenAI 客户端
client = OpenAI(
    base_url=API_URL,
    api_key=API_KEY
)

print("正在发送请求...\n")

# 发送流式请求
stream = client.chat.completions.create(
    model="deepseek-v3-search",
    messages=[
        {"role": "", "content": "盐田港为啥不涨？" }
    ],
    stream=True
)

# 拼接完整文本
full_text = ""

for chunk in stream:
    # 检查是否有 choices
    if not chunk.choices:
        continue
    
    # 遍历所有 choices，避免数据丢失
    for choice_index, choice in enumerate(chunk.choices):
        delta = choice.delta
        # print(f"\nchunk: {chunk}")
        # print(f"\nchoice[{choice_index}]: {choice}")
        # print(f"\ndelta: {delta}")
        content = delta.content if delta.content else ""
        finish_reason = choice.finish_reason
        
        # 打印结束原因（如果有）
        if finish_reason:
            print(f"\n流式响应结束，原因: {finish_reason}")
        
        if content:
            # 尝试解析 JSON 格式的 content
            try:
                # 将 content 解析为 JSON 对象
                json_obj = json.loads(content)
                msg_type = json_obj.get("type", "")

                # print(f"完整 JSON 对象: {json.dumps(json_obj, ensure_ascii=False, indent=2)}")
                # print("\n-----------------------------------------------------------------")
                
                # 处理不同类型的消息
                if msg_type == "text":
                    msg = json_obj.get("msg", "")
                    # 过滤掉以 '[](@replace' 开头的内容
                    if msg and not msg.startswith("[](@replace"):
                        full_text += msg
                elif msg_type == "mark":
                    mark_obj = json_obj.get("mark", {})
                    if isinstance(mark_obj, dict):
                        msg = mark_obj.get("content", "")
                        if msg:
                            full_text += msg
                else:
                    # 其他类型的消息也记录下来，避免遗漏
                    print(f"⚠️ 未处理的消息类型: {msg_type}")
                    # 尝试提取可能的文本内容
                    for key in ["content", "text", "data", "message"]:
                        if key in json_obj:
                            value = json_obj[key]
                            if isinstance(value, str):
                                full_text += value
                                print(f"   → 从 '{key}' 字段提取内容")
                            break

            except json.JSONDecodeError as e:
                # 如果不是有效的 JSON，可能是纯文本，直接拼接
                print(f"\n非 JSON 内容，作为纯文本处理")
                print(f"原始内容: {content[:200]}...")
                full_text += content
            except Exception as e:
                # 其他异常也打印出来，但不丢失数据
                print(f"\n其他错误: {type(e).__name__}: {e}")
                # 发生错误时，尝试将原始内容加入
                full_text += content

print("\n\n" + "="*50)
print("完整文本内容：")
print("="*50)

# 将 [](@mark_underline=数字) 转换为普通引用标注 [数字]
full_text = re.sub(r'\[\]\(@mark_underline=(\d+)\)', r'[\1]', full_text)

print(full_text)
print("="*50)
print(f"\n总字符数: {len(full_text)}")
