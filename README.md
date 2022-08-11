# Amiya-Bot

![PyPI](https://img.shields.io/pypi/v/amiyabot)

简洁高效的异步 Python QQ 机器人框架

官方文档：[www.amiyabot.com](https://www.amiyabot.com/)

    pip install amiyabot

```python
import asyncio

from amiyabot import AmiyaBot, Message, Chain

bot = AmiyaBot(appid='******', token='******')


@bot.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')


asyncio.run(bot.start())
```
