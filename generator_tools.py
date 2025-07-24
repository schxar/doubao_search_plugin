from src.plugin_system.base.base_plugin import BasePlugin
from src.plugin_system.apis.plugin_register_api import register_plugin
from src.plugin_system.base.base_action import BaseAction, ActionActivationType, ChatMode
from src.plugin_system.base.base_command import BaseCommand
from src.plugin_system.base.component_types import ComponentInfo
from src.plugin_system.base.config_types import ConfigField
from src.plugin_system.apis import generator_api
from src.plugin_system.apis import database_api
from src.plugin_system.apis import config_api
from src.common.database.database_model import Messages, PersonInfo
from src.person_info.person_info import get_person_info_manager
from src.common.logger import get_logger
from PIL import Image
from typing import Tuple, Dict, Optional, List, Any, Type
from pathlib import Path
import traceback
import tomlkit
import json
import random
import asyncio
import aiohttp
import base64
import toml
import io
import os
import re
from typing import Any, Tuple

async def generate_rewrite_reply(chat_stream: Any, raw_reply: str, reason: str) -> Tuple[bool, Any]:
    """
    调用 generator_api.rewrite_reply 生成回复，供插件统一调用。
    :param chat_stream: 聊天流对象
    :param raw_reply: 原始回复文本
    :param reason: 生成回复的理由
    :return: (状态, 消息)
    """
    return await generator_api.rewrite_reply(
        chat_stream=chat_stream,
        reply_data={
            "raw_reply": raw_reply,
            "reason": reason,
        }
    )
