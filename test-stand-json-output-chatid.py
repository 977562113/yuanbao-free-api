from openai import OpenAI
import json
import re
import time

# python test-stand-json-output-chatid.py

# 配置
API_URL = "http://localhost:8000/v1"
API_KEY = "sk-your-api-key-here"  # 使用 .env 中配置的 API Key

# 创建 OpenAI 客户端
client = OpenAI(
    base_url=API_URL,
    api_key=API_KEY
)

print("正在发送请求...\n")

# ========== 耗时统计 ==========
t_start = time.perf_counter()           # 总体开始时间
t_first_chunk = None                    # 首个有效 chunk 到达时间
chunk_count = 0                         # chunk 总数
chunk_times = []                        # 每个 chunk 的时间戳 (perf_counter)
# ==============================

# 发送流式请求
prompt = (
    "用户输入：华夏眼科\n"
    "你是一个专业的A股技术分析与筹码分析助手。用户输入一只股票名称或代码后，请按以下流程分析并仅以 JSON 格式返回结果，不要输出任何额外解释性文字。\n"
    "\n"
    "【返回格式】\n"
    "1.仅限json格式, 不需要其他文字;\n"
    "\n"
    "【分析流程】\n"
    "1. 获取该股票最新交易日（以当前日期为基准）的实时行情数据：最新价、涨跌幅、成交额、换手率、量比。\n"
    "2. 读取近 250 个交易日的日K数据，计算以下技术指标：\n"
    "   - 均线：MA5、MA10、MA20、MA60\n"
    "   - 布林带：BOLL（20, 2）上轨、中轨、下轨\n"
    "   - MACD（12, 26, 9）：DIF、DEA、红绿柱\n"
    "   - KDJ（9, 3, 3）：K、D、J\n"
    "   - RSI（6, 12, 24）\n"
    "   - 筹码分布：平均成本、获利比例、近期筹码峰位置\n"
    "3. 识别近 30 个交易日的显著高低点，结合均线、布林带、前高前低、筹码峰，确定 3-5 个压力位与 3-5 个支撑位。\n"
    "4. 检测背离信号：\n"
    "   - 量价背离：价创新高但量能萎缩（顶背离），或价创新低但量能放大/价跌量缩（底背离）\n"
    "   - MACD背离：价与DIF/柱子的顶底背离，日线优先，辅以60分钟和周线\n"
    "   - KDJ背离：价与J值/RSI的顶底背离\n"
    "5. 盈亏比分析（假设现价买入）：\n"
    "   - 短线止损 stop_loss_short：现价下方最近的\"已站稳支撑\"，优先级 MA5支撑 > MA10支撑 > MA20支撑 > 最近前低 > 布林下轨，取第一个在现价下方的\n"
    "   - 短线止盈 take_profit_short：现价上方最近的\"有效压力\"，优先级 布林上轨 > 前高 > MA5/MA10反压 > 整数关口，取第一个在现价上方的\n"
    "   - 波段止损 stop_loss_swing：现价下方最近且 strength∈[\"中\",\"强\"] 的支撑，优先 MA20支撑/布林中轨/平台低点\n"
    "   - 波段止盈 take_profit_swing：现价上方最近且 strength∈[\"中\",\"强\"] 的压力，优先 前高/上方套牢筹码峰下沿/整数关口\n"
    "   - 短线盈亏比 ratio_short = (take_profit_short - entry) / (entry - stop_loss_short)，保留2位小数\n"
    "   - 波段盈亏比 ratio_swing = (take_profit_swing - entry) / (entry - stop_loss_swing)，保留2位小数\n"
    "   - 多档止盈 ladder：取 pressure_levels 中现价上方前 4 档，逐档计算 profit_pct 和以 stop_loss_short 为分母的 ladder_ratio\n"
    "   - 回踩优化 better_entry：取 support_levels 中离现价次近且 strength≠弱 的价位作为回踩买点，算 entry2=该价、stop=波段止损、tp=波段止盈 的改良盈亏比\n"
    "   - suitable_for_short_term：ratio_short >= 2.0 且 short_term.bias!=\"看空\" → \"适合\"；1.5~2.0 → \"谨慎\"；<1.5 或 bias==\"看空\" → \"不适合\"；若 entry<=stop_loss_short 则 \"不适合(已破位)\"\n"
    "6. 综合量价、趋势、指标背离、盈亏比情况，给出短线（1-5个交易日）和波段（2-8周）操作建议。\n"
    "\n"
    "【压力位类型枚举】\n"
    "- \"布林上轨\"        布林带BOLL(20,2)上轨\n"
    "- \"MA5反压\"         上方未站上的5日均线\n"
    "- \"MA10反压\"        上方未站上的10日均线\n"
    "- \"MA20反压\"        上方未站上的20日均线（月线）\n"
    "- \"MA60反压\"        上方未站上的60日均线（季线）\n"
    "- \"前高\"            近期（30日内）阶段性高点\n"
    "- \"平台高点\"        箱体/整理区间上沿\n"
    "- \"上方套牢筹码峰\"  现价上方筹码密集套牢区\n"
    "- \"整数关口\"        整数价位\n"
    "\n"
    "【支撑位类型枚举】\n"
    "- \"布林下轨\"        布林带下轨\n"
    "- \"布林中轨\"        布林带中轨（多头回踩参考）\n"
    "- \"MA5支撑\"         下方已站上的5日均线\n"
    "- \"MA10支撑\"        下方已站上的10日均线\n"
    "- \"MA20支撑\"        下方已站上的20日均线（月线）\n"
    "- \"MA60支撑\"        下方已站上的60日均线（季线）\n"
    "- \"前低\"            近期（30日内）阶段性低点\n"
    "- \"平台低点\"        箱体/整理区间下沿\n"
    "- \"下方获利筹码峰\"  现价下方筹码密集获利区\n"
    "- \"筹码谷\"          两筹码峰之间的稀疏区下沿\n"
    "- \"整数关口\"        整数价位\n"
    "\n"
    "【强度等级枚举】（strength 字段）\n"
    "- \"强\"    MA60/筹码峰/前高前低/平台高点低点\n"
    "- \"中\"    MA20/布林轨/MA10\n"
    "- \"弱\"    MA5/整数关口/筹码谷\n"
    "\n"
    "【背离类型枚举】（divergence 字段）\n"
    "- \"量价顶背离\"      价升量缩，上涨动能衰竭\n"
    "- \"量价底背离\"      价跌量缩或价新低量放大，下跌动能衰竭\n"
    "- \"MACD顶背离\"      价新高但MACD的DIF/柱子走低\n"
    "- \"MACD底背离\"      价新低但MACD的DIF/柱子走高\n"
    "- \"KDJ顶背离\"       价新高但J值/RSI走低\n"
    "- \"KDJ底背离\"       价新低但J值/RSI走高\n"
    "\n"
    "【背离重要性枚举】（significance 字段）\n"
    "- \"高\"    日线级别 + 多次背离 + 靠近关键压力/支撑位\n"
    "- \"中\"    日线级别单次背离，或60分钟级别多次背离\n"
    "- \"低\"    60分钟/30分钟级别单次背离\n"
    "\n"
    "【背离检测时间框架】（timeframe 字段）\n"
    "- \"日线\"   日K级别（最重要）\n"
    "- \"60分钟\" 60分钟K级别\n"
    "- \"周线\"   周K级别（用于波段确认）\n"
    "\n"
    "【短线操作建议字段】\n"
    "- action: \"买入\" | \"持有\" | \"减仓\" | \"观望\"\n"
    "- bias: \"看多\" | \"中性\" | \"看空\"\n"
    "- key_level: 明日需重点盯防的价位（一个）\n"
    "- buy_point: 建议买入价位（一个数值，若无则填 null）\n"
    "- sell_point: 建议卖出价位（一个数值，若无则填 null）\n"
    "- logic: 一句话操作逻辑（≤40字，若检测到底背离/顶背离须在逻辑中体现）\n"
    "\n"
    "【波段操作建议字段】\n"
    "- action: \"做多\" | \"持仓\" | \"离场\" | \"观望\"\n"
    "- bias: \"看多\" | \"中性\" | \"看空\"\n"
    "- target: 波段目标位（上沿，一个）\n"
    "- stop_loss: 波段止损位（一个）\n"
    "- buy_point: 建议买入价位（一个数值，若无则填 null）\n"
    "- sell_point: 建议卖出价位（一个数值，若无则填 null）\n"
    "- logic: 一句话操作逻辑（≤50字，若检测到底背离/顶背离须在逻辑中体现）\n"
    "\n"
    "【输出 JSON 结构（严格遵循，字段名不可变）】\n"
    "{\n"
    "  \"stock\": {\n"
    "    \"name\": \"股票名称\",\n"
    "    \"code\": \"股票代码\",\n"
    "    \"price\": 现价(数字),\n"
    "    \"change_pct\": 涨跌幅(数字, 带正负),\n"
    "    \"updated_at\": \"数据日期 YYYY-MM-DD\"\n"
    "  },\n"
    "  \"pressure_levels\": [\n"
    "    { \"price\": 价位1, \"type\": [\"类型1\"], \"strength\": \"强度\" },\n"
    "    { \"price\": 价位2, \"type\": [\"类型1\", \"类型2\"], \"strength\": \"强度\" }\n"
    "  ],\n"
    "  \"support_levels\": [\n"
    "    { \"price\": 价位A, \"type\": [\"类型A\"], \"strength\": \"强度\" },\n"
    "    { \"price\": 价位B, \"type\": [\"类型B\"], \"strength\": \"强度\" }\n"
    "  ],\n"
    "  \"divergence\": [\n"
    "    {\n"
    "      \"type\": \"背离类型\",\n"
    "      \"direction\": \"顶背离/底背离\",\n"
    "      \"timeframe\": \"日线/60分钟/周线\",\n"
    "      \"description\": \"一句话描述（含具体价/量/指标数值）\",\n"
    "      \"significance\": \"高/中/低\"\n"
    "    }\n"
    "  ],\n"
    "  \"risk_reward\": {\n"
    "    \"entry_price\": 现价,\n"
    "    \"short_term\": {\n"
    "      \"stop_loss\": 短线止损价,\n"
    "      \"take_profit\": 短线止盈价,\n"
    "      \"profit_amount\": 止盈空间(保留2位),\n"
    "      \"loss_amount\": 止损空间(保留2位),\n"
    "      \"ratio\": 短线盈亏比值(保留2位),\n"
    "      \"ratio_text\": \"1 : 2.52\",\n"
    "      \"breakeven_win_rate\": 保本所需胜率(%, 保留1位, =1/(1+ratio)*100),\n"
    "      \"suitable\": \"适合/谨慎/不适合\"\n"
    "    },\n"
    "    \"swing\": {\n"
    "      \"stop_loss\": 波段止损价,\n"
    "      \"take_profit\": 波段止盈价,\n"
    "      \"profit_amount\": 保留2位,\n"
    "      \"loss_amount\": 保留2位,\n"
    "      \"ratio\": 保留2位,\n"
    "      \"ratio_text\": \"1 : 2.17\",\n"
    "      \"breakeven_win_rate\": 保留1位,\n"
    "      \"suitable\": \"适合/谨慎/不适合\"\n"
    "    },\n"
    "    \"take_profit_ladder\": [\n"
    "      { \"price\": 止盈价, \"logic\": \"布林上轨/前高/...\", \"profit_pct\": 2.00, \"ladder_ratio\": 2.52, \"ladder_ratio_text\": \"1 : 2.52\" }\n"
    "    ],\n"
    "    \"better_entry\": {\n"
    "      \"entry_price\": 回踩买点价,\n"
    "      \"stop_loss\": 波段止损价,\n"
    "      \"take_profit\": 波段止盈价,\n"
    "      \"risk_pct\": 回踩买入后止损幅度%,\n"
    "      \"reward_pct\": 回踩买入后止盈幅度%,\n"
    "      \"ratio\": 改良盈亏比数值,\n"
    "      \"ratio_text\": \"1 : 3.56\"\n"
    "    },\n"
    "    \"conclusion\": \"一句话结论（是否现价可买/等回踩/放弃）\"\n"
    "  },\n"
    "  \"short_term\": {\n"
    "    \"action\": \"买入/持有/减仓/观望\",\n"
    "    \"bias\": \"看多/中性/看空\",\n"
    "    \"key_level\": 关键价位,\n"
    "    \"buy_point\": 建议买入价位,\n"
    "    \"sell_point\": 建议卖出价位,\n"
    "    \"logic\": \"一句话逻辑\"\n"
    "  },\n"
    "  \"swing\": {\n"
    "    \"action\": \"做多/持仓/离场/观望\",\n"
    "    \"bias\": \"看多/中性/看空\",\n"
    "    \"target\": 目标位,\n"
    "    \"stop_loss\": 止损位,\n"
    "    \"buy_point\": 建议买入价位,\n"
    "    \"sell_point\": 建议卖出价位,\n"
    "    \"logic\": \"一句话逻辑\"\n"
    "  }\n"
    "}\n"
    "\n"
    "【硬性约束】\n"
    "1. 仅输出合法 JSON，禁止使用 Markdown 代码块包裹，禁止任何非 JSON 文本。\n"
    "2. 所有价位保留 2 位小数，涨跌幅保留 2 位小数，ratio 保留 2 位小数，pct 保留 2 位小数，breakeven_win_rate 保留 1 位小数。\n"
    "3. 若数据获取失败，返回 {\"error\": \"原因描述\"}，仍保持 JSON。\n"
    "4. 压力位按 price 升序排列，支撑位按 price 降序排列，take_profit_ladder 按 price 升序排列。\n"
    "5. 若无背离信号，divergence 返回空数组 []，不得省略该字段。\n"
    "6. risk_reward 中若现价已跌破最近支撑，short_term.stop_loss 填该支撑价位，short_term.suitable 填 \"不适合(已破位)\"。\n"
    "7. 不提供任何投资建议外的主观评论，不预测具体涨幅点数。\n"
    "\n"
)

