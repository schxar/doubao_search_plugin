from src.tools.tool_can_use.base_tool import BaseTool, register_tool
from src.common.logger import get_logger
from typing import Dict, Any
from bs4 import BeautifulSoup
import requests
import random
import os
import traceback

logger = get_logger("search_bing")

ABSTRACT_MAX_LENGTH = 300    # abstract max length

user_agents = [
    # Edge浏览器
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    
    # Chrome浏览器
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    
    # Firefox浏览器
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    
    # Safari浏览器
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    
    # 移动端浏览器
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
    
    # 搜索引擎爬虫 (模拟)
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)',
    'Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)'
]

# 请求头信息
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "www.bing.com",
    "Referer": "https://www.bing.com/",
    "Sec-Ch-Ua": "\"Chromium\";v=\"122\", \"Microsoft Edge\";v=\"122\", \"Not-A.Brand\";v=\"99\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "\"Windows\"",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
}

# 替代的中国区必应请求头
CN_BING_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "cn.bing.com",
    "Referer": "https://cn.bing.com/",
    "Sec-Ch-Ua": "\"Chromium\";v=\"122\", \"Microsoft Edge\";v=\"122\", \"Not-A.Brand\";v=\"99\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "\"Windows\"",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
}

bing_host_url = "https://www.bing.com"
bing_search_url = "https://www.bing.com/search?q="
cn_bing_host_url = "https://cn.bing.com"
cn_bing_search_url = "https://cn.bing.com/search?q="


