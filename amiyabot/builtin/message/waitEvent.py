import asyncio

from typing import List, Dict, Union, Optional
from amiyabot import log

from .structure import MessageStructure


class WaitEvent:
    def __init__(self, event_id: int, target_id: int, force: bool):
        self.event_id = event_id
        self.target_id = target_id
        self.force = force

        self.curr_time = 0

        self.data: Optional[MessageStructure] = None
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
            raise WaitEventCancel(self, 'This event already deleted.')

        if self.event_id != wait_events_bucket[self.target_id].event_id:
            raise WaitEventCancel(self, 'Event id not equal.', del_event=False)

        if not self.alive:
            WaitEventCancel(self, 'Timeout.')

        return self.alive

    def set(self, data: Optional[MessageStructure]):
        self.data = data

    def get(self) -> MessageStructure:
        return self.data

    def cancel(self, del_event: bool = True):
        self.alive = False

        if del_event:
            del wait_events_bucket[self.target_id]


class ChannelWaitEvent(WaitEvent):
    def __init__(self, event_id: int, target_id: int, force: bool):
        super().__init__(event_id, target_id, force)

        self.data: List[MessageStructure] = list()
        self.type = 'channel'
        self.token = None

    def __repr__(self):
        return f'ChannelWaitEvent(target_id:{self.target_id} alive:{self.alive} token:{self.token})'

    def set(self, data: Optional[MessageStructure]):
        if data:
            self.data.append(data)

    def get(self) -> MessageStructure:
        if self.data:
            return self.data.pop(0)

    def focus(self, token: str):
        self.token = token

    def on_focus(self, token: str):
        return self.token == token

    def clean(self):
        self.data = list()


class ChannelMessagesItem:
    def __init__(self, event: ChannelWaitEvent, item: MessageStructure):
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
    def __init__(self, event: WaitEvent, reason: str, del_event: bool = True):
        self.key = event.target_id

        event.cancel(del_event)

        log.info(f'Wait event cancel -> {event.target_id}({event.event_id}), reason: {reason}')

    def __str__(self):
        return f'WaitEventCancel: {self.key}'


class WaitEventOutOfFocus(Exception):
    def __init__(self, event: ChannelWaitEvent, token: str):
        self.token = token

        log.info(f'Wait event out of focus: new token {event.token}, curr {token}')

    def __str__(self):
        return f'WaitEventOutOfFocus: {self.token}'


wait_events_bucket = WaitEventsBucket()
