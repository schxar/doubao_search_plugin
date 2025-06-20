# doubao_search_plugin
maimai的DEV 08S2 用 耐杀王 


## 插件简介
豆包搜索插件是基于火山引擎豆包模型的AI搜索插件，提供智能LLM判定和高效搜索功能。主要功能包括：
- 智能LLM判定：根据聊天内容智能判断是否需要生成图片或搜索内容。
- 高质量搜索结果生成：使用火山引擎豆包模型生成智能回复。
- 结果缓存：避免重复生成相同内容的结果。    
- 配置验证：自动验证和修复配置文件。
- 参数验证：完整的输入参数验证和错误处理。

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