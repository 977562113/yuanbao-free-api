"""YuanBao API Proxy 启动脚本"""

import asyncio
import sys

# 在 Windows 上设置 SelectorEventLoop 以支持 Playwright
# 必须在导入任何其他模块之前设置
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    # 暂时禁用 reload 以测试事件循环策略是否生效
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
