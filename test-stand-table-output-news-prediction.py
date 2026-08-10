from openai import OpenAI
import json
import re

# python test-stand-table-output.py

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


"你是一个股票市场的事件驱动分析专家，能根据新闻分析出利好利空，以及把新闻的影响力大小划分成不同的重要等级，抽取重要性前10的新闻，分析出它们对应的利空利好行业/概念！"
"要求与步骤:"
"1.获取今天日期, 上个交易日收盘日期时间, 上个交易日行业涨幅前十行业和跌幅前十行业(步骤5时要用来结合分析,有些时候开盘某些行业大涨,收盘后1-2小时内又出相关行业利好(有可能是忽悠散户接盘))"
"2.拉取指定API的数据（热点经济新闻列表）: https://newsapi.eastmoney.com/kuaixun/v1/getlist_101_ajaxResult_100_1_.html"
"3.对步骤2获取新闻列表进行时间范围过滤，只保留上个交易日收盘后(15:00)到今日早盘(9:30)分前的最新新闻(对当日走势有最大影响力！)"
"4.分析步骤3过滤后的符合时间范围的热点新闻(不得胡乱捏造假新闻)，分析出重要事件（影响力大，重要性高）所带来的利空利好，推理出A股今天的行业风口/危机在那几个行业概念！(注意对应行业在是否已经price in, 是则过滤掉它)"
"5.推荐你当天推理出来的风口/行业/概念对应的潜力优质个股（最好是央企，国企，地方政府持股，社保持股的个股/相应的行业etf）！"
"6.只返回 JSON 对象，严格按照示例格式返回JSON(注意{},{},{},{}是示例省略字符,要返回具体内容对象), 不要其他内容(否则干扰 JSON 解析)"
"7.JSON示例: [{\"sort\":1,\"time\":\"2026-08-03 06:45:30\",\"title\":\"国常会决定核准辽宁庄河一期等四个核电项目，共8台机组，总投资超1700亿元\",\"type\":\"利好\",\"target\":\"核电ETF/中国核建(601611)\"},{},{},{},{},{\"sort\":1,\"time\":\"2026-08-03 16:14:35\",\"title\":\"韩股触发熔断，三星电子与SK海力士跌近9%，拖累A股半导体，兆易创新跌停，科创50跌5.08%\",\"type\":\"利空\",\"target\":\"半导体ETF(512480)/兆易创新(603986)\"},{},{},{},{}]"

prompt = (
    "1.要求：根据用户提供股票列表，分析是否央国企，是否社保持仓股"
    "2.股票列表：大众交通, 锦江在线, 海汽集团, 上海机场, 海南机场, 白云机场, 中国国航, 南方航空, 中国东航, 宁波港"
    "3.输出：以 JSON 对象格式返回，键为股票代码，值为包含分析结果的字典（包含名称字段）"
    "4.示例：[{\"名称\":\"浦发银行\",\"央国企\":\"是\",\"社保持仓\":\"否\"}]"
    "5.只返回 JSON 对象，严格按照示例格式返回JSON，不要其他内容(否则干扰 JSON 解析)"
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
# 清理引用标签
full_text = re.sub(r'\[citation:\d+\]', '', full_text)
full_text = re.sub(r'\[(\d+)\]', '', full_text)

print(full_text)
print("="*50)
print(f"\n总字符数: {len(full_text)}")
