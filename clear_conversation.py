import requests
import json

# 配置
API_URL = "http://localhost:8000"
API_KEY = "sk-your-api-key-here"

def test_clear_conversations():
    """测试清理所有会话接口"""
    url = f"{API_URL}/v1/conversations/clear"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("正在调用清理会话接口...")
    print(f"URL: {url}")
    print("-" * 50)
    
    try:
        response = requests.post(url, headers=headers)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print("-" * 50)
        
        if response.status_code == 200:
            result = response.json()
            print("清理结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("-" * 50)
            print(f"✅ 成功清理 {result.get('success', 0)} 个会话")
            print(f"❌ 失败 {result.get('failed', 0)} 个会话")
            if result.get('failed_ids'):
                print(f"失败的会话ID: {result['failed_ids']}")
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 发生错误: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_clear_conversations()
