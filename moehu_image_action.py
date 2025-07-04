import os
import base64
import requests
import random
import json
import toml

# 读取代理配置，优先从config.toml读取[proxy]节
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.toml')
if not os.path.exists(CONFIG_PATH):
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.toml')
PROXIES = None
try:
    if os.path.exists(CONFIG_PATH):
        config = toml.load(CONFIG_PATH)
        proxy_cfg = config.get('proxy', {})
        use_proxy = proxy_cfg.get('use_proxy', False)
        proxy_url = proxy_cfg.get('proxy_url', '')
        if use_proxy and proxy_url:
            PROXIES = {"http": proxy_url, "https": proxy_url}
except Exception as e:
    print(f"代理配置读取失败: {e}")
if PROXIES is None:
    PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

def get_moehu_image(image_type=None, proxy=None):
    """
    获取一张moehu.org图片，返回datauri格式的base64 jpg图片。
    :param image_type: 图片类型(2d, 3d, vtuber, character, game, anime, emoji)
    :param proxy: 代理地址（如不传则自动读取proxy_setting.json）
    :return: datauri格式的base64 jpg图片
    :raises: Exception 获取失败时抛出异常
    """
    type_lists = {
        "2d": [
            "img1", "img2", "sjpic", "pc", 
            "acghs", "acgbs", "kemonomimi", 
            "yin", "xingk", "loli"
        ],
        "3d": ["xjj", "gqbz", "cat"],
        "vtuber": [
            "gawr-gura", "yukihana", "natsuiro",
            "uruha-rushia", "hanazono-serena", "sasaki-saku",
            "tsunomaki-watame", "tokoyami-towa", "amamiya-kokoro",
            "usada-pekora", "ninomae", "ookami-mio",
            "sara-hoshikawa", "sakura-miko", "holoen",
            "kizunaai", "kagura-nana", "kagura-mea",
            "fubuki", "inugami-korone", "aqua",
            "nekomiya-hinata"
        ],
        "character": [
            "myn", "ydmy", "miku", "tianyi", "gokou-ruri",
            "mashiro", "kano", "saber", "yoshino", "misakimei",
            "akari", "kanna", "miaops", "nymph", "noel",
            "kurumi", "violet", "shinobu", "kazuki", "iliya",
            "beatrice", "umr", "rem", "aharen", "02",
            "aniya", "takagi", "misaka-mikoto", "yor", "mizuhara",
            "nico", "tangkk", "eru", "asuna", "chiro",
            "karyl", "haibara", "hinatsuru", "shimarin", "rikka",
            "katoumegumi", "yukino", "siesta", "hayasakaai", "kaguya",
            "haruhi", "chika", "nezuko", "onoderaoosaki", "nakanomiku",
            "elaina", "ruiko", "kuroko", "konata", "shiroganekei",
            "linomiko", "kanade", "kitagawa-marin", "amayadori-machi",
            "makise-kurisu", "lsla", "yuzuriha-inori", "uranus-queen",
            "yashiro-nene", "filo", "shokuho-isaki", "gasai-yuno",
            "nagatoro-hayase", "noname-kumo", "izumi-sagiri", "kuriyama-mirai",
            "nyaruko", "ogiwara-sayu", "blois", "miniwa-tsumiki"
        ],
        "game": ["ys", "mrfz", "blhx", "dongf", "blda", "yzk", "snqx", "bh3"],
        "anime": [
            "saima", "re0", "sao", "yaowei", "gmzr",
            "5huajia", "bingg", "kiminame", "gongzhulj", "spyfamily",
            "camp", "yuruyuri", "miyone", "xuebulai", "nobiyori",
            "kin-iro-mosaic", "flag-ojousama", "hori-to-miyamura", "saenai-heroine", "mydcy",
            "slime-300", "fox-senko", "yu-gi-oh", "lycoris-recoil", "akame-ga-kill",
            "fgo", "k-on", "lovelive", "overlord", "hentaiandneko",
            "majutsu-koushi", "kara-no-kyoukai", "kobayashi-no-dragon", "toradora", "tensei-slime",
            "hana-no-amae", "ika-usume", "celia-claire", "kuma-bear", "sekai-shukufuku"
        ],
        "emoji": [
            "bqb", "gcmm", "mc", "kemomimi", "miao",
            "akqa", "cheshire", "capoo", "ceciliabqb", "cecilia",
            "longtu", "luox", "huaji", "pand", "tfkz",
            "ysbqb", "beifang", "kenan", "tomandjerry", "whitevillain",
            "xiaohua", "toukui", "laofan", "goum", "sofei",
            "yingyy", "caomeiguo", "shawu"
        ]
    }
    all_ids = []
    for ids in type_lists.values():
        all_ids.extend(ids)
    if not image_type or image_type not in type_lists:
        image_id = random.choice(all_ids)
    else:
        image_id = random.choice(type_lists[image_type])
    api_url = f"https://img.moehu.org/pic.php?id={image_id}&size=larger&cdn=baidu"
    # 优先使用proxy参数，否则用PROXIES
    proxies = {"http": proxy, "https": proxy} if proxy else PROXIES
    img_resp = requests.get(api_url, timeout=10, proxies=proxies)
    img_resp.raise_for_status()
    img_bytes = img_resp.content
    if not img_bytes or len(img_bytes) < 100:
        raise Exception("无效的图片数据")
    base64_image = base64.b64encode(img_bytes).decode("utf-8")
    datauri = f"data:image/jpeg;base64,{base64_image}"
    return datauri
