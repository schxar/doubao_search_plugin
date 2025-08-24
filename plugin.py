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
import toml

# 导入新插件系统
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
from src.person_info.person_info import get_person_id_by_person_name
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
from openai import OpenAI



logger = get_logger("doubao_search_plugin")


# 读取代理配置并设置环境变量
try:
    config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.toml')
    proxy_url = None
    use_proxy = False
    if os.path.exists(config_path):
        config = toml.load(config_path)
        proxy_cfg = config.get('proxy', {})
        use_proxy = proxy_cfg.get('use_proxy', False)
        proxy_url = proxy_cfg.get('proxy_url', '')
    if use_proxy and proxy_url:
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
except Exception as e:
    print(f"代理配置读取失败: {e}")


# ===== Action组件 =====


class DoubaoSearchGenerationAction(BaseAction):
    """豆包搜索生成Action - 根据描述使用OpenAI标准参数系统生成智能回复"""

    # 激活设置
    focus_activation_type = ActionActivationType.ALWAYS  # Focus模式使用LLM判定，精确理解需求
    normal_activation_type = ActionActivationType.ALWAYS  # Normal模式使用关键词激活，快速响应
    mode_enable = ChatMode.ALL
    parallel_action = False

    # 动作基本信息
    action_name = "doubao_llm_search"
    action_description = (
        "可以根据用户输入，通过火山引擎豆包的搜索LLM生成智能回复或结果。支持查询天气、知识问答等。"
    )

    # 关键词设置（用于Normal模式）
    activation_keywords = ["搜索", "问答", "智能回复", "查询", "search", "answer"]
    keyword_case_sensitive = False

    # LLM判定提示词（用于Focus模式）
    llm_judge_prompt = """
判定是否需要使用LLM搜索动作的条件：
1. 用户明确要求搜索、查询、获取智能回复或查询天气
2. 用户提出了需要回答的问题、需要进一步解释的内容，或需要获取天气信息
3. 对话中提到需要智能化的回答、信息生成或天气查询

适合使用的情况：
- "搜索..."、"查询..."、"回答..."、"今天天气怎么样"、"帮我查下北京天气"
- "能帮我找到...吗"
- "解释一下..."
- "生成一个关于...的回复"
- "请告诉我明天上海的天气"

绝对不要使用的情况：
1. 用户明确表示不需要搜索、智能回复或天气查询
2. 用户仅进行闲聊或无具体问题
3. 用户要求执行其他非搜索/天气相关的功能
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
        "当用户需要获取天气信息时使用",
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

            # 统一使用 generator_api.rewrite_reply
            status, rewrite_result, error_message = await generator_api.rewrite_reply(
                chat_stream=self.chat_stream,
                reply_data={
                    "raw_reply": response_content,
                    "reason": "豆包LLM生成的智能回复，请优化表达后发送给用户"
                },
                enable_splitter=False,
                enable_chinese_typo=False
            )
            if status:
                for reply_seg in rewrite_result:
                    data = reply_seg[1]
                    await self.send_text(data)
                    await asyncio.sleep(1.0)
            else:
                error_msg = error_message if error_message else "回复生成失败"
                await self.send_text(error_msg)

            # 根据配置决定是否发送Pixiv排行榜图片
            enable_pixiv_rank50_on_search = self.get_config("components.enable_pixiv_rank50_on_search", False)
            if enable_pixiv_rank50_on_search:
                try:
                    from .PixivRank50 import get_pixiv_image_by_rank
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
    parallel_action = False

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
            try:
                from .moehu_image_action import get_moehu_image
            except ImportError as e:
                logger.warning(f"moehu_image_action模块导入失败: {e}")
                await self.send_text("Moehu图片功能未安装或缺失，请联系管理员补全依赖。")
                return False, "moehu_image_action模块导入失败"
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
    parallel_action = False

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
        import random
        content_rating = self.action_data.get("content_rating", 0)
        keyword = self.action_data.get("keyword")
        tag = self.action_data.get("tag")
        try:
            from .pixiv_image_action import get_random_pixiv_image
        except ImportError as e:
            logger.warning(f"pixiv_image_action模块导入失败: {e}")
            await self.send_text("Pixiv图片功能未安装或缺失，请联系管理员补全依赖。")
            return False, "pixiv_image_action模块导入失败"
        max_attempts = 3
        last_exception = None
        for attempt in range(max_attempts):
            try:
                # 第一次用原始参数，后两次随机参数
                if attempt == 0:
                    cr = content_rating
                    kw = keyword
                    tg = tag
                else:
                    cr = random.choice([0, 1, 2])
                    kw = None
                    tg = None
                datauri = get_random_pixiv_image(cr, kw, tg)
                # 只取datauri的base64部分
                if datauri.startswith("data:image/"):
                    base64_image = datauri.split(",", 1)[-1]
                else:
                    base64_image = datauri
                await self.send_image(base64_image)
                return True, f"已发送Pixiv图片"
            except Exception as e:
                last_exception = e
                logger.warning(f"Pixiv图片发送失败(第{attempt+1}次): {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(3)
        await self.send_text("Pixiv图片获取失败，请稍后再试。")
        return False, f"Pixiv图片获取失败: {last_exception}"


class PixivRank50Action(BaseAction):
    """Pixiv排行榜图片API Action - 获取指定排名的Pixiv图片"""

    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD
    mode_enable = ChatMode.ALL
    parallel_action = False

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
            try:
                from .PixivRank50 import get_pixiv_image_by_rank
            except ImportError as e:
                logger.warning(f"PixivRank50模块导入失败: {e}")
                await self.send_text("Pixiv排行榜图片功能未安装或缺失，请联系管理员补全依赖。")
                return False, "PixivRank50模块导入失败"
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


class BingSearchAction(BaseAction):
    """必应搜索并润色结果Action"""
    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD
    mode_enable = ChatMode.ALL
    parallel_action = False

    action_name = "bing_search"
    action_description = "通过必应搜索并用LLM润色结果后返回（不适用于天气查询）"
    activation_keywords = ["bing", "必应", "bing搜索"]
    keyword_case_sensitive = False
    llm_judge_prompt = """
