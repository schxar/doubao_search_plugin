"""
豆包图片生成插件

基于火山引擎豆包模型的AI图片生成插件。

功能特性：
- 智能LLM判定：根据聊天内容智能判断是否需要生成图片
- 高质量图片生成：使用豆包Seed Dream模型生成图片
- 结果缓存：避免重复生成相同内容的图片
- 配置验证：自动验证和修复配置文件
- 参数验证：完整的输入参数验证和错误处理
- 多尺寸支持：支持多种图片尺寸生成

包含组件：
- 图片生成Action - 根据描述使用火山引擎API生成图片
"""

import asyncio
import json
import urllib.request
import urllib.error
import base64
import traceback
import os
from typing import List, Tuple, Type, Optional

# 导入新插件系统
from src.plugin_system.base.base_plugin import BasePlugin
from src.plugin_system.base.base_plugin import register_plugin
from src.plugin_system.base.base_action import BaseAction
from src.plugin_system.base.component_types import ComponentInfo, ActionActivationType, ChatMode
from src.plugin_system.base.config_types import ConfigField
from src.common.logger import get_logger
from openai import OpenAI

from .PixivRank50 import get_pixiv_image_by_rank
from .pixiv_image_action import get_random_pixiv_image
from .moehu_image_action import get_moehu_image
from .generator_tools import generate_rewrite_reply

logger = get_logger("doubao_search_plugin")


# ===== Action组件 =====


