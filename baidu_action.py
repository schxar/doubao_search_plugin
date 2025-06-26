import traceback
from typing import Dict, Any, Tuple
from baidusearch.baidusearch import search

from src.chat.focus_chat.planners.actions.plugin_action import PluginAction, register_action
from src.common.logger_manager import get_logger

logger = get_logger("baidu_action")

@register_action
class BaiduSearchAction(PluginAction):
    """执行百度搜索的动作处理类"""

    action_name = "baidu_search"
    action_description = "使用百度进行搜索"
    action_parameters = {
        "query": "需要搜索的关键词或句子",
        "num_results": "获取的搜索结果数量，默认为4"
    }
    default = True
    associated_types = ["text"]

    async def process(self) -> Tuple[bool, str]:
        """处理搜索请求并返回结果"""
        try:
            query = self.action_data.get("query", "")
            if not query:
                return False, "未提供搜索查询"
                
            num_results = int(self.action_data.get("num_results", 4))
            
            # 添加搜索状态提示
            await self.send_message_by_expressor(f"🔍 正在使用百度搜索关于'{query}'的信息...")
            
            results = self._baidu_search(query, num_results)
            if not results["success"]:
                await self.send_message_by_expressor(f"抱歉，搜索'{query}'时遇到问题: {results['results']}")
                return False, f"搜索失败: {results['results']}"
            
            # 改进结果格式化
            if not results["results"]:
                formatted_results = f"没有找到关于【{query}】的相关结果"
            else:
                formatted_results = f"🔍 关于【{query}】的百度搜索结果({len(results['results'])}条):\n\n"
                formatted_results += self._format_results(results["results"])
                formatted_results += "\n(来自百度搜索)"
                
            await self.send_message_by_expressor(formatted_results)
            return True, f"成功搜索到 {len(results['results'])} 条结果"
            
        except Exception as e:
            logger.error(f"{self.log_prefix} 搜索过程出错: {traceback.format_exc()}")
            return False, f"搜索处理出错: {str(e)}"

    def _baidu_search(self, query: str, num_results: int) -> Dict[str, Any]:
        """执行百度搜索"""
        try:
            results = search(query, num_results=num_results)
            
            formatted_results = []
            for item in results:
                formatted_results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', '#'),
                    'snippet': item.get('abstract', '')
                })
            
            return {
                "success": True,
                "results": formatted_results
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} 百度搜索出错: {traceback.format_exc()}")
            return {
                "success": False,
                "results": str(e)
            }

    def _format_results(self, results: list) -> str:
        """格式化搜索结果"""
        formatted = []
        for idx, item in enumerate(results, 1):
            formatted.append(
                f"{idx}. [{item['title']}]({item['url']})\n"
                f"{item['snippet']}\n"
            )
        return "\n".join(formatted)
