"""会话管理服务模块"""

import asyncio
import logging
import random
from typing import Dict, List

import httpx

CREATE_URL = "https://yuanbao.tencent.com/api/user/agent/conversation/create"
LIST_URL = "https://yuanbao.tencent.com/api/user/agent/conversation/list"
CLEAR_URL = "https://yuanbao.tencent.com/api/user/agent/conversation/v1/clear"

DEFAULT_TIMEOUT = 60

logger = logging.getLogger(__name__)


class ConversationCreationError(Exception):
    """会话创建异常"""

    pass


class ConversationRemoveError(Exception):
    """会话删除异常"""

    pass


async def create_conversation(agent_id: str, headers: Dict[str, str], timeout: int = DEFAULT_TIMEOUT) -> str:
    """创建会话

    Args:
        agent_id: 代理 ID
        headers: 认证请求头
        timeout: 超时时间

    Returns:
        str: 会话 ID

    Raises:
        ConversationCreationError: 会话创建失败时抛出
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(CREATE_URL, json={"agentId": agent_id}, headers=headers, timeout=timeout)

            if response.status_code != 200:
                raise Exception(f"Request failed. Status code: {response.status_code}, Response: {response.text}")

            try:
                json_data = response.json()
            except ValueError:
                raise Exception(f"Failed to parse response as JSON. Response: {response.text}")

            if "id" not in json_data:
                raise Exception(f"Failed to find 'id' in response JSON. Response: {response.text}")

            return json_data["id"]

    except Exception as e:
        raise ConversationCreationError(e)


async def remove_conversation(chat_id: str, headers: Dict[str, str], timeout: int = DEFAULT_TIMEOUT) -> None:
    """删除会话

    Args:
        chat_id: 会话 ID
        headers: 认证请求头
        timeout: 超时时间

    Raises:
        ConversationRemoveError: 会话删除失败时抛出
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CLEAR_URL,
                json={"conversationIds": [chat_id], "uiOptions": {"noToast": True}},
                headers=headers,
                timeout=timeout,
            )

            if response.status_code != 200:
                raise Exception(f"Request failed. Status code: {response.status_code}, Response: {response.text}")

    except Exception as e:
        raise ConversationRemoveError(e)


async def list_conversations(
    agent_id: str, headers: Dict[str, str], offset: int = 0, limit: int = 40, timeout: int = DEFAULT_TIMEOUT
) -> List[Dict]:
    """获取会话列表

    Args:
        agent_id: 代理 ID
        headers: 认证请求头
        offset: 偏移量
        limit: 限制数量
        timeout: 超时时间

    Returns:
        List[Dict]: 会话列表

    Raises:
        Exception: 获取会话列表失败时抛出
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                LIST_URL,
                json={"agentId": agent_id, "offset": offset, "limit": limit, "filterGoodQuestion": True},
                headers=headers,
                timeout=timeout,
            )

            if response.status_code != 200:
                raise Exception(f"Request failed. Status code: {response.status_code}, Response: {response.text}")

            json_data = response.json()
            # 返回会话列表，通常在一个字段中，比如 'list' 或 'conversations'
            return json_data.get("list", json_data.get("conversations", []))

    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise


async def clear_all_conversations(agent_id: str, headers: Dict[str, str], timeout: int = DEFAULT_TIMEOUT) -> Dict:
    """清理所有会话

    Args:
        agent_id: 代理 ID
        headers: 认证请求头
        timeout: 超时时间

    Returns:
        Dict: 包含清理结果的字典 {total: 总数, success: 成功数, failed: 失败数}
    """
    result = {"total": 0, "success": 0, "failed": 0, "failed_ids": []}

    try:
        # 获取所有会话列表
        conversations = await list_conversations(agent_id, headers, offset=0, limit=100, timeout=timeout)
        result["total"] = len(conversations)

        if not conversations:
            logger.info("No conversations to clear")
            return result

        logger.info(f"Found {len(conversations)} conversations to clear")

        # 逐个删除会话，每次调用间隔 3-8 秒
        for idx, conv in enumerate(conversations):
            chat_id = conv.get("id") or conv.get("chatId") or conv.get("conversationId")
            if not chat_id:
                logger.warning(f"Could not find chat ID in conversation: {conv}")
                result["failed"] += 1
                continue

            try:
                await remove_conversation(chat_id, headers, timeout)
                result["success"] += 1
                logger.info(f"Successfully removed conversation: {chat_id}")
                
                # 如果不是最后一个会话，等待 3-8 秒后再删除下一个
                if idx < len(conversations) - 1:
                    delay = random.uniform(3, 8)
                    logger.info(f"Waiting {delay:.2f} seconds before next deletion...")
                    await asyncio.sleep(delay)
            except Exception as e:
                result["failed"] += 1
                result["failed_ids"].append(chat_id)
                logger.error(f"Failed to remove conversation {chat_id}: {e}")
                
                # 即使失败也要等待，避免频繁请求
                if idx < len(conversations) - 1:
                    delay = random.uniform(3, 8)
                    await asyncio.sleep(delay)

        logger.info(f"Clear conversations completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Failed to clear all conversations: {e}")
        raise
