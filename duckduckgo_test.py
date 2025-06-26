from flask import Flask, request, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import os
import json
import hashlib
from datetime import datetime, timedelta

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DuckDuckGo 搜索测试</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .search-box { margin-bottom: 20px; }
        .result { margin-bottom: 15px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .result-title { font-weight: bold; margin-bottom: 5px; }
        .result-url { color: #1a0dab; margin-bottom: 5px; }
        .result-snippet { color: #545454; }
    </style>
</head>
<body>
    <h1>DuckDuckGo 搜索测试</h1>
    <form method="POST" class="search-box">
        <input type="text" name="query" placeholder="输入搜索关键词" value="{{ query }}" style="width: 70%; padding: 8px;">
        <button type="submit" style="padding: 8px 15px;">搜索</button>
    </form>
    
    {% if results %}
        <h2>搜索结果 ({{ results|length }}条)</h2>
        {% for result in results %}
            <div class="result">
                <div class="result-title">{{ result.title }}</div>
                <div class="result-url">{{ result.url }}</div>
                <div class="result-snippet">{{ result.snippet }}</div>
            </div>
        {% endfor %}
    {% endif %}
</body>
</html>
"""

def get_cache_path(query: str, cache_dir: str) -> str:
    """获取查询结果的缓存路径"""
    query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
    return os.path.join(cache_dir, f"{query_hash}.json")

def is_cache_valid(cache_path: str) -> bool:
    """检查缓存是否有效（12小时内）"""
    if not os.path.exists(cache_path):
        return False
    cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
    return datetime.now() - cache_time < timedelta(hours=12)

def duckduckgo_search(query: str, cache_dir: str) -> dict:
    """独立封装的DuckDuckGo搜索函数"""
    try:
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = get_cache_path(query, cache_dir)
        
        # 检查缓存
        if os.path.exists(cache_path) and is_cache_valid(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 配置Chrome选项 - 启用headless并模拟普通用户
        chrome_options = Options()
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
                    print(f"使用选择器 '{selector}' 找到搜索结果")
                    break
                except:
                    continue
            else:
                print("警告: 未能检测到标准搜索结果元素")
            
            # 保存页面HTML用于调试
            debug_html_path = os.path.join(cache_dir, "debug_last_page.html")
            with open(debug_html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            
            # 解析结果
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = []
            
            # 调试：打印页面关键元素
            print("页面标题:", driver.title)
            print("搜索结果容器数量:", len(soup.find_all('article')))
            
            # 提取有机搜索结果 - 使用多种选择器组合
            search_containers = set()
            for selector in [
                "article[data-testid='result']", 
                ".result",
                ".web-result",
                ".result__body",
                "[data-testid='result']"
            ]:
                search_containers.update(soup.select(selector))
            
            for container in search_containers:
                try:
                    # 优先使用data-testid属性定位元素
                    title_elem = container.find(attrs={"data-testid": "result-title-a"})
                    if not title_elem:
                        title_elem = container.find(['h2', 'h3', 'h4', 'h5', 'h6'])
                    
                    link_elem = container.find(attrs={"data-testid": "result-extras-url"})
                    if not link_elem:
                        link_elem = container.find('a', href=True)
                    
                    snippet_elem = container.find(attrs={"data-testid": "result-extras-snippet"})
                    if not snippet_elem:
                        snippet_elem = container.find(class_=lambda x: x and 'snippet' in x.lower())
                    
                    if title_elem and link_elem:
                        results.append({
                            'title': title_elem.text.strip(),
                            'url': link_elem['href'],
                            'snippet': snippet_elem.text.strip() if snippet_elem else ""
                        })
                        print(f"找到结果: {title_elem.text.strip()}")
                except Exception as e:
                    print(f"解析结果时出错: {str(e)}")
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
                
            print(f"成功获取 {len(results)} 条结果")
            return result_data
            
        except Exception as e:
            print(f"搜索过程中发生错误: {str(e)}")
            raise
        finally:
            try:
                if driver:
                    driver.quit()
                    print("浏览器已关闭")
            except Exception as e:
                print(f"关闭浏览器时出错: {str(e)}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "results": f"搜索过程中出错: {str(e)}"
        }

@app.route('/duckduckgo_test', methods=['GET', 'POST'])
def duckduckgo_test():
    if request.method == 'POST':
        query = request.form.get('query', '')
        if query:
            # 设置缓存目录
            cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'duckduckgo_test')
            
            # 执行搜索
            result = duckduckgo_search(query, cache_dir)
            if result['success']:
                return render_template_string(HTML_TEMPLATE, query=query, results=result['results'])
            
    return render_template_string(HTML_TEMPLATE, query='', results=None)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
