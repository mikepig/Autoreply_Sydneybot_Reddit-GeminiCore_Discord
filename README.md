# Discord上的自动回复机器人，由Gemini驱动，支持自定义设置

Discord的自动回复机器人

将Reddit鸭鸭Autoreplybot Gemini核心+人社/触发逻辑保留，将Reddit依赖换成discord适配

## 功能，

- 通过设置system_prompt来为GEMINI创建人设
- 通过让AI在回复之前学习子版块的风格，比如学习用户的帖子和评论，生成更高质量的回复.
- 自定义机器人回复的频率和触发机器人回复的条件。
- 可以回复图片
- 自定义触发词


## 环境

- Python 3.11+ with pip.
- Windows 10+, macOS or Linux.

## 如何使用
到 Google AI Studio 申请 [Gemini API Key]，免费档可日刷 15 次左右。

在config.json中设置 gemini_api_key，discord bot token，根据自己的需求修改persona

运行 ```python discord_bot.py```


## 来源
- https://github.com/AutoReplySender/Youmo-SydneyBot
- https://github.com/juzeon/SydneyQt
- https://github.com/JayGarland/Autoreply_Sydneybot_Reddit/tree/GeminiCore_Reddit
