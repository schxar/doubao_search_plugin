from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import random

# 可选：你可以根据需要扩展 user_agents
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
]

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "User-Agent": user_agents[0],
}

BING_SEARCH_URL = "https://www.bing.com/search?q="
ABSTRACT_MAX_LENGTH = 300

def search_bing(query: str, num_results: int = 10) -> List[Dict]:
    """
    输入query，返回必应搜索结果列表，每项包含title、url、abstract、rank。
    """
    if not query:
        return []
    results = []
    url = BING_SEARCH_URL + requests.utils.quote(query)
    headers = HEADERS.copy()
    headers["User-Agent"] = random.choice(user_agents)
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("li.b_algo")
        for idx, item in enumerate(items[:num_results], 1):
            title_tag = item.find("h2")
            link = title_tag.find("a") if title_tag else None
            title = link.text.strip() if link else ""
            url = link["href"] if link and link.has_attr("href") else ""
            abstract_tag = item.find("p")
            abstract = abstract_tag.text.strip() if abstract_tag else ""
            if len(abstract) > ABSTRACT_MAX_LENGTH:
                abstract = abstract[:ABSTRACT_MAX_LENGTH]
            results.append({
                "title": title,
                "url": url,
                "abstract": abstract,
                "rank": idx
            })
        return results
    except Exception:
        return []
