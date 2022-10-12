import abc

from typing import Any, Union, Callable, Coroutine
from amiyabot.builtin.message import Event, Message
from amiyabot.builtin.messageChain import Chain

handler_type = Callable[[str, dict], Coroutine[Any, Any, None]]


class BotAdapterProtocol(object):
    def __init__(self, appid: str, token: str):
        self.appid = appid
        self.token = token
        self.alive = False
        self.keep_run = True

    def __str__(self):
        return 'Adapter'

    def set_alive(self, status: bool):
        self.alive = status

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def connect(self, private: bool, handler: handler_type):
        raise NotImplementedError

    @abc.abstractmethod
    async def send_chain_message(self, chain: Chain):
        raise NotImplementedError

    @abc.abstractmethod
    async def send_message(self,
                           chain: Chain,
                           user_id: str = '',
                           channel_id: str = '',
                           direct_src_guild_id: str = ''):
        """
        发送主动消息

        :param chain:               消息 Chain 对象
        :param user_id:             用户 ID
        :param channel_id:          子频道 ID
        :param direct_src_guild_id: 来源的频道 ID（私信时需要）
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def package_message(self, event: str, message: dict) -> Union[Message, Event]:
        """
        预处理并封装消息对象

        :param event:   事件名
        :param message: 消息对象
        """
        raise NotImplementedError
