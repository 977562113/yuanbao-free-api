"""角色与 chat_id 的文件缓存模块

通过 role 自动关联 chat_id，同一 role 复用同一个会话。
数据持久化到 ./roleChatIdMappings.json 文件中。
"""

import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 映射文件路径（相对于项目根目录）
MAPPINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "roleChatIdMappings.json")


def _load_mappings() -> Dict[str, str]:
    """从文件加载映射"""
    if not os.path.exists(MAPPINGS_FILE):
        return {}
    try:
        with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load role chat mappings: {e}")
        return {}


def _save_mappings(mappings: Dict[str, str]) -> None:
    """保存映射到文件"""
    try:
        with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(mappings, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Failed to save role chat mappings: {e}")


def get_chat_id_by_role(role: str) -> Optional[str]:
    """根据 role 获取缓存的 chat_id

    Args:
        role: 角色名称

    Returns:
        Optional[str]: 缓存的 chat_id，不存在则返回 None
    """
    mappings = _load_mappings()
    return mappings.get(role)


def set_chat_id_for_role(role: str, chat_id: str) -> None:
    """为 role 缓存 chat_id

    Args:
        role: 角色名称
        chat_id: 会话 ID
    """
    mappings = _load_mappings()
    mappings[role] = chat_id
    _save_mappings(mappings)
    logger.info(f"Cached chat_id for role '{role}': {chat_id}")


def clear_role_cache(role: Optional[str] = None) -> None:
    """清理角色缓存

    Args:
        role: 指定角色名称，不传则清理全部（删除映射文件）
    """
    if role:
        mappings = _load_mappings()
        if role in mappings:
            del mappings[role]
            _save_mappings(mappings)
            logger.info(f"Cleared cache for role: {role}")
    else:
        if os.path.exists(MAPPINGS_FILE):
            os.remove(MAPPINGS_FILE)
            logger.info(f"Deleted mappings file: {MAPPINGS_FILE}")
