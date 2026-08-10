from openai import OpenAI
import json
import re
import time
import random

# python test-stand-table-output.py

# 配置
API_URL = "http://localhost:8000/v1"
API_KEY = "sk-your-api-key-here"  # 使用 .env 中配置的 API Key

# 创建 OpenAI 客户端
client = OpenAI(
    base_url=API_URL,
    api_key=API_KEY
)

for NUMBER in range(1297, 1351):
    print(f"\n{'='*50}")
    print(f"正在处理第 {NUMBER} 章...")
    print(f"{'='*50}")

    # 发送流式请求
    prompt = (
        f"https://ixdzs.tw/read/66080/p{NUMBER}.html,概括总结剧情（不需要解说）, 简体文字"
    )

    stream = client.chat.completions.create(
        model="deepseek-v3-search",
        messages=[{"role": "", "content": prompt}],
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
                    print(f"原始内容: {content}...")
                    full_text += content
                except Exception as e:
                    # 其他异常也打印出来，但不丢失数据
                    print(f"\n其他错误: {type(e).__name__}: {e}")
                    # 发生错误时，尝试将原始内容加入
                    full_text += content

    # 将 [](@mark_underline=数字) 转换为普通引用标注 [数字]
    full_text = re.sub(r'\[\]\(@mark_underline=(\d+)\)', r'[\1]', full_text)
    # 清理引用标签
    full_text = re.sub(r'\[citation:\d+\]', '', full_text)
    full_text = re.sub(r'\[(\d+)\]', '', full_text)

    # 根据中文标点符号换行（！。？；等）
    full_text = re.sub(r'([！。？；])', r'\1\n', full_text)
    # 清理多余空行
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    full_text = full_text.strip()

    # 保存到文件
    output_file = f"{NUMBER}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"\n✅ 已保存到 {output_file}")
    print(f"总字符数: {len(full_text)}")

    # 随机睡眠 20-40 秒
    sleep_time = random.randint(20, 40)
    print(f"\n⏳ 等待 {sleep_time} 秒后继续...")
    time.sleep(sleep_time)

print("\n\n🎉 所有章节处理完成！")
