import abc

from typing import Any, Union, Callable, Coroutine
from amiyabot.builtin.message import Event, Message
from amiyabot.builtin.messageChain import Chain

handler_type = Callable[[str, dict], Coroutine[Any, Any, None]]


class BotAdapterProtocol(object):
    def __init__(self, appid: str, token: str):
        self.appid = appid
        self.token = token

    @abc.abstractmethod
    async def connect(self, private: bool, handler: handler_type):
        raise NotImplementedError

    @abc.abstractmethod
    async def send_chain_message(self, chain: Chain):
        raise NotImplementedError

    @abc.abstractmethod
    async def send_message(self, channel_id: str = '', user_id: str = '', direct_src_guild_id: str = ''):
        raise NotImplementedError

    @abc.abstractmethod
    async def package_message(self, event: str, message: dict) -> Union[Message, Event]:
        """
        预处理并封装消息对象

        :param event:        事件名
        :param message:      消息对象
        """
        raise NotImplementedError