判定是否需要使用必应搜索动作的条件：
1. 用户明确要求网络搜索、bing搜索、网页查询等（不包括天气查询）
2. 用户提出了需要查找互联网最新信息的问题，但不是天气相关内容

绝对不要用于天气查询。
"""
    action_parameters = {
        "query": "用户查询内容，输入需要搜索的问题，必填",
    }
    action_require = [
        "当用户需要网络搜索时使用",
        "当用户需要获取互联网最新信息时使用",
    ]
    associated_types = ["text"]

    async def execute(self) -> tuple:
        query = self.action_data.get("query")
        # 统一使用 generator_api.rewrite_reply
        if not query or not query.strip():
            fail_msg = "你需要告诉我想要搜索什么内容哦~ 例如：'bing搜索2025年高考时间'"
            status, rewrite_result, error_message = await generator_api.rewrite_reply(
                chat_stream=self.chat_stream,
                reply_data={
                    "raw_reply": fail_msg,
                    "reason": "请用自然语言友好地提醒用户输入搜索内容，并举例。"
                },
                enable_splitter=False,
                enable_chinese_typo=False
            )
            if status and rewrite_result:
                for reply_seg in rewrite_result:
                    data = reply_seg[1]
                    await self.send_text(data)
                    await asyncio.sleep(1.0)
            else:
                error_msg = error_message if error_message else fail_msg
                await self.send_text(error_msg)
            return False, "查询内容为空"
        query = query.strip()
        try:
            from .bing_search_tool import search_bing
            results = search_bing(query, num_results=5)
            if not results:
                fail_msg = f"没有搜索到与“{query}”相关的内容。"
                result_status, result_message = await generator_api.rewrite_reply(
                    chat_stream=self.chat_stream,
                    reply_data={
                        "raw_reply": fail_msg,
                        "reason": "请用自然语言简要解释无搜索结果的可能原因，并安慰用户。"
                    },
                    enable_splitter=False,
                    enable_chinese_typo=False
                )
                if result_status:
                    for reply_seg in result_message:
                        data = reply_seg[1]
                        await self.send_text(data)
                        await asyncio.sleep(1.0)
                else:
                    await self.send_text(fail_msg)
                return False, "无搜索结果"
            # 简单拼接搜索摘要
            summary = "\n".join([
                f"[{item['rank']}] {item['title']}\n{item['abstract']}\n链接: {item['url']}" for item in results
            ])
            # 只用 generator_tools 润色，不用LLM再润色
            result_status, result_message = await generator_api.rewrite_reply(
                chat_stream=self.chat_stream,
                reply_data={
                    "raw_reply": summary,
                    "reason": "总结搜索结果，选择高相关性结果回复，请务必在回复中包含至少一个原始搜索结果中的网页链接，且内容要准确、简洁、友好。"
                },
                enable_splitter=False,
                enable_chinese_typo=False
            )
            if result_status:
                for reply_seg in result_message:
                    data = reply_seg[1]
                    await self.send_text(data)
                    await asyncio.sleep(1.0)
            else:
                await self.send_text(summary)
            return True, summary
        except Exception as e:
            logger.error(f"Bing搜索Action出错: {e}", exc_info=True)
            fail_msg = f"未能搜索到“{query}”的相关内容，或发生错误：{str(e)[:100]}。请简要解释可能的原因并安慰用户。"
            result_status, result_message = await generator_api.rewrite_reply(
                chat_stream=self.chat_stream,
                reply_data={
                    "raw_reply": fail_msg,
                    "reason": "请用自然语言简要解释搜索失败的可能原因，并安慰用户。"
                },
                enable_splitter=False,
                enable_chinese_typo=False
            )
            if result_status:
                for reply_seg in result_message:
                    data = reply_seg[1]
                    await self.send_text(data)
                    await asyncio.sleep(1.0)
            else:
                await self.send_text(fail_msg)
            return False, fail_msg


class DuckDuckGoSearchAction(BaseAction):
    """DuckDuckGo 搜索 Action"""
    focus_activation_type = ActionActivationType.LLM_JUDGE
    normal_activation_type = ActionActivationType.KEYWORD
    mode_enable = ChatMode.ALL
    parallel_action = False

    action_name = "duckduckgo_search"
    action_description = "通过 DuckDuckGo 搜索并返回结果摘要"
    activation_keywords = ["duckduckgo", "ddg", "网页搜索", "网络搜索", "duckduckgo搜索"]
    keyword_case_sensitive = False
    llm_judge_prompt = """
