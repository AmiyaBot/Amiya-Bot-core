import re
import time
import asyncio
import collections

from typing import List, Dict, Tuple, Union, Optional, Callable
from amiyabot import log

Equal = collections.namedtuple('equal', ['content'])  # 全等对象，接受一个字符串，表示消息文本完全匹配该值


class Event:
    def __init__(self, instance, event_name, data):
        self.instance = instance
        self.event_name = event_name
        self.data = data

    def __str__(self):
        return f'Bot:{self.instance.appid} Event:{self.event_name}'


class Message:
    def __init__(self, instance, message: dict = None):
        """
        二次封装的消息对象
        """
        self.instance = instance
        self.message = message
        self.message_id = None
        self.message_type = None

        self.face = []
        self.image = []

        self.text = ''
        self.text_digits = ''
        self.text_origin = ''
        self.text_initial = ''
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

        self.time = int(time.time())

    def __str__(self):
        text = self.text_origin.replace('\n', ' ')
        face = ''.join([f'[face:{n}]' for n in self.face])
        image = '[image]' * len(self.image)

        return 'Bot:{bot} Guild:{guild} Channel:{channel} {direct}{nickname}: {message}'.format(
            **{
                'bot': self.instance.appid,
                'guild': self.guild_id,
                'channel': self.channel_id,
                'direct': '(direct)' if self.is_direct else '',
                'nickname': self.nickname,
                'message': text + face + image
            }
        )

    async def send(self, reply):
        await self.instance.send_chain_message(reply)

    async def wait(self,
                   reply=None,
                   force: bool = False,
                   max_time: int = 30,
                   data_filter: Callable = None):
        if self.is_direct:
            target_id = f'{self.instance.appid}_{self.guild_id}_{self.user_id}'
        else:
            target_id = f'{self.instance.appid}_{self.channel_id}_{self.user_id}'

        if reply:
            await self.instance.send_chain_message(reply)

        event: WaitEvent = await wait_events_bucket.set_event(target_id, force)
        asyncio.create_task(event.timer(max_time))

        while event.check_alive():
            await asyncio.sleep(0)
            data = event.get()
            if data:
                if data_filter:
                    res = await data_filter(data)
                    if not res:
                        event.set(None)
                        continue

                event.cancel()
                return data

        event.cancel()

    async def wait_channel(self,
                           reply=None,
                           force: bool = False,
                           clean: bool = True,
                           max_time: int = 30,
                           data_filter: Callable = None):
        if self.is_direct:
            raise WaitEventException('direct message not support "wait_channel"')

        target_id = f'{self.instance.appid}_{self.channel_id}'

        if reply:
            await self.instance.send_chain_message(reply)

        if target_id not in wait_events_bucket:
            event: ChannelWaitEvent = await wait_events_bucket.set_event(target_id, force, for_channel=True)
            asyncio.create_task(event.timer(max_time))
        else:
            event: ChannelWaitEvent = wait_events_bucket[target_id]
            if event.check_alive():
                event.reset()
                if clean:
                    event.clean()
            else:
                event.cancel()
                event: ChannelWaitEvent = await wait_events_bucket.set_event(target_id, force, for_channel=True)
                asyncio.create_task(event.timer(max_time))

        event.focus(self.message_id)

        while event.check_alive():
            if not event.on_focus(self.message_id):
                raise WaitEventOutOfFocus(event, self.message_id)

            await asyncio.sleep(0)
            data = event.get()
            if data:
                if data_filter:
                    res = await data_filter(data)
                    if not res:
                        continue

                event.reset()
                return ChannelMessagesItem(event, data)

        event.cancel()


class MessageMatch:
    @staticmethod
    def check_str(data: Message, text: str, level: int) -> Tuple[bool, int]:
        if text.lower() in data.text_origin.lower():
            return True, level or 1
        return False, 0

    @staticmethod
    def check_equal(data: Message, text: Equal, level: int) -> Tuple[bool, int]:
        if text.content == data.text_origin:
            return True, level or 10000
        return False, 0

    @staticmethod
    def check_reg(data: Message, reg: re.Pattern, level: int) -> Tuple[bool, int]:
        r = re.search(reg, data.text_origin)
        if r:
            return True, level or (r.re.groups or 1)
        return False, 0


