import typing
import asyncio

from typing import Optional, Union

from amiyabot import log
from amiyabot.util import random_code

# adapters
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters.kook import KOOKBotInstance
from amiyabot.adapters.mirai import MiraiBotInstance
from amiyabot.adapters.cqhttp import CQHttpBotInstance
from amiyabot.adapters.onebot.v11 import OneBot11Instance
from amiyabot.adapters.onebot.v12 import OneBot12Instance
from amiyabot.adapters.tencent.qqGuild import QQGuildBotInstance, QQGuildSandboxBotInstance
from amiyabot.adapters.comwechat import ComWeChatBotInstance

# network
from amiyabot.network.httpServer import HttpServer

# factory
from amiyabot.factory import BotInstance, PluginInstance, GroupConfig

# handler
from amiyabot.handler.messageHandler import message_handler
from amiyabot.signalHandler import SignalHandler

# lib
from amiyabot.builtin.lib.eventBus import event_bus
from amiyabot.builtin.lib.timedTask import TasksControl
from amiyabot.builtin.lib.browserService import BrowserLaunchConfig, basic_browser_service

# message
from amiyabot.builtin.messageChain import Chain, ChainBuilder, InlineKeyboard, CQCode
from amiyabot.builtin.message import (
    Event,
    EventList,
    Message,
    Waiter,
    WaitEventCancel,
    WaitEventOutOfFocus,
    Equal,
)


class AmiyaBot(BotInstance):
    def __init__(
        self,
        appid: Optional[str] = None,
        token: Optional[str] = None,
        private: bool = False,
        adapter: typing.Type[BotAdapterProtocol] = QQGuildBotInstance,
    ):
        if not appid:
            appid = random_code(10)

        super().__init__(appid, token, adapter, private)

        self.send_message = self.instance.send_message

        self.__closed = False

        SignalHandler.on_shutdown.append(self.close)

    async def start(self, launch_browser: typing.Union[bool, BrowserLaunchConfig] = False):
        TasksControl.start()

        if launch_browser:
            await basic_browser_service.launch(BrowserLaunchConfig() if launch_browser is True else launch_browser)

        self.run_timed_tasks()
        await self.instance.start(self.__message_handler)

    async def close(self):
        if not self.__closed:
            self.__closed = True
            await self.instance.close()

    async def __message_handler(self, data: Optional[Union[Message, Event, EventList]]):
        if not data:
            return False

        async with log.catch(
            desc='handler error:',
            ignore=[asyncio.TimeoutError, WaitEventCancel, WaitEventOutOfFocus],
            handler=self.__exception_handler(data),
        ):
            await message_handler(self, data)

    def __exception_handler(self, data: Union[Message, Event, EventList]):
        async def handler(err: Exception):
            if self.exception_handlers:
                subclass = type(err)
                if subclass not in self.exception_handlers:
                    subclass = Exception

                for func in self.exception_handlers[subclass]:
                    async with log.catch('exception handler error:'):
                        await func(err, self.instance, data)

        return handler


class MultipleAccounts(BotInstance):
    def __init__(self, *bots: AmiyaBot):
        super().__init__()

        self.__ready = False
        self.__instances: typing.Dict[str, AmiyaBot] = {str(item.appid): item for item in bots}
        self.__keep_alive = True

        SignalHandler.on_shutdown.append(self.close)

    def __iter__(self):
        return iter(self.__instances.values())

    def __contains__(self, appid: typing.Union[str, int]):
        return str(appid) in self.__instances

    def __getitem__(self, appid: typing.Union[str, int]):
        return self.__instances.get(str(appid), None)

    def __delitem__(self, appid: typing.Union[str, int]):
        asyncio.create_task(self.__instances[str(appid)].close())
        del self.__instances[str(appid)]

    async def start(self, launch_browser: typing.Union[bool, BrowserLaunchConfig] = False):
        assert not self.__ready, 'MultipleAccounts already started'

        self.__ready = True

        if self.__instances:
            await asyncio.wait(
                [self.append(item, start_up=False).start(launch_browser) for _, item in self.__instances.items()]
            )

        while self.__keep_alive:
            await asyncio.sleep(1)

    def append(
        self,
        item: AmiyaBot,
        launch_browser: typing.Union[bool, BrowserLaunchConfig] = False,
        start_up: bool = True,
    ):
        assert self.__ready, 'MultipleAccounts not started'

        item.combine_factory(self)

        appid = str(item.appid)

        if appid not in self.__instances:
            self.__instances[appid] = item
            if start_up:
                asyncio.create_task(item.start(launch_browser))

        return item

    async def close(self):
        for _, item in self.__instances.items():
            await item.close()

        self.__keep_alive = False
