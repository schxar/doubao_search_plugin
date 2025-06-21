from src.plugin_system.apis import generator_api
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