判定是否需要使用 DuckDuckGo 搜索动作的条件：
1. 用户明确要求 DuckDuckGo、ddg、网页查询等
2. 用户提出了需要查找互联网信息的问题
"""
    action_parameters = {
        "query": "用户查询内容，输入需要搜索的问题，必填",
    }
    action_require = [
        "当用户需要 DuckDuckGo 网络搜索时使用",
        "当用户需要获取互联网信息时使用",
    ]
    associated_types = ["text"]

    async def execute(self) -> tuple:
        query = self.action_data.get("query")
        # 统一使用 generator_api.rewrite_reply
        try:
            from .duckduckgo_tool import duckduckgo_search
        except ImportError as e:
            logger.warning(f"duckduckgo_tool模块导入失败: {e}")
            await self.send_text("DuckDuckGo搜索功能未安装或缺失，请联系管理员补全依赖。")
            return False, "duckduckgo_tool模块导入失败"
        if not query or not query.strip():
            fail_msg = "你需要告诉我想要搜索什么内容哦~ 例如：'duckduckgo搜索2025年高考时间'"
            status, rewrite_result, error_message = await generator_api.rewrite_reply(
                chat_stream=self.chat_stream,
                reply_data={
                    "raw_reply": fail_msg,
                    "reason": "请用自然语言友好地提醒用户输入DuckDuckGo搜索内容，并举例。"
                },
                enable_splitter=False,
                enable_chinese_typo=False
            )
            if status and rewrite_result:
                for reply_seg in rewrite_result:
                    data = reply_seg[1]
                    await self.send_text(data)
                    await asyncio.sleep(1.0)
            else:
                error_msg = error_message if error_message else fail_msg
                await self.send_text(error_msg)
            return False, "查询内容为空"
        query = query.strip()
        try:
            results = duckduckgo_search(query)
            if not results.get("success") or not results.get("results"):
                fail_msg = f"没有搜索到与“{query}”相关的内容。请简要解释可能的原因并安慰用户。"
                result_status, result_message = await generator_api.rewrite_reply(
                    chat_stream=self.chat_stream,
                    reply_data={
                        "raw_reply": fail_msg,
                        "reason": "请用自然语言简要解释DuckDuckGo搜索无结果的可能原因，并安慰用户。"
                    },
                    enable_splitter=False,
                    enable_chinese_typo=False
                )
                if result_status:
                    for reply_seg in result_message:
                        data = reply_seg[1]
                        await self.send_text(data)
                        await asyncio.sleep(1.0)
                else:
                    await self.send_text(fail_msg)
                return False, "无搜索结果"
            summary = "\n".join([
                f"[{i+1}] {item['title']}\n{item['snippet']}\n链接: {item['url']}" for i, item in enumerate(results["results"])
            ])
            # 使用generate_rewrite_reply润色后再发送
            status, rewrite_result, error_message = await generator_api.rewrite_reply(
                chat_stream=self.chat_stream,
                reply_data={
                    "raw_reply": summary,
                    "reason": "总结DuckDuckGo搜索结果，选择高相关性结果回复，请务必在回复中包含至少一个原始搜索结果中的网页链接，且内容要准确、简洁、友好。"
                },
                enable_splitter=False,
                enable_chinese_typo=False
            )
            if status and rewrite_result:
                for reply_seg in rewrite_result:
                    data = reply_seg[1]
                    await self.send_text(data)
                    await asyncio.sleep(1.0)
            else:
                error_msg = error_message if error_message else summary
                await self.send_text(error_msg)
            return True, summary
        except Exception as e:
            logger.error(f"DuckDuckGo搜索Action出错: {e}", exc_info=True)
            fail_msg = f"DuckDuckGo搜索失败：{str(e)[:100]}。请简要解释可能的原因并安慰用户。"
            status, rewrite_result, error_message = await generator_api.rewrite_reply(
                chat_stream=self.chat_stream,
                reply_data={
                    "raw_reply": fail_msg,
                    "reason": "请用自然语言简要解释DuckDuckGo搜索失败的可能原因，并安慰用户。"
                },
                enable_splitter=False,
                enable_chinese_typo=False
            )
            if status and rewrite_result:
                for reply_seg in rewrite_result:
                    data = reply_seg[1]
                    await self.send_text(data)
                    await asyncio.sleep(1.0)
            else:
                error_msg = error_message if error_message else fail_msg
                await self.send_text(error_msg)
            return False, fail_msg


# ===== 插件主类 =====


@register_plugin

class DoubaoSearchPlugin(BasePlugin):
    dependencies = []  # type: ignore
    python_dependencies = ["openai", "requests", "pillow", "toml", "tomlkit", "aiohttp", "selenium>=4.0.0", "webdriver-manager>=3.0.0", "beautifulsoup4>=4.0.0"]  # type: ignore
    """豆包搜索插件

    基于火山引擎豆包模型的AI搜索插件：
    - 搜索Action：根据描述使用火山引擎API生成搜索结果
    """

    # 插件基本信息
    plugin_name = "doubao_search_plugin"  # type: ignore  # 内部标识符
    enable_plugin = True  # type: ignore
    config_file_name = "config.toml"  # type: ignore

    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本信息配置",
        "api": "API相关配置，包含火山引擎API的访问信息",
        "cache": "结果缓存配置",
        "components": "组件启用配置",
        "proxy": "HTTP/HTTPS 代理配置",
    }

    # 配置Schema定义
    config_schema = {  # type: ignore
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
            "enable_search_action": ConfigField(type=bool, default=True, description="是否启用搜索Action"),
            "enable_bing_action": ConfigField(type=bool, default=True, description="是否启用Bing搜索Action"),
            "enable_duckduckgo_action": ConfigField(type=bool, default=True, description="是否启用DuckDuckGo搜索Action"),
            "enable_pixiv_moehu_action": ConfigField(type=bool, default=True, description="是否启用Moehu图片Action"),
            "enable_pixiv_random_action": ConfigField(type=bool, default=True, description="是否启用Pixiv随机图片Action"),
            "enable_pixiv_rank50_action": ConfigField(type=bool, default=True, description="是否启用Pixiv排行榜图片Action"),
            "enable_pixiv_rank50_on_search": ConfigField(type=bool, default=False, description="搜索后是否自动发送Pixiv排行榜随机图片"),
        },
        "proxy": {
            "use_proxy": ConfigField(type=bool, default=False, description="是否启用HTTP/HTTPS代理"),
            "proxy_url": ConfigField(type=str, default="http://127.0.0.1:7897", description="HTTP/HTTPS代理地址"),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""

        # 从配置获取组件启用状态
        enable_search_action = self.get_config("components.enable_search_action", True)
        enable_bing_action = self.get_config("components.enable_bing_action", True)
        enable_duckduckgo_action = self.get_config("components.enable_duckduckgo_action", True)
        enable_pixiv_moehu_action = self.get_config("components.enable_pixiv_moehu_action", True)
        enable_pixiv_random_action = self.get_config("components.enable_pixiv_random_action", True)
        enable_pixiv_rank50_action = self.get_config("components.enable_pixiv_rank50_action", True)

        components = []

        # 添加搜索Action
        if enable_search_action:
            components.append((DoubaoSearchGenerationAction.get_action_info(), DoubaoSearchGenerationAction))
        if enable_bing_action:
            components.append((BingSearchAction.get_action_info(), BingSearchAction))
        if enable_duckduckgo_action:
            components.append((DuckDuckGoSearchAction.get_action_info(), DuckDuckGoSearchAction))
        if enable_pixiv_moehu_action:
            components.append((PixivMoehuAction.get_action_info(), PixivMoehuAction))
        if enable_pixiv_random_action:
            components.append((PixivRandomImageAction.get_action_info(), PixivRandomImageAction))
        if enable_pixiv_rank50_action:
            components.append((PixivRank50Action.get_action_info(), PixivRank50Action))

        return components