class DoubaoSearchGenerationAction(BaseAction):
    """豆包搜索生成Action - 根据描述使用OpenAI标准参数系统生成智能回复"""

    # 激活设置
    focus_activation_type = ActionActivationType.LLM_JUDGE  # Focus模式使用LLM判定，精确理解需求
    normal_activation_type = ActionActivationType.KEYWORD  # Normal模式使用关键词激活，快速响应
    mode_enable = ChatMode.ALL
    parallel_action = True

    # 动作基本信息
    action_name = "doubao_llm_search"
    action_description = (
        "可以根据用户输入，通过火山引擎豆包的搜索LLM生成智能回复或结果。"
    )

    # 关键词设置（用于Normal模式）
    activation_keywords = ["搜索", "问答", "智能回复", "查询", "search", "answer"]
    keyword_case_sensitive = False

    # LLM判定提示词（用于Focus模式）
    llm_judge_prompt = """
判定是否需要使用LLM搜索动作的条件：
1. 用户明确要求搜索、查询或获取智能回复
2. 用户提出了需要回答的问题或需要进一步解释的内容
3. 对话中提到需要智能化的回答或信息生成

适合使用的情况：
- "搜索..."、"查询..."、"回答..."
- "能帮我找到...吗"
- "解释一下..."
- "生成一个关于...的回复"

绝对不要使用的情况：
1. 用户明确表示不需要搜索或智能回复
2. 用户仅进行闲聊或无具体问题
3. 用户要求执行其他非搜索相关的功能
"""

    # 动作参数定义
    action_parameters = {
        "query": "用户查询内容，输入需要搜索或回答的问题，必填",
    }

    # 动作使用场景
    action_require = [
        "当用户提出问题或需要智能化回答时使用",
        "当用户要求查询或搜索具体信息时使用",
        "当用户需要基于上下文的多轮对话支持时使用",
    ]

    # 关联类型
    associated_types = ["image", "text"]

    # 简单的请求缓存，避免短时间内重复请求
    _request_cache = {}
    _cache_max_size = 10

    # 初始化OpenAI客户端
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        api_key = self.get_config("api.volcano_generate_api_key")
        model_name = self.get_config("api.model_name")
        if not isinstance(api_key, str):
            raise ValueError("API key must be a string")
        if not isinstance(model_name, str):
            raise ValueError("Model name must be a string")

        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3/bots",
            api_key=api_key
        )

    async def execute(self) -> Tuple[bool, Optional[str]]:
        """执行LLM请求动作"""
        logger.info(f"{self.log_prefix} 执行豆包LLM请求动作")

        # 参数验证
        query = self.action_data.get("query")
        if not query or not query.strip():
            logger.warning(f"{self.log_prefix} 查询内容为空，无法生成回复。")
            await self.send_text("你需要告诉我想要查询什么内容哦~ 比如说'常见的十字花科植物有哪些？'")
            return False, "查询内容为空"

        query = query.strip()

        try:
            # 调用OpenAI客户端
            completion = self.client.chat.completions.create(
                model=self.get_config("api.model_name"),  # 从配置中读取模型名称
                messages=[
                    {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"},
                    {"role": "user", "content": query},
                ],
            )

            # 获取回复内容
            response_content = completion.choices[0].message.content or ""
            # 使用 generator_tools 工具生成回复
            result_status, result_message = await generate_rewrite_reply(
                chat_stream=self.chat_stream,
                raw_reply=response_content,
                reason="豆包LLM生成的智能回复，请优化表达后发送给用户"
            )
            if result_status:
                for reply_seg in result_message:
                    data = reply_seg[1]
                    await self.send_text(data)
                    await asyncio.sleep(1.0)
            else:
                await self.send_text(response_content)

            # 发送一张Pixiv排行榜随机图片
            try:
                
                img_datauri = get_pixiv_image_by_rank(None)
                # 只取datauri的base64部分
                if img_datauri.startswith("data:image/"):
                    base64_image = img_datauri.split(",", 1)[-1]
                else:
                    base64_image = img_datauri
                await self.send_image(base64_image)
            except Exception as e:
                logger.warning(f"Pixiv排行榜图片发送失败: {e}")

            return True, response_content

        except Exception as e:
            logger.error(f"{self.log_prefix} 调用OpenAI API时出错: {e}", exc_info=True)
            await self.send_text(f"哎呀，生成回复时遇到问题：{str(e)[:100]}")
            return False, f"生成回复失败: {str(e)[:100]}"

    @classmethod
    def _get_cache_key(cls, description: str, model: str, size: str) -> str:
        """生成缓存键"""
        return f"{description[:100]}|{model}|{size}"

    @classmethod
    def _cleanup_cache(cls):
        """清理缓存，保持大小在限制内"""
        if len(cls._request_cache) > cls._cache_max_size:
            keys_to_remove = list(cls._request_cache.keys())[: -cls._cache_max_size // 2]
            for key in keys_to_remove:
                del cls._request_cache[key]


class PixivMoehuAction(BaseAction):
    """Moehu图片API Action - 获取二次元/三次元/角色/游戏/动漫/表情包图片"""

    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD
    mode_enable = ChatMode.ALL
    parallel_action = True

    action_name = "moehu_image"
    action_description = "从moehu.org API获取并发送一张图片（支持多类型）"
    action_parameters = {
        "type": "图片类型(2d:二次元, 3d:三次元, vtuber:虚拟主播, character:角色系列, game:游戏系列, anime:动漫系列, emoji:表情包, 默认2d)"
    }
    action_require = [
        "需要发送普通图片的场景",
        "当他人让你发送一张图片时",
        "当他人需要非R18图片时"
    ]
    associated_types = ["image"]

    async def execute(self) -> tuple:
        image_type = self.action_data.get("type")
        try:
            from .moehu_image_action import get_moehu_image
            datauri = get_moehu_image(image_type)
            # 只取datauri的base64部分
            if datauri.startswith("data:image/"):
                base64_image = datauri.split(",", 1)[-1]
            else:
                base64_image = datauri
            await self.send_image(base64_image)
            return True, f"已发送图片(type={image_type or '2d'})"
        except Exception as e:
            logger.warning(f"Moehu图片发送失败: {e}")
            await self.send_text("图片获取失败，请稍后再试。")
            return False, f"图片获取失败: {e}"


class PixivRandomImageAction(BaseAction):
    """Pixiv随机图片API Action - 获取Pixiv随机图片"""

    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD
    mode_enable = ChatMode.ALL
    parallel_action = True

    action_name = "pixiv_random_image"
    action_description = "从网络API获取并发送一张随机P站图（Pixiv API）"
    action_parameters = {
        "content_rating": "内容分级（0为全年龄，1为限制级，2为混合）",
        "keyword": "可选，按关键词搜索图片,不允许空格,只允许一个词",
        "tag": "可选，按标签搜索图片，多个标签用|分隔,如果没有要求,只用一个词,多tag无法获取到图片"
    }
    action_require = [
        "需要发送P站图的场景",
        "当他人让你发送一张P站图时"
    ]
    associated_types = ["image"]

    async def execute(self) -> tuple:
        content_rating = self.action_data.get("content_rating", 0)
        keyword = self.action_data.get("keyword")
        tag = self.action_data.get("tag")
        try:
            from .pixiv_image_action import get_random_pixiv_image
            datauri = get_random_pixiv_image(content_rating, keyword, tag)
            # 只取datauri的base64部分
            if datauri.startswith("data:image/"):
                base64_image = datauri.split(",", 1)[-1]
            else:
                base64_image = datauri
            await self.send_image(base64_image)
            return True, f"已发送Pixiv图片"
        except Exception as e:
            logger.warning(f"Pixiv图片发送失败: {e}")
            await self.send_text("Pixiv图片获取失败，请稍后再试。")
            return False, f"Pixiv图片获取失败: {e}"


class PixivRank50Action(BaseAction):
    """Pixiv排行榜图片API Action - 获取指定排名的Pixiv图片"""

    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD
    mode_enable = ChatMode.ALL
    parallel_action = True

    action_name = "pixiv_rank50_image"
    action_description = "获取Pixiv排行榜指定排名的图片（1-50，默认随机）"
    action_parameters = {
        "rank": "图片排名（1-50，留空为随机）"
    }
    action_require = [
        "需要发送Pixiv排行榜图片的场景",
        "当他人让你发送一张排行榜图片时"
    ]
    associated_types = ["image"]

    async def execute(self) -> tuple:
        rank = self.action_data.get("rank")
        try:
            from .PixivRank50 import get_pixiv_image_by_rank
            # rank参数处理
            if rank is not None:
                try:
                    rank = int(rank)
                except Exception:
                    rank = None
            datauri = get_pixiv_image_by_rank(rank)
            # 只取datauri的base64部分
            if datauri.startswith("data:image/"):
                base64_image = datauri.split(",", 1)[-1]
            else:
                base64_image = datauri
            await self.send_image(base64_image)
            return True, f"已发送Pixiv排行榜图片(rank={rank or '随机'})"
        except Exception as e:
            logger.warning(f"Pixiv排行榜图片发送失败: {e}")
            await self.send_text("Pixiv排行榜图片获取失败，请稍后再试。")
            return False, f"Pixiv排行榜图片获取失败: {e}"


# ===== 插件主类 =====


@register_plugin
class DoubaoSearchPlugin(BasePlugin):
    """豆包搜索插件

    基于火山引擎豆包模型的AI搜索插件：
    - 搜索Action：根据描述使用火山引擎API生成搜索结果
    """

    # 插件基本信息
    plugin_name = "doubao_search_plugin"  # 内部标识符
    enable_plugin = True
    config_file_name = "config.toml"

    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本信息配置",
        "api": "API相关配置，包含火山引擎API的访问信息",
        "cache": "结果缓存配置",
        "components": "组件启用配置",
    }

    # 配置Schema定义
    config_schema = {
        "plugin": {
            "name": ConfigField(type=str, default="doubao_search_plugin", description="插件名称", required=True),
            "version": ConfigField(type=str, default="1.0.0", description="插件版本号"),
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
            "description": ConfigField(
                type=str, default="基于火山引擎豆包模型的AI搜索插件", description="插件描述", required=True
            ),
        },
        "api": {
            "base_url": ConfigField(
                type=str,
                default="https://ark.cn-beijing.volces.com/api/v3",
                description="API基础URL",
                example="https://api.example.com/v1",
            ),
            "volcano_generate_api_key": ConfigField(
                type=str, default="YOUR_DOUBAO_API_KEY_HERE", description="火山引擎豆包API密钥", required=True
            ),
            "model_name": ConfigField(
                type=str, default="YOUR_DOUBAO_MODEL_NAME_HERE", description="使用的模型名称", required=True
            ),
        },
        "cache": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用请求缓存"),
            "max_size": ConfigField(type=int, default=10, description="最大缓存数量"),
        },
        "components": {
            "enable_search_action": ConfigField(type=bool, default=True, description="是否启用搜索Action")
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""

        # 从配置获取组件启用状态
        enable_search_action = self.get_config("components.enable_search_action", True)

        components = []

        # 添加搜索Action
        if enable_search_action:
            components.append((DoubaoSearchGenerationAction.get_action_info(), DoubaoSearchGenerationAction))

        # 注册Pixiv和moehu相关Action
        components.append((PixivMoehuAction.get_action_info(), PixivMoehuAction))
        components.append((PixivRandomImageAction.get_action_info(), PixivRandomImageAction))
        components.append((PixivRank50Action.get_action_info(), PixivRank50Action))

        return components