class Verify:
    def __init__(self, result: bool, weight: Union[int, float] = 0):
        self.result = result
        self.weight = weight

    def __bool__(self):
        return bool(self.result)

    def __repr__(self):
        return f'<Verify, {self.result}, {self.weight}>'

    def __len__(self):
        return self.weight


class WaitEvent:
    def __init__(self, event_id: int, target_id: int, force: bool):
        self.event_id = event_id
        self.target_id = target_id
        self.force = force

        self.curr_time = 0

        self.data: Optional[Message] = None
        self.type = 'user'

        self.alive = True

    def __repr__(self):
        return f'WaitEvent(target_id:{self.target_id} alive:{self.alive})'

    async def timer(self, max_time: int):
        while self.alive and self.curr_time < max_time:
            await asyncio.sleep(0.2)
            self.curr_time += 0.2
        self.alive = False

    def reset(self):
        self.alive = True
        self.curr_time = 0

    def check_alive(self):
        if self.target_id not in wait_events_bucket:
            raise WaitEventCancel(self.target_id, 'target_id not exist')

        if self.event_id != wait_events_bucket[self.target_id].event_id:
            raise WaitEventCancel(self.target_id, 'event_id not equal')

        return self.alive

    def set(self, data: Optional[Message]):
        self.data = data

    def get(self) -> Message:
        return self.data

    def cancel(self):
        self.alive = False
        self.event_id = None
        del wait_events_bucket[self.target_id]


class ChannelWaitEvent(WaitEvent):
    def __init__(self, event_id: int, target_id: int, force: bool):
        super().__init__(event_id, target_id, force)

        self.data: List[Message] = list()
        self.type = 'channel'
        self.token = None

    def __repr__(self):
        return f'ChannelWaitEvent(target_id:{self.target_id} alive:{self.alive} token:{self.token})'

    def set(self, data: Optional[Message]):
        if data:
            self.data.append(data)

    def get(self) -> Message:
        if self.data:
            return self.data.pop(0)

    def focus(self, token: str):
        self.token = token

    def on_focus(self, token: str):
        return self.token == token

    def clean(self):
        self.data = list()


class ChannelMessagesItem:
    def __init__(self, event: ChannelWaitEvent, item: Message):
        self.event = event
        self.message = item

    def close_event(self):
        self.event.cancel()


class WaitEventsBucket:
    def __init__(self):
        self.id = 0
        self.lock = asyncio.Lock()
        self.bucket: Dict[Union[int, str], Union[WaitEvent, ChannelWaitEvent]] = {}

    def __contains__(self, item):
        return item in self.bucket

    def __getitem__(self, item):
        try:
            return self.bucket[item]
        except KeyError:
            return None

    def __delitem__(self, key):
        try:
            del self.bucket[key]
        except KeyError:
            pass

    async def __get_id(self):
        async with self.lock:
            self.id += 1
            return self.id

    async def set_event(self, target_id: Union[int, str], force: bool, for_channel: bool = False):
        event_id = await self.__get_id()

        if for_channel:
            event = ChannelWaitEvent(event_id, target_id, force)
        else:
            event = WaitEvent(event_id, target_id, force)

        self.bucket[target_id] = event

        return event


class WaitEventException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class WaitEventCancel(Exception):
    def __init__(self, target_id: Union[int, str], reason: str):
        self.key = target_id
        del wait_events_bucket[target_id]

        log.info(f'Wait event cancel: {target_id}, {reason}')

    def __str__(self):
        return f'WaitEventCancel: {self.key}'


class WaitEventOutOfFocus(Exception):
    def __init__(self, event: ChannelWaitEvent, token: str):
        self.token = token

        log.info(f'Wait event out of focus: new token {event.token}, curr {token}')

    def __str__(self):
        return f'WaitEventOutOfFocus: {self.token}'


wait_events_bucket = WaitEventsBucket()
