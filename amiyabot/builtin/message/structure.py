import abc
import time

from typing import Any, Union, Optional, Callable


class EventStructure:
    def __init__(self, instance, event_name, data):
        self.instance = instance
        self.event_name = event_name
        self.data = data

    def __str__(self):
        return f'Bot: {self.instance.appid} Event: {self.event_name}'


class MessageStructure:
    def __init__(self, instance, message: dict = None):
        self.instance = instance
        self.message = message
        self.message_id = None
        self.message_type = None

        self.face = []
        self.image = []

        self.text = ''
        self.text_digits = ''
        self.text_unsigned = ''
        self.text_original = ''
        self.text_words = []

        self.at_target = []

        self.is_at = False
        self.is_admin = False
        self.is_direct = False

        self.user_id = None
        self.guild_id = None
        self.src_guild_id = None
        self.channel_id = None
        self.nickname = None
        self.avatar = None

        self.joined_at = None

        self.verify: Optional[Verify] = None
        self.time = int(time.time())

    def __str__(self):
        text = self.text.replace('\n', ' ')
        face = ''.join([f'[face:{n}]' for n in self.face])
        image = '[image]' * len(self.image)

        return 'Bot:{bot} Channel:{channel} User:{user}{direct} {nickname}: {message}'.format(
            **{
                'bot': self.instance.appid,
                'channel': self.channel_id,
                'user': self.user_id,
                'direct': '(direct)' if self.is_direct else '',
                'nickname': self.nickname,
                'message': text + face + image
            }
        )

    @abc.abstractmethod
    async def send(self, reply):
        raise NotImplementedError

    @abc.abstractmethod
    async def wait(self,
                   reply=None,
                   force: bool = False,
                   max_time: int = 30,
                   data_filter: Callable = None):
        raise NotImplementedError

    @abc.abstractmethod
    async def wait_channel(self,
                           reply=None,
                           force: bool = False,
                           clean: bool = True,
                           max_time: int = 30,
                           data_filter: Callable = None):
        raise NotImplementedError

    @abc.abstractmethod
    async def recall(self):
        raise NotImplementedError


class Verify:
    def __init__(self, result: bool, weight: Union[int, float] = 0, keypoint: Any = None):
        self.result = result
        self.weight = weight
        self.keypoint = keypoint

    def __bool__(self):
        return bool(self.result)

    def __repr__(self):
        return f'<Verify, {self.result}, {self.weight}>'

    def __len__(self):
        return self.weight