prompt = (
    "中国海油"
)

stream = client.chat.completions.create(
    model="deepseek-v3-search",
    messages=[{"role": "股票压力支撑分析专家", "content": prompt}],
    stream=True
)

# 拼接完整文本
full_text = ""
max_cmpid = 0

for chunk in stream:
    # 检查是否有 choices
    if not chunk.choices:
        continue

    # 记录首个 chunk 到达时间 (TTFB)
    if t_first_chunk is None:
        t_first_chunk = time.perf_counter()

    chunk_count += 1
    chunk_times.append(time.perf_counter())

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

            print(f"\n handling ... ")

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
                        # print(f" text  → {msg}")
                        full_text += msg

                elif msg_type == "deepSearchAgent":
                    contents_obj = json_obj.get("contents", [])
                    # 遍历 contents 数组，提取 text 类型的内容
                    if contents_obj:
                        for item in contents_obj:
                            if isinstance(item, dict) and item.get("type") == "text":
                                cmpid = int(item.get("cmpid", '0'))
                                if cmpid > max_cmpid:
                                    max_cmpid = cmpid
                                    full_text = ''

                                msg = item.get("text", "")
                                if msg:
                                    # print(f" deepSearchAgent  → {item}")
                                    full_text += msg

                elif msg_type == "agentCapabilities":
                    continue
                elif msg_type == "mark":
                    mark_obj = json_obj.get("mark", {})
                    if isinstance(mark_obj, dict):
                        msg = mark_obj.get("content", "")
                        if msg:
                            # print(f" mark  → {msg}")
                            full_text += msg
                else:

                    if msg_type == "meta" or msg_type == "heartbeat" or msg_type == "hint_v2_tip" or msg_type == "searchGuid" or msg_type == "step":
                        continue

                    # 其他类型的消息也记录下来，避免遗漏
                    print(f"⚠️ 未处理的消息类型: {msg_type}")
                    print(f"⚠️ 未处理的消息类型 json_obj : {json_obj}")


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

