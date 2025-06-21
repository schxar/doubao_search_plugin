import base64
import requests

def get_random_pixiv_image(content_rating=0, keyword=None, tag=None, proxy="http://127.0.0.1:7897"):
    """
    获取一张随机Pixiv图片，返回datauri格式的base64 jpg图片。
    :param content_rating: 0为全年龄，1为限制级，2为混合
    :param keyword: 可选，关键词
    :param tag: 可选，标签，多个用|分隔
    :param proxy: 代理地址
    :return: datauri格式的base64 jpg图片
    :raises: Exception 获取失败时抛出异常
    """
    api_url = "https://api.lolicon.app/setu/v2"
    payload = {
        "r18": int(content_rating),
        "num": 1,
        "size": ["original", "regular"],
        "proxy": "i.pixiv.re"
    }
    if keyword:
        payload["keyword"] = keyword
    if tag:
        payload["tag"] = tag.split("|") if "|" in tag else [tag]
    proxies = {"http": proxy, "https": proxy}
    resp = requests.post(api_url, json=payload, timeout=10, proxies=proxies)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise Exception(f"API错误: {data['error']}")
    if not data.get("data"):
        # 尝试移除keyword和tag重试
        payload.pop("keyword", None)
        payload.pop("tag", None)
        resp = requests.post(api_url, json=payload, timeout=10, proxies=proxies)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("data"):
            raise Exception("未获取到图片")
    image_info = data["data"][0]
    image_url = image_info["urls"].get("regular") or image_info["urls"].get("original")
    if not image_url and image_info["urls"]:
        image_url = next(iter(image_info["urls"].values()))
    if not image_url:
        raise Exception("未获取到图片URL")
    img_resp = requests.get(image_url, timeout=10, proxies=proxies)
    img_resp.raise_for_status()
    img_bytes = img_resp.content
    base64_image = base64.b64encode(img_bytes).decode("utf-8")
    datauri = f"data:image/jpeg;base64,{base64_image}"
    return datauri