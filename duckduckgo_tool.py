import traceback
from typing import Dict, Any, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import json
from datetime import datetime, timedelta
import hashlib

from src.common.logger import get_logger

logger = get_logger("duckduckgo_tool")

# 自定义用户数据目录
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "chrome_profile_duckduckgo")
# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "cache", "duckduckgo")
os.makedirs(CACHE_DIR, exist_ok=True)

def _get_cache_path(query: str) -> str:
    """获取查询结果的缓存路径"""
    query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{query_hash}.json")

def _is_cache_valid(cache_path: str) -> bool:
    """检查缓存是否有效（12小时内）"""
    if not os.path.exists(cache_path):
        return False
        
    cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
    return datetime.now() - cache_time < timedelta(hours=12)

def duckduckgo_search(query: str) -> Dict[str, Any]:
    """使用Selenium执行DuckDuckGo搜索"""
    try:
        cache_path = _get_cache_path(query)
        
        # 检查缓存
        if os.path.exists(cache_path) and _is_cache_valid(cache_path):
            logger.info(f"Using cached results for query: {query}")
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 配置Chrome选项 - 启用headless并模拟普通用户
        chrome_options = Options()
        chrome_options.add_argument(f"user-data-dir={USER_DATA_DIR}")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # 初始化WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # 执行搜索 - 使用显式等待
            driver.get(f"https://duckduckgo.com/?t=h_&q={query}")
            
            # 智能等待搜索结果 - 检查多个可能的选择器
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            selectors = [
                "article[data-testid='result']",
                ".result",
                ".web-result",
                "[data-testid='result-extras-url']"
            ]
            
            for selector in selectors:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"使用选择器 '{selector}' 找到搜索结果")
                    break
                except:
                    continue
            else:
                logger.warning("未能检测到标准搜索结果元素")
            
            # 保存页面HTML用于调试
            debug_html_path = os.path.join(CACHE_DIR, "debug_last_page.html")
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            
            # 解析结果
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 调试：打印页面关键元素
            logger.info("页面标题: %s", driver.title)
            logger.info("页面源代码长度: %d 字符", len(driver.page_source))
            logger.info("搜索结果容器数量: %d", len(soup.find_all('article')))
            results = []
            
            # 提取有机搜索结果 - 使用多种选择器组合
            search_containers = set()
            for selector in [
                "article[data-testid='result']", 
                ".result",
                ".web-result",
                ".result__body",
                "[data-testid='result']",
                "li[data-layout='organic']"
            ]:
                search_containers.update(soup.select(selector))
            
            for container in search_containers:
                try:
                    # 提取标题
                    title_elem = container.find(attrs={"data-testid": "result-title-a"}) or \
                                container.find(['h2', 'h3', 'h4', 'h5', 'h6'])
                    
                    # 提取链接 - 使用rel="noopener"作为主要标识
                    link_elem = container.find('a', {
                        'href': True,
                        'rel': 'noopener',
                        'target': '_blank'
                    }) or container.find('a', href=True)
                    
                    # 提取来源信息
                    source_elem = container.find(class_="fOCEb2mA3YZTJXXjpgdS")
                    source = source_elem.text.strip() if source_elem else ""
                    
                    # 提取snippet
                    snippet_elem = container.find(attrs={"data-testid": "result-extras-snippet"}) or \
                                  container.find(class_=lambda x: x and 'snippet' in x.lower()) or \
                                  container.find(attrs={"data-result": "snippet"})
                    
                    # 提取完整URL
                    url_elem = container.find(class_="veU5I0hFkgFGOPhX2RBE")
                    full_url = url_elem.text.strip() if url_elem else ""
                    
                    if title_elem and link_elem:
                        results.append({
                            'type': 'organic',
                            'title': title_elem.text.strip(),
                            'url': link_elem['href'],
                            'source': source,
                            'full_url': full_url,
                            'snippet': snippet_elem.text.strip() if snippet_elem else ""
                        })
                        logger.info(f"找到结果: {title_elem.text.strip()} (来源: {source})")
                except Exception as e:
                    logger.warning(f"解析结果时出错: {str(e)}")
                    continue
            
            # 保存结果
            result_data = {
                "success": True,
                "results": results[:4],
                "debug_info": {
                    "page_title": driver.title,
                    "result_count": len(results),
                    "html_saved_to": debug_html_path
                }
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f)
                
            logger.info(f"成功获取 {len(results)} 条结果")
            return result_data
            
        except Exception as e:
            logger.error(f"搜索过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            try:
                if driver:
                    driver.quit()
                    logger.info("浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {str(e)}")
            
    except Exception as e:
        logger.error(f"DuckDuckGo搜索出错: {traceback.format_exc()}")
        return {
            "success": False,
            "results": f"搜索过程中出错: {str(e)}"
        }
