# doubao_search_plugin
maimai的DEV 08S2 用 耐杀王 


## 插件简介
豆包搜索插件是基于火山引擎豆包模型的AI搜索插件，提供智能LLM判定和高效搜索功能。主要功能包括：
- 智能LLM判定：根据聊天内容智能判断是否需要生成图片或搜索内容。
- 高质量搜索结果生成：使用火山引擎豆包模型生成智能回复。
- 结果缓存：避免重复生成相同内容的结果。    
- 配置验证：自动验证和修复配置文件。
- 参数验证：完整的输入参数验证和错误处理。

## 内置图片相关Action说明
插件已内置并自动注册以下图片相关Action，可在对话中通过关键词或LLM判定自动触发：
- **PixivMoehuAction**：通过 [moehu.org](https://moehu.org) API 获取二次元、三次元、角色、游戏、动漫、表情包等类型图片。
- **PixivRandomImageAction**：获取Pixiv随机图片，支持内容分级、关键词、标签筛选。
- **PixivRank50Action**：获取Pixiv排行榜指定排名（1-50，默认随机）图片。

这些Action可用于满足用户发送图片、动漫、插画等多样化需求，具体参数和调用方式见插件源码注释。

## 配置文件说明
插件需要一个名为 `config.toml` 的配置文件来运行。如果您发现配置文件被重命名或丢失，请按照以下步骤操作：

1. 确保插件目录下存在 `template_config.toml` 文件。
2. 将 `template_config.toml` 文件重命名为 `config.toml`。
3. 根据需要修改 `config.toml` 中的配置，例如填写正确的 `volcano_generate_api_key`。

配置文件的主要内容包括：
- 插件基本信息配置
- API相关配置（如API密钥和基础URL）
- 结果缓存配置
- 组件启用配置

## 注意事项
- 请确保 `volcano_generate_api_key` 字段填写正确的API密钥，否则插件将无法正常工作。
- 修改配置文件后，请重新启动插件以应用更改。

## 如何获取自定义模型端点

为了使用豆包搜索插件，您需要在火山引擎控制台中创建一个无代码应用并开通联网插件。请按照以下步骤操作：

1. 打开[火山引擎控制台](https://console.volcengine.com/ark/region:ark+cn-beijing/assistant)。
2. 创建一个新的无代码应用。
3. 前往[联网插件页面](https://console.volcengine.com/ark/region:ark+cn-beijing/components?action=%7B%7D)并开通联网插件。
4. 在无代码应用中配置您的自定义模型端点。
5. 将生成的模型端点填入 `config.toml` 文件中的 `model_name` 字段。

完成以上步骤后，请确保重新启动插件以应用更改。

更多信息请参考插件的[官方文档](https://github.com/MaiM-with-u/MaiBot/tree/dev)。

## 代理配置说明

Pixiv排行榜图片功能支持自定义代理，代理配置已独立为 `proxy_setting.json` 文件，位于插件目录下。

- 默认内容如下：
  ```json
  {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897"
  }
  ```
- 如需更换代理，直接修改 `proxy_setting.json`，无需更改代码。
- 若不需要代理，可将文件内容设为 `{}` 或删除该文件。

## Pixiv排行榜图片工具

插件内置 `PixivRank50.py` 工具文件，可通过 `get_pixiv_image_by_rank(rank=None)` 获取 Pixiv 日榜指定序号（1-50）的图片，返回 datauri 格式的 base64 jpg 图片字符串。
- 参数 `rank` 非法或未填时自动随机。
- 该工具自动读取 `proxy_setting.json` 作为代理配置。

## Pixiv排行榜图片自动发送说明

每次豆包搜索插件执行一次智能搜索时，都会自动随机获取并发送一张 Pixiv 日榜图片（1-50名随机）。该图片通过内置工具 `PixivRank50.py` 获取，使用 datauri base64 格式，并自动应用 `proxy_setting.json` 代理配置。

如需关闭此功能，请在 `plugin.py` 的 Action 逻辑中移除相关调用。