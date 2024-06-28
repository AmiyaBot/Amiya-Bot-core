# Amiya-Bot

![PyPI](https://img.shields.io/pypi/v/amiyabot)

简洁高效的 Python 异步渐进式 QQ 机器人框架！

现已支持：

- [QQ频道机器人](https://www.amiyabot.com/develop/adapters/qqChannel)
- [QQ群机器人](https://www.amiyabot.com/develop/adapters/qqGroup)
- [QQ全域机器人](https://www.amiyabot.com/develop/adapters/qqGlobal)
- [KOOK机器人](https://www.amiyabot.com/develop/adapters/kook)
- [Mirai-Api-Http](https://www.amiyabot.com/develop/adapters/mah)
- [Go-CQHttp](https://www.amiyabot.com/develop/adapters/gocq)
- [ComWeChatBot Client](https://www.amiyabot.com/develop/adapters/comwechat)
- [OneBot 11](https://www.amiyabot.com/develop/adapters/onebot11)
- [OneBot 12](https://www.amiyabot.com/develop/adapters/onebot12)

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

### 多账户

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

### 使用适配器

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

