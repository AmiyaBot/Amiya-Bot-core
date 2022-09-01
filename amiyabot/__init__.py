import asyncio

from typing import List, Dict, Type, Union
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters.mirai import MiraiBotInstance
from amiyabot.adapters.tencent import TencentBotInstance
from amiyabot.network.httpServer import HttpServer
from amiyabot.handler import BotHandlerFactory, GroupConfig
from amiyabot.handler.messageHandler import message_handler
from amiyabot.builtin.lib.htmlConverter import ChromiumBrowser
from amiyabot.builtin.messageChain import Chain, ChainBuilder
from amiyabot.builtin.message import Event, Message, WaitEventCancel, WaitEventOutOfFocus, Equal
from amiyabot import log

chromium = ChromiumBrowser()


class AmiyaBot(BotHandlerFactory):
    def __init__(self,
                 appid: str,
                 token: str,
                 private: bool = False,
                 adapter: Type[BotAdapterProtocol] = TencentBotInstance):
        super().__init__(appid, token, adapter)

        self.private = private
        self.send_message = self.instance.send_message

    async def start(self, enable_chromium: bool = False):
        if enable_chromium:
            await chromium.launch()

        await self.instance.connect(self.private, self.__message_handler)

    def close(self):
        self.instance.close()

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

        self.__ready = False
        self.__instances: Dict[str, AmiyaBot] = {
            str(item.appid): item for item in bots
        }

    def __getitem__(self, appid: Union[str, int]):
        return self.__instances.get(str(appid), None)

    def __delitem__(self, appid: Union[str, int]):
        self.__instances[str(appid)].close()
        del self.__instances[str(appid)]

    async def start(self, enable_chromium: bool = False):
        assert not self.__ready, 'MultipleAccounts already started'

        self.__ready = True

        if self.__instances:
            await asyncio.wait(
                [
                    self.append(item, start_up=False).start(enable_chromium) for _, item in self.__instances.items()
                ]
            )

        while True:
            await asyncio.sleep(1)

    def append(self, item: AmiyaBot, enable_chromium: bool = False, start_up: bool = True):
        assert self.__ready, 'MultipleAccounts not started'

        item = self.__combine_factory(item)
        appid = str(item.appid)

        if appid not in self.__instances:
            self.__instances[appid] = item
            if start_up:
                asyncio.create_task(item.start(enable_chromium))

        return item

    def close(self):
        for _, item in self.__instances.items():
            item.close()

    def __combine_factory(self, item: AmiyaBot):
        item.prefix_keywords += self.prefix_keywords
        item.message_handlers += self.message_handlers
        item.after_reply_handlers += self.after_reply_handlers
        item.before_reply_handlers += self.before_reply_handlers
        item.message_handler_middleware += self.message_handler_middleware

        item.group_config.config.update(self.group_config.config)

        self.__combine_dict_handlers(item, 'event_handlers')
        self.__combine_dict_handlers(item, 'exception_handlers')

        return item

    def __combine_dict_handlers(self, item: AmiyaBot, keyname: str):
        for e in getattr(self, keyname):
            if e not in getattr(item, keyname):
                getattr(item, keyname)[e] = getattr(self, keyname)[e]
            else:
                getattr(item, keyname)[e] += getattr(self, keyname)[e]
