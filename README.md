# Amiya-Bot

快速构建 QQ 频道机器人

    pip install amiyabot

### 创建一个实例

```python
import asyncio

from amiyabot import AmiyaBot, Message, Chain

bot = AmiyaBot(appid='******', token='******')


@bot.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')


asyncio.run(bot.start())
```

### 创建多个单独实例

```python
import asyncio

from amiyabot import AmiyaBot, Message, Chain

bot1 = AmiyaBot(appid='******', token='******', private=True)
bot2 = AmiyaBot(appid='******', token='******')


@bot1.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')


@bot2.on_message(keywords='hey')
async def _(data: Message):
    return Chain(data).text(f'hey, {data.nickname}')


asyncio.run(
    asyncio.wait([
        bot1.start(),
        bot2.start()
    ])
)
```

### 创建一个多账号实例

```python
import asyncio

from amiyabot import AmiyaBot, MultipleAccounts, Message, Chain

bot1 = AmiyaBot(appid='******', token='******', private=True)
bot2 = AmiyaBot(appid='******', token='******')

bot = MultipleAccounts(
    [
        bot1,
        bot2
    ]
)


# 公共触发器
@bot.on_message(keywords='hello')
async def _(data: Message):
    return Chain(data).text(f'hello, {data.nickname}')


# 专属触发器
@bot1.on_message(keywords='hey')
async def _(data: Message):
    return Chain(data).text(f'hey, my name is Amiyabot')


asyncio.run(bot.start())
```
