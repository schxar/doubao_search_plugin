import os
import base64
import time
import json
import random
from pathlib import Path
import requests
import asyncio
from functools import partial

CACHE_DIR = Path("cache/pixiv_ranking")
CACHE_FILE = CACHE_DIR / "ranking.json"
CACHE_EXPIRE = 12 * 60 * 60  # 12小时缓存

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 读取代理配置
PROXY_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "proxy_setting.json")
if os.path.exists(PROXY_CONFIG_PATH):
    with open(PROXY_CONFIG_PATH, "r", encoding="utf-8") as f:
        PROXIES = json.load(f)
else:
    PROXIES = None

def _get_ranking_data_sync():
    """同步获取排行榜数据，带缓存机制"""
    if CACHE_FILE.exists():
        mtime = CACHE_FILE.stat().st_mtime
        if time.time() - mtime < CACHE_EXPIRE:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    api_url = "https://pixiv.mokeyjay.com/?r=api/pixiv-json"
    resp = requests.get(
        api_url,
        timeout=10,
        proxies=PROXIES
    )
    resp.raise_for_status()
    data = resp.json()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data

def get_pixiv_image_by_rank(rank=None):
    """
    获取Pixiv排行榜指定排名的图片，返回datauri格式的base64 jpg图片。
    :param rank: int类型，1-50，非法或None时自动随机。
    :return: str，datauri格式的base64 jpg图片
    :raises: Exception 获取失败时抛出异常
    """
    try:
        if not isinstance(rank, int) or not (1 <= rank <= 50):
            rank = random.randint(1, 50)
        ranking_data = _get_ranking_data_sync()
        if not ranking_data or "data" not in ranking_data:
            raise Exception("获取排行榜数据失败")
        target_item = next((item for item in ranking_data["data"] if item["rank"] == rank), None)
        if not target_item:
            raise Exception(f"未找到排名{rank}的图片")
        image_url = target_item["url"]
        img_resp = requests.get(
            image_url,
            timeout=10,
            proxies=PROXIES
        )
        img_resp.raise_for_status()
        img_bytes = img_resp.content
        base64_image = base64.b64encode(img_bytes).decode("utf-8")
        datauri = f"data:image/jpeg;base64,{base64_image}"
        return datauri
    except Exception as e:
        raise Exception(f"Pixiv图片获取失败: {e}")