class BingSearch:
    session = requests.Session()
    session.headers = HEADERS

    def search(self, keyword, num_results=10):
        """
        通过关键字进行搜索
        :param keyword: 关键字
        :param num_results： 指定返回的结果个数
        :return: 结果列表
        """
        if not keyword:
            return None

        list_result = []
        page = 1

        # 起始搜索的url
        next_url = bing_search_url + keyword

        # 循环遍历每一页的搜索结果，并返回下一页的url
        while len(list_result) < num_results:
            data, next_url = self.parse_html(next_url, rank_start=len(list_result))
            if data:
                list_result += data
                logger.debug("---searching[{}], finish parsing page {}, results number={}: ".format(keyword, page, len(data)))
                for d in data:
                    logger.debug(str(d))

            if not next_url:
                logger.debug(u"already search the last page。")
                break
            page += 1

        logger.debug("\n---search [{}] finished. total results number={}！".format(keyword, len(list_result)))
        return list_result[: num_results] if len(list_result) > num_results else list_result


    def parse_html(self, url, rank_start=0, debug=0):
        """
        解析处理结果
        :param url: 需要抓取的 url
        :return:  结果列表，下一页的url
        """
        try:
            logger.debug("--search_bing-------url: {}".format(url))
            
            # 确定是国际版还是中国版必应
            is_cn_bing = "cn.bing.com" in url
            
            # 保存当前URL以便调试
            query_part = url.split("?q=")[1] if "?q=" in url else "unknown_query"
            debug_filename = f"debug/bing_{'cn' if is_cn_bing else 'www'}_search_{query_part[:30]}.html"
            
            # 设置必要的Cookie
            cookies = {
                "SRCHHPGUSR": "SRCHLANG=zh-Hans",  # 设置默认搜索语言为中文
                "SRCHD": "AF=NOFORM",
                "SRCHUID": "V=2&GUID=1A4D4F1C8844493F9A2E3DB0D1BC806C",
                "_SS": "SID=0D89D9A3C95C60B62E7AC80CC85461B3",
                "_EDGE_S": "ui=zh-cn",  # 设置界面语言为中文
                "_EDGE_V": "1"
            }
            
            # 使用适当的请求头
            # 为每次请求随机选择不同的用户代理，降低被屏蔽风险
            headers = CN_BING_HEADERS.copy() if is_cn_bing else HEADERS.copy()
            headers["User-Agent"] = random.choice(user_agents)
            
            # 为不同域名使用不同的Session，避免Cookie污染
            session = requests.Session()
            session.headers.update(headers)
            session.cookies.update(cookies)
            
            # 添加超时和重试，降低超时时间并允许重试
            try:
                res = session.get(url=url, timeout=(3.05, 6), 
                              verify=True, allow_redirects=True)  # 超时分别为连接超时和读取超时
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # 如果第一次尝试超时，使用更宽松的设置再试一次
                logger.warning(f"第一次请求超时，正在重试: {str(e)}")
                try:
                    # 第二次尝试使用更长的超时时间
                    res = session.get(url=url, timeout=(5, 10), 
                                  verify=False)  # 忽略SSL验证
                except Exception as e2:
                    logger.error(f"第二次请求也失败: {str(e2)}")
                    # 如果所有尝试都失败，返回空结果
                    return [], None
            
            res.encoding = "utf-8"
            
            # 保存响应内容以便调试
            os.makedirs("debug", exist_ok=True)
            with open(debug_filename, "w", encoding="utf-8") as f:
                f.write(res.text)
                
            # 检查响应状态
            logger.debug(f"--search_bing-------status_code: {res.status_code}")
            if res.status_code == 403:
                logger.error(f"被禁止访问 (403 Forbidden)，可能是IP被限制")
                # 如果被禁止，返回空结果
                return [], None
                
            if res.status_code != 200:
                logger.error(f"必应搜索请求失败，状态码: {res.status_code}")
                return None, None
            
            # 检查是否被重定向到登录页面或验证页面
            if "login.live.com" in res.url or "login.microsoftonline.com" in res.url:
                logger.error("被重定向到登录页面，可能需要登录")
                return None, None
                
            if "https://www.bing.com/ck/a" in res.url:
                logger.error("被重定向到验证页面，可能被识别为机器人")
                return None, None
                
            # 解析HTML - 添加对多种解析器的支持
            try:
                # 首先尝试使用lxml解析器
                root = BeautifulSoup(res.text, "lxml")
            except Exception as e:
                logger.warning(f"lxml解析器不可用: {str(e)}，尝试使用html.parser")
                try:
                    # 如果lxml不可用，使用内置解析器
                    root = BeautifulSoup(res.text, "html.parser")
                except Exception as e2:
                    logger.error(f"HTML解析失败: {str(e2)}")
                    return None, None
                    
            # 保存解析结果的一小部分用于调试
            sample_html = str(root)[:1000] if root else ""
            logger.debug(f"HTML解析结果示例: {sample_html}")

            list_data = []
            
            # 确保我们能获取到内容 - 先尝试直接提取链接
            all_links = root.find_all("a")
            
            # 记录链接总数，帮助诊断
            logger.debug(f"页面中总共找到了 {len(all_links)} 个链接")
            
            # 保存一些链接示例到日志
            sample_links = []
            for i, link in enumerate(all_links):
                if i < 10:  # 只记录前10个链接
                    sample_links.append({
                        "text": link.text.strip(),
                        "href": link.get("href", "")
                    })
            logger.debug(f"链接示例: {sample_links}")
            
            # 尝试多种选择器查找搜索结果
            search_results = []

            # 方法0：查找动态提取的结果
            # 尝试查找包含完整结果项的父容器
            result_containers = []
            # 一些可能的结果容器选择器
            container_selectors = [
                "ol#b_results", "div.b_searchResults", "div#b_content", 
                "div.srchrslt_main", "div.mspg_cont", "div.ms-srchResult-results",
                "div#ContentAll", "div.resultlist"
            ]

            for selector in container_selectors:
                containers = root.select(selector)
                if containers:
                    logger.debug(f"找到可能的结果容器: {selector}, 数量: {len(containers)}")
                    result_containers.extend(containers)

            # 如果找到容器，尝试在容器中寻找有价值的链接
            extracted_items = []
            if result_containers:
                for container in result_containers:
                    # 查找标题元素（h1, h2, h3, h4）
                    for heading in container.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
                        # 如果标题元素包含链接，这很可能是搜索结果的标题
                        link = heading.find("a")
                        if link and link.get("href") and link.text.strip():
                            url = link.get("href")
                            title = link.text.strip()
                            
                            # 如果是有效的外部链接
                            if (not url.startswith("javascript:") and 
                                not url.startswith("#") and
                                not any(x in url for x in ["bing.com/search", "bing.com/images"])):
                                
                                # 查找摘要：尝试找到相邻的段落元素
                                abstract = ""
                                # 尝试在标题后面查找摘要
                                next_elem = heading.next_sibling
                                while next_elem and not abstract:
                                    if hasattr(next_elem, 'name') and next_elem.name in ['p', 'div', 'span']:
                                        abstract = next_elem.text.strip()
                                        break
                                    next_elem = next_elem.next_sibling
                                
                                # 如果没找到，尝试在父元素内查找其他段落
                                if not abstract:
                                    parent = heading.parent
                                    for p in parent.find_all(['p', 'div'], class_=lambda c: c and any(x in str(c) for x in ["desc", "abstract", "snippet", "caption", "summary"])):
                                        if p != heading:
                                            abstract = p.text.strip()
                                            break
                                
                                # 创建结果项
                                extracted_items.append({
                                    "title": title,
                                    "url": url,
                                    "abstract": abstract,
                                })
                                logger.debug(f"提取到搜索结果: {title}")

            # 如果找到了结果，添加到列表
            if extracted_items:
                for rank, item in enumerate(extracted_items, start=rank_start+1):
                    # 裁剪摘要长度
                    abstract = item["abstract"]
                    if ABSTRACT_MAX_LENGTH and len(abstract) > ABSTRACT_MAX_LENGTH:
                        abstract = abstract[:ABSTRACT_MAX_LENGTH]
                        
                    list_data.append({
                        "title": item["title"],
                        "abstract": abstract,
                        "url": item["url"],
                        "rank": rank
                    })
                logger.debug(f"从容器中提取了 {len(list_data)} 个搜索结果")
                if list_data:
                    return list_data, None
            
            # 如果上面的方法没有找到结果，尝试通用链接提取
            valid_links = []
            for link in all_links:
                href = link.get("href", "")
                text = link.text.strip()
                
                # 有效的搜索结果链接通常有这些特点
                if (href and text and 
                    len(text) > 10 and  # 标题通常比较长
                    not href.startswith("javascript:") and 
                    not href.startswith("#") and
                    not any(x in href for x in [
                        "bing.com/search", "bing.com/images", "bing.com/videos",
                        "bing.com/maps", "bing.com/news", "login", "account", 
                        "javascript", "about.html", "help.html", "microsoft"
                    ]) and
                    "http" in href):  # 必须是有效URL
                    valid_links.append(link)
            
            # 按文本长度排序，更长的文本更可能是搜索结果标题
            valid_links.sort(key=lambda x: len(x.text.strip()), reverse=True)

            if valid_links:
                logger.debug(f"找到 {len(valid_links)} 个可能的搜索结果链接")
                
                # 提取前10个作为搜索结果
                for rank, link in enumerate(valid_links[:10], start=rank_start+1):
                    href = link.get("href", "")
                    text = link.text.strip()
                    
                    # 获取摘要
                    abstract = ""
                    # 尝试获取父元素的文本作为摘要
                    parent = link.parent
                    if parent and parent.text:
                        full_text = parent.text.strip()
                        if len(full_text) > len(text):
                            abstract = full_text.replace(text, "", 1).strip()
                    
                    # 如果没有找到好的摘要，尝试查找相邻元素
                    if len(abstract) < 20:
                        next_elem = link.next_sibling
                        while next_elem and len(abstract) < 20:
                            if hasattr(next_elem, 'text') and next_elem.text.strip():
                                abstract = next_elem.text.strip()
                                break
                            next_elem = next_elem.next_sibling
                    
                    # 裁剪摘要长度
                    if ABSTRACT_MAX_LENGTH and len(abstract) > ABSTRACT_MAX_LENGTH:
                        abstract = abstract[:ABSTRACT_MAX_LENGTH]
                        
                    list_data.append({
                        "title": text,
                        "abstract": abstract,
                        "url": href,
                        "rank": rank
                    })
                    logger.debug(f"提取到备选搜索结果 #{rank}: {text}")
                
                # 如果找到了结果，返回
                if list_data:
                    logger.debug(f"通过备选方法提取了 {len(list_data)} 个搜索结果")
                    return list_data, None
            
            # 检查是否有错误消息
            error_msg = root.find("div", class_="b_searcherrmsg")
            if error_msg:
                logger.error(f"必应搜索返回错误: {error_msg.text.strip()}")
            
            # 找到下一页按钮 (尝试多种可能的选择器)
            next_url = None
            
            # 方式1: 标准下一页按钮
            pagination_classes = ["b_widePag sb_bp", "b_pag"]
            for cls in pagination_classes:
                next_page = root.find("a", class_=cls)
                if next_page and any(txt in next_page.text for txt in ["下一页", "Next", "下页"]):
                    next_url = next_page.get("href", "")
                    if next_url and not next_url.startswith("http"):
                        next_url = (cn_bing_host_url if is_cn_bing else bing_host_url) + next_url
                    break
            
            # 方式2: 备用下一页按钮
            if not next_url:
                pagination = root.find_all("a", class_="sb_pagN")
                if pagination:
                    next_url = pagination[0].get("href", "")
                    if next_url and not next_url.startswith("http"):
                        next_url = (cn_bing_host_url if is_cn_bing else bing_host_url) + next_url
            
            # 方式3: 通用导航元素
            if not next_url:
                nav_links = root.find_all("a")
                for link in nav_links:
                    if link.text.strip() in ["下一页", "Next", "下页", "»", ">>"]:
                        next_url = link.get("href", "")
                        if next_url and not next_url.startswith("http"):
                            next_url = (cn_bing_host_url if is_cn_bing else bing_host_url) + next_url
                        break
            
            logger.debug(f"已解析 {len(list_data)} 个结果，下一页链接: {next_url}")
            return list_data, next_url
            
        except Exception as e:
            logger.error(f"解析页面时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return None, None

class BingSearchTool(BaseTool):
    """从必应上搜索相关内容工具"""
    name = "search_bing"
    description = "从必应上搜索相关内容/从Bing上搜索相关内容"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询关键词"
            }
        },
        "required": ["query"]
    }

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行网络搜索

        Args:
            function_args: 工具参数

        Returns:
            Dict: 工具执行结果
        """
        try:
            query = function_args.get("query", "")
            logger.info(f"开始必应搜索: {query}")

            # 添加重试机制
            max_retries = 1  # 国际版必应重试次数
            cn_max_retries = 5  # 国内版必应重试次数
            result = None

            # 首先尝试国际版必应
            for attempt in range(max_retries):
                try:
                    logger.info(f"尝试使用国际版必应 (www.bing.com) 搜索: {query}")
                    bing_search = BingSearch()
                    bing_search.session.headers = HEADERS
                    result = bing_search.search(query)
                    if result:
                        logger.info(f"国际版必应搜索成功，找到 {len(result)} 个结果")
                        break
                    logger.warning(f"搜索尝试 {attempt+1}/{max_retries} 未找到结果")
                except Exception as e:
                    logger.error(f"国际版必应搜索尝试 {attempt+1}/{max_retries} 失败: {str(e)}")

            # 如果国际版必应搜索失败，尝试中国版必应
            if not result:
                logger.info(f"国际版必应搜索失败，尝试中国版必应 (cn.bing.com)")
                for attempt in range(cn_max_retries):
                    try:
                        logger.info(f"尝试使用中国版必应 (cn.bing.com) 搜索: {query}")
                        bing_search = BingSearch()
                        bing_search.session.headers = CN_BING_HEADERS
                        # 使用中国版必应URL
                        global bing_search_url, bing_host_url
                        original_search_url = bing_search_url
                        original_host_url = bing_host_url
                        bing_search_url = cn_bing_search_url
                        bing_host_url = cn_bing_host_url

                        try:
                            result = bing_search.search(query)
                        finally:
                            # 恢复全局URL变量
                            bing_search_url = original_search_url
                            bing_host_url = original_host_url

                        if result:
                            logger.info(f"中国版必应搜索成功，找到 {len(result)} 个结果")
                            break
                        logger.warning(f"中国版必应搜索尝试 {attempt+1}/{cn_max_retries} 未找到结果")
                    except Exception as e:
                        logger.error(f"中国版必应搜索尝试 {attempt+1}/{cn_max_retries} 失败: {str(e)}")

            logger.debug(f"必应搜索结果: {result}")

            if result:
                documents = [f'网页连接：{item.get("url", "")}，标题：{item.get("title", "")}，简介：{item.get("abstract", "")}' for item in result]
                logger.debug(f"search_bing结果: {documents}")
                content = f"你的必应搜索结果: {documents}"
            else:
                content = f"你没能从必应搜索到{query}的相关内容"

            logger.info(f"search_bing结果: {content}")
            return {
                "name": self.name,
                "content": content
            }
        except Exception as e:
            logger.error(f"必应搜索执行失败: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "name": self.name,
                "content": f"必应搜索失败: {str(e)}"
            }

# 注册工具
register_tool(BingSearchTool)