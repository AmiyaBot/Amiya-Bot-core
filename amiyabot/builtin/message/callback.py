import abc

from typing import Union, List, Any
from amiyabot.typeIndexes import T_BotAdapterProtocol


class MessageCallback:
    def __init__(self, instance: T_BotAdapterProtocol, response: Any):
        self.instance = instance
        self.response = response

    @abc.abstractmethod
    async def recall(self):
        """
        撤回本条消息

        :return:
        """
        raise NotImplementedError


MessageCallbackType = Union[MessageCallback, List[MessageCallback]]
