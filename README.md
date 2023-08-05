# Amiya-Bot

![PyPI](https://img.shields.io/pypi/v/amiyabot)

简洁高效的 Python 异步渐进式机器人框架，支持 KOOK、QQ频道、MiraiHttp 以及 CQHttp

官方文档：[www.amiyabot.com](https://www.amiyabot.com/)

## Install

    pip install amiyabot

## Get started

```python
import asyncio

from amiyabot import AmiyaBot, Message, Chain

bot = AmiyaBot(appid='******', token='******')


@bot.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')


asyncio.run(bot.start())
```
