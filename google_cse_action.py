import requests
import traceback
from typing import Dict, Any, Tuple
from pathlib import Path

from src.chat.focus_chat.planners.actions.plugin_action import PluginAction, register_action
from src.common.logger_manager import get_logger

logger = get_logger("google_cse_action")

@register_action
class GoogleCSESearchAction(PluginAction):
    """执行Google CSE搜索的动作处理类"""

    action_name = "google_cse_search"
    action_description = "使用Google CSE进行搜索"
    action_parameters = {
        "query": "需要搜索的关键词或句子",
        "num_results": "获取的搜索结果数量，默认为4",
        "language": "搜索结果的语言，例如zh-CN、en-US，默认为zh-CN"
    }
    default = True
    associated_types = ["text"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        # 读取Google CSE配置
        plugin_root = Path(__file__).parent.parent
        api_key_path = plugin_root / 'config' / 'api_key.txt'
        engine_id_path = plugin_root / 'config' / 'engine_id.txt'
        
        with open(api_key_path, 'r') as f:
            self.api_key = f.read().strip()
        with open(engine_id_path, 'r') as f:
            self.engine_id = f.read().strip()

    async def process(self) -> Tuple[bool, str]:
        """处理搜索请求并返回结果"""
        try:
            query = self.action_data.get("query", "")
            if not query:
                return False, "未提供搜索查询"
                
            num_results = int(self.action_data.get("num_results", 4))
            language = self.action_data.get("language", "zh-CN")
            
            # 添加搜索状态提示
            await self.send_message_by_expressor(f"🔍 正在使用Google搜索关于'{query}'的信息...")
            
            results = self._perform_search(query, num_results, language)
            if not results["success"]:
                await self.send_message_by_expressor(f"抱歉，搜索'{query}'时遇到问题: {results['results']}")
                return False, f"搜索失败: {results['results']}"
            
            # 改进结果格式化
            if not results["results"]:
                formatted_results = f"没有找到关于【{query}】的相关结果"
            else:
                formatted_results = f"🔍 关于【{query}】的Google搜索结果({len(results['results'])}条):\n\n"
                formatted_results += self._format_results(results["results"])
                formatted_results += "\n(来自Google搜索)"
                
            await self.send_message_by_expressor(formatted_results)
            return True, f"成功搜索到 {len(results['results'])} 条结果"
            
        except Exception as e:
            logger.error(f"{self.log_prefix} 搜索过程出错: {traceback.format_exc()}")
            return False, f"搜索处理出错: {str(e)}"

    def _perform_search(self, query: str, num_results: int, language: str) -> Dict[str, Any]:
        """执行实际的搜索"""
        try:
            params = {
                'key': self.api_key,
                'cx': self.engine_id,
                'q': query,
                'num': num_results,
                'hl': language
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items']:
                    results.append({
                        'title': item.get('title', 'No title'),
                        'url': item.get('link', '#'),
                        'snippet': item.get('snippet', '')
                    })
            
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} 搜索错误: {str(e)}")
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
