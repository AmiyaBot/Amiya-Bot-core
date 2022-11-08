import asyncio

from typing import Dict, Type, Union
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters.mirai import MiraiBotInstance
from amiyabot.adapters.tencent import TencentBotInstance
from amiyabot.network.httpServer import HttpServer, ServerEventHandler
from amiyabot.handler import BotInstance, PluginInstance, GroupConfig
from amiyabot.handler.messageHandler import message_handler
from amiyabot.builtin.lib.browserService import BrowserLaunchConfig, basic_browser_service
from amiyabot.builtin.lib.timedTask import tasks_control
from amiyabot.builtin.messageChain import Chain, ChainBuilder
from amiyabot.builtin.message import Event, Message, WaitEventCancel, WaitEventOutOfFocus, Equal
from amiyabot import log


class AmiyaBot(BotInstance):
    def __init__(self,
                 appid: str,
                 token: str,
                 private: bool = False,
                 adapter: Type[BotAdapterProtocol] = TencentBotInstance):
        super().__init__(appid, token, adapter)

        self.private = private
        self.send_message = self.instance.send_message

        self.__allow_close = True

        ServerEventHandler.on_shutdown.append(self.close)

    async def start(self, launch_browser: Union[bool, BrowserLaunchConfig] = False):
        asyncio.create_task(tasks_control.run_tasks())

        if launch_browser:
            await basic_browser_service.launch(BrowserLaunchConfig() if launch_browser is True else launch_browser)

        await self.instance.connect(self.private, self.__message_handler)

    def close(self):
        if self.__allow_close:
            self.__allow_close = False
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


class MultipleAccounts(BotInstance):
    def __init__(self, *bots: AmiyaBot):
        super().__init__()

        self.__ready = False
        self.__instances: Dict[str, AmiyaBot] = {
            str(item.appid): item for item in bots
        }
        self.__keep_alive = True

        ServerEventHandler.on_shutdown.append(self.close)

    def __contains__(self, appid: Union[str, int]):
        return str(appid) in self.__instances

    def __getitem__(self, appid: Union[str, int]):
        return self.__instances.get(str(appid), None)

    def __delitem__(self, appid: Union[str, int]):
        self.__instances[str(appid)].close()
        del self.__instances[str(appid)]

    async def start(self, launch_browser: Union[bool, BrowserLaunchConfig] = False):
        assert not self.__ready, 'MultipleAccounts already started'

        self.__ready = True

        if self.__instances:
            await asyncio.wait(
                [
                    self.append(item, start_up=False).start(launch_browser) for _, item in self.__instances.items()
                ]
            )

        while self.__keep_alive:
            await asyncio.sleep(1)

    def append(self, item: AmiyaBot, launch_browser: Union[bool, BrowserLaunchConfig] = False, start_up: bool = True):
        assert self.__ready, 'MultipleAccounts not started'

        item.combine_factory(self)

        appid = str(item.appid)

        if appid not in self.__instances:
            self.__instances[appid] = item
            if start_up:
                asyncio.create_task(item.start(launch_browser))

        return item

    def close(self):
        for _, item in self.__instances.items():
            item.close()

        self.__keep_alive = False
