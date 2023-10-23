import abc

from typing import Optional


class BotInstanceAPIProtocol:
    @abc.abstractmethod
    async def get(self, url: str, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def post(self, url: str, data: Optional, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def request(self, url: str, method: str, *args, **kwargs):
        raise NotImplementedError

    async def get_user_avatar(self, *args, **kwargs):
        return ''