t_post_start = time.perf_counter()

# 将 [](@mark_underline=数字) 转换为普通引用标注 [数字]
full_text = re.sub(r'\[\]\(@mark_underline=(\d+)\)', r'[\1]', full_text)
# 清理引用标签
full_text = re.sub(r'\[citation:\d+\]', '', full_text)
full_text = re.sub(r'\[(\d+)\]', '', full_text)

t_post_end = time.perf_counter()
t_total = time.perf_counter()

# ========== 耗时统计报告 ==========
print("\n" + "=" * 50)
print("⏱️  耗时统计报告")
print("=" * 50)

# TTFB (Time To First Byte)
if t_first_chunk is not None:
    ttfb = t_first_chunk - t_start
    print(f"  首字节耗时 (TTFB):      {ttfb*1000:>8.2f} ms")

# 流式接收阶段
if t_first_chunk is not None:
    t_stream_end = chunk_times[-1] if chunk_times else t_first_chunk
    stream_duration = t_stream_end - t_first_chunk
    print(f"  流式接收耗时:            {stream_duration*1000:>8.2f} ms")

# chunk 间隔统计
if len(chunk_times) >= 2:
    intervals = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
    avg_interval = sum(intervals) / len(intervals)
    max_interval = max(intervals)
    min_interval = min(intervals)
    print(f"  Chunk 数量:              {chunk_count:>8}")
    print(f"  Chunk 平均间隔:          {avg_interval*1000:>8.2f} ms")
    print(f"  Chunk 最大间隔:          {max_interval*1000:>8.2f} ms")
    print(f"  Chunk 最小间隔:          {min_interval*1000:>8.2f} ms")

# API 总耗时 (从请求到最后一个 chunk)
if t_first_chunk is not None:
    api_total = t_stream_end - t_start
    print(f"  API 请求总耗时:          {api_total*1000:>8.2f} ms")

# 后处理耗时
post_duration = t_post_end - t_post_start
print(f"  后处理耗时:              {post_duration*1000:>8.2f} ms")

# 全程总计
total_duration = t_total - t_start
print(f"  ─────────────────────────────────")
print(f"  全程总计:                {total_duration*1000:>8.2f} ms ({total_duration:.2f} s)")

print("=" * 50)

print(full_text)
print("="*50)
print(f"\n总字符数: {len(full_text)}")
