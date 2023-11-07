# Amiya-Bot

![PyPI](https://img.shields.io/pypi/v/amiyabot)

简洁高效的 Python 异步渐进式 QQ 频道机器人框架！<br>
可使用内置的适配器创建 KOOK、mirai-api-http、go-cqhttp、ComWeChat Client 以及支持 OneBot v11/12 的机器人实现。

官方文档：[www.amiyabot.com](https://www.amiyabot.com/)

## Install

    pip install amiyabot

## Get started

### Single mode

```python
import asyncio

from amiyabot import AmiyaBot, Message, Chain

bot = AmiyaBot(appid='******', token='******')


@bot.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')


asyncio.run(bot.start())
```

### Multiple mode

```python
import asyncio

from amiyabot import MultipleAccounts, AmiyaBot, Message, Chain

bots = MultipleAccounts(
    AmiyaBot(appid='******', token='******'),
    AmiyaBot(appid='******', token='******'),
    ...
)


@bots.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')


asyncio.run(bots.start())
```

### Use adapter

```python
import asyncio

from amiyabot import AmiyaBot, Message, Chain
from amiyabot.adapters.onebot.v11 import onebot11

bot = AmiyaBot(
    appid='******',
    token='******',
    adapter=onebot11(host='127.0.0.1', http_port=8080, ws_port=8060)
)


@bot.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')


asyncio.run(bot.start())
```

## [Get more](https://www.amiyabot.com/)
