import abc

from typing import Optional, Union


class BotInstanceAPIProtocol:
    @abc.abstractmethod
    async def get(self, url: str, params: Optional[dict] = None, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def post(self, url: str, data: Optional[Union[dict, list]] = None, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def request(self, url: str, method: str, *args, **kwargs):
        raise NotImplementedError

    async def get_user_avatar(self, *args, **kwargs):
        return ''
