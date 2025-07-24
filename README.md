
# doubao_search_plugin 090灰度测试版本插件
# 081版本的插件在branch上，此处仅为090灰度测试版本插件

## 概述

`doubao_search_plugin` 是基于火山引擎豆包模型的 AI 智能搜索与图片生成插件，支持多种智能对话、图片与网页搜索场景。插件集成了 LLM 智能判定、丰富的图片获取、必应与 DuckDuckGo 网络搜索等能力，适用于多样化的聊天机器人和智能助手场景。

主要特性：
- **智能 LLM 判定**：自动识别用户意图，智能决定是否生成图片或进行搜索。
- **高质量内容生成**：基于火山引擎豆包模型，生成高质量智能回复。
- **多图片源支持**：内置多种图片获取方式，满足二次元、三次元、插画、表情包等需求。
- **网页搜索能力**：集成必应（Bing）和 DuckDuckGo 搜索，自动润色并返回带真实链接的摘要。
- **结果缓存**：避免重复生成相同内容，提升效率。
- **配置与参数校验**：自动验证和修复配置文件，参数完整性校验与错误处理。

---

## 内置 Action 说明

插件自动注册以下 Action，可通过关键词或 LLM 判定自动触发：

- **PixivMoehuAction**：通过 [moehu.org](https://moehu.org) API 获取二次元、三次元、角色、游戏、动漫、表情包等图片。
- **PixivRandomImageAction**：获取 Pixiv 随机图片，支持内容分级、关键词、标签筛选。
- **PixivRank50Action**：获取 Pixiv 日榜指定排名（1-50，默认随机）图片。
- **BingSearchAction**：通过必应（Bing）搜索互联网内容，AI 自动摘要润色，回复中包含真实网页链接。
- **DuckDuckGoSearchAction**：通过 DuckDuckGo 搜索互联网内容，AI 自动摘要润色，回复中包含真实网页链接。

**Action 触发方式**：
- 关键词触发（如“搜索”、“bing”、“duckduckgo”等）
- LLM 智能判定（如用户提出问题、请求图片、查询天气等）

**Action 详细参数与调用方式请参考源码注释。**

---

## 依赖环境说明

### Python 依赖
已在 `requirements.txt` 中声明，主要包括：
- openai
- requests
- pillow
- selenium >= 4.0.0
- webdriver-manager >= 3.0.0
- beautifulsoup4 >= 4.0.0

### 浏览器依赖（DuckDuckGo 搜索）
- 需本地安装 Google Chrome 浏览器（建议最新版）。
  - [Chrome官方下载](https://www.google.cn/chrome/)
- 插件首次运行时会自动下载并管理对应版本的 ChromeDriver。

如遇浏览器或驱动相关报错，请检查 Chrome 是否已正确安装，或尝试手动升级 Chrome 及 ChromeDriver。

---

## 配置文件说明

插件需要 `config.toml` 配置文件，主要内容包括：
- 插件基本信息
- API 相关配置（如 API 密钥、基础 URL、模型名称）
- 结果缓存配置
- 组件启用配置
- 代理配置

**首次使用请确保：**
1. 插件目录下存在 `config.toml` 文件（如丢失可复制 `template_config.toml` 并重命名）。
2. 填写正确的 `volcano_generate_api_key` 和 `model_name`。
3. 修改配置后需重启插件生效。

---

## 如何获取自定义模型端点

1. 登录 [火山引擎控制台](https://console.volcengine.com/ark/region:ark+cn-beijing/assistant)。
2. 创建无代码应用并开通联网插件。
3. 在无代码应用中配置自定义模型端点。
4. 将生成的模型端点填入 `config.toml` 的 `model_name` 字段。
5. 重启插件。

详细流程请参考[官方文档](https://github.com/MaiM-with-u/MaiBot/tree/dev)。

---

## 代理与 Pixiv 图片功能

Pixiv 排行榜图片功能支持自定义代理，代理配置文件为 `proxy_setting.json`，内容示例：

```json
{
  "http": "http://127.0.0.1:7897",
  "https": "http://127.0.0.1:7897"
}
```

如需更换代理，直接修改该文件，无需更改代码。若不需要代理，可将内容设为 `{}` 或删除该文件。

**Pixiv 日榜图片工具**：
- 通过 `get_pixiv_image_by_rank(rank=None)` 获取 Pixiv 日榜指定序号（1-50）的图片，返回 datauri 格式 base64 jpg 字符串。
- 该工具自动读取 `proxy_setting.json`。

**自动发送说明**：
每次执行智能搜索时，默认会自动发送一张随机 Pixiv 日榜图片（可在配置中关闭）。

---

## 常见问题与注意事项

- 请确保 API 密钥填写正确，否则插件无法正常工作。
- 修改配置后请重启插件。
- DuckDuckGo 搜索需本地安装 Chrome 浏览器。
- 如遇依赖或环境问题，请优先检查 Python 依赖和浏览器环境。

---

如需自定义 Action 行为、回复风格或图片展示方式，请直接修改 `plugin.py` 中对应 Action 的实现。