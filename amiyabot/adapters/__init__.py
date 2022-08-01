import abc

from typing import Union
from amiyabot.builtin.message import Event, Message
from amiyabot.builtin.messageChain import Chain


class BotAdapterProtocol(object):
    def __init__(self, appid: str, token: str):
        self.appid = appid
        self.token = token

    async def get_me(self):
        pass

    async def get_message(self, channel_id: str, message_id: str):
        pass

    @abc.abstractmethod
    async def send_chain_message(self, chain: Chain):
        raise NotImplementedError

    @abc.abstractmethod
    async def send_message(self, channel_id: str, user_id: str, direct_src_guild_id: str):
        raise NotImplementedError

    @abc.abstractmethod
    async def package_message(self, event: str, message: dict, is_reference: bool = False) -> Union[Message, Event]:
        """
        预处理并封装消息对象

        :param is_reference: 是否是引用的消息
        :param event:        事件名
        :param message:      消息对象
        """
        raise NotImplementedError
