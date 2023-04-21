import abc

from typing import Union, List


class MessageCallback:
    def __init__(self, chain, instance, response):
        self.chain = chain
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
