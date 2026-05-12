import requests
import json

# 配置
API_URL = "http://localhost:8000/v1/chat/completions"
API_KEY = "sk-your-api-key-here"  # 使用 .env 中配置的 API Key

# 请求数据
data = {
    "messages": [
        {"role": "", "content": "今天A股跌幅最大行业板块有哪些？"}
        # {"content": "今天A股涨幅最大的行业板块是？"}
    ],
    "model": "deepseek-v3-search",
    "stream": True  # 启用流式输出
}

# 发送请求
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

print("正在发送请求...\n")
response = requests.post(API_URL, headers=headers, json=data, stream=True)

# 处理 SSE 流式响应
for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        # SSE 格式: data: {...}
        if line_str.startswith('data: '):
            data_str = line_str[6:]  # 去掉 "data: " 前缀
            if data_str == '[DONE]':
                print("\n[完成]")
                break
            try:
                chunk = json.loads(data_str)
                content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                if content:
                    print("\n")
                    print(content, end='', flush=True)
            except json.JSONDecodeError as e:
                print(f"\n解析错误: {e}")
                print(f"原始数据: {data_str}")
