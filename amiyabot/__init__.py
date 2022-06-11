from . import env

import qqbot
import asyncio

from typing import List
from amiyabot.handler import BotHandlerFactory, BotInstance
from amiyabot.handler.messageHandler import message_handler
from amiyabot.builtin.lib.htmlConverter import ChromiumBrowser
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.message import Message, WaitEventCancel, WaitEventOutOfFocus, Equal
from amiyabot import log

chromium = ChromiumBrowser()


class AmiyaBot(BotHandlerFactory):
    def __init__(self, appid: str, token: str, private: bool = False):
        super().__init__(appid, token)

        self.handler_type = qqbot.HandlerType.AT_MESSAGE_EVENT_HANDLER
        if private:
            self.handler_type = qqbot.HandlerType.MESSAGE_EVENT_HANDLER

    async def start(self, enable_chromium: bool = False):
        if enable_chromium:
            await chromium.launch()
        await qqbot.async_listen_events(self.instance.token,
                                        False,
                                        qqbot.Handler(self.handler_type, self.__message_handler),
                                        ret_coro=True)

    async def __message_handler(self, event, message: qqbot.Message):
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
        self.__combine_handlers()

        await asyncio.wait(
            [item.start(enable_chromium) for item in self.bots]
        )

    def __combine_handlers(self):
        for item in self.bots:
            item.prefix_keywords += self.prefix_keywords
            item.message_handlers += self.message_handlers
            item.after_reply_handlers += self.after_reply_handlers
            item.before_reply_handlers += self.before_reply_handlers
            item.message_handler_middleware += self.message_handler_middleware

            for e in self.exception_handlers:
                if e not in item.exception_handlers:
                    item.exception_handlers[e] = self.exception_handlers[e]
                else:
                    item.exception_handlers[e] += self.exception_handlers[e]
