import asyncio

from typing import List
from amiyabot.adapter import BotInstance
from amiyabot.handler import BotHandlerFactory, GroupConfig
from amiyabot.handler.messageHandler import message_handler
from amiyabot.builtin.lib.htmlConverter import ChromiumBrowser
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.message import Event, Message, WaitEventCancel, WaitEventOutOfFocus, Equal
from amiyabot import log

chromium = ChromiumBrowser()


class AmiyaBot(BotHandlerFactory):
    def __init__(self, appid: str, token: str, private: bool = False):
        super().__init__(appid, token)

        self.private = private

    async def start(self, enable_chromium: bool = False):
        if enable_chromium:
            await chromium.launch()

        await self.instance.connect(self.private, self.__message_handler)

    async def __message_handler(self, event: str, message: dict):
        async with log.catch(desc='handler error:',
                             ignore=[asyncio.TimeoutError, WaitEventCancel, WaitEventOutOfFocus],
                             handler=self.__exception_handler):
            await message_handler(self, event, message)

    async def __exception_handler(self, err: Exception):
        if self.exception_handlers:
            subclass = type(err)
            if subclass not in self.exception_handlers:
                subclass = Exception

            for func in self.exception_handlers[subclass]:
                await func(err, self.instance)


class MultipleAccounts(BotHandlerFactory):
    def __init__(self, bots: List[AmiyaBot]):
        super().__init__()

        self.bots = bots

    async def start(self, enable_chromium: bool = False):
        self.__combine_factory()

        await asyncio.wait(
            [item.start(enable_chromium) for item in self.bots]
        )

    def __combine_factory(self):
        for item in self.bots:
            item.prefix_keywords += self.prefix_keywords
            item.message_handlers += self.message_handlers
            item.after_reply_handlers += self.after_reply_handlers
            item.before_reply_handlers += self.before_reply_handlers
            item.message_handler_middleware += self.message_handler_middleware

            item.group_config.update(self.group_config)

            self.__combine_dict_handlers(item, 'event_handlers')
            self.__combine_dict_handlers(item, 'exception_handlers')

    def __combine_dict_handlers(self, item: AmiyaBot, keyname: str):
        for e in getattr(self, keyname):
            if e not in getattr(item, keyname):
                getattr(item, keyname)[e] = getattr(self, keyname)[e]
            else:
                getattr(item, keyname)[e] += getattr(self, keyname)[e]
