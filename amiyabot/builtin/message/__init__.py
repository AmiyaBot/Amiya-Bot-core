import re
import asyncio

from typing import Callable, Optional, Union, List, Tuple, Any
from dataclasses import dataclass

from .callback import MessageCallback, MessageCallbackType
from .structure import EventStructure, MessageStructure, Verify
from .waitEvent import (
    WaitEvent,
    ChannelWaitEvent,
    ChannelMessagesItem,
    WaitEventsBucket,
    WaitEventException,
    WaitEventCancel,
    WaitEventOutOfFocus,
    wait_events_bucket
)

SendReturn = Optional[MessageCallbackType]
WaitReturn = Optional[MessageStructure]
WaitCallbackReturn = Tuple[Optional[MessageStructure], SendReturn]
WaitChannelReturn = Optional[ChannelMessagesItem]
WaitChannelCallbackReturn = Tuple[Optional[ChannelMessagesItem], SendReturn]


@dataclass
class Equal:
    content: str


class Event(EventStructure):
    ...


class EventList:
    def __init__(self, events: list = None):
        self.events: List[Event] = events or list()

    def __iter__(self):
        return iter(self.events)

    def append(self, instance, event_name, data):
        self.events.append(
            Event(instance, event_name, data)
        )


class Message(MessageStructure):
    async def send(self, reply) -> SendReturn:

        # todo 生命周期 - message_before_send
        for method in self.bot.process_message_before_send:
            reply = await method(reply, self.factory_name, self.instance) or reply

        callbacks: List[MessageCallback] = await self.instance.send_chain_message(reply, use_http=True)

        # todo 生命周期 - message_after_send
        for method in self.bot.process_message_after_send:
            await method(reply, self.factory_name, self.instance)

        if not callbacks:
            return None

        return callbacks if len(callbacks) > 1 else callbacks[0]

    async def recall(self):
        if self.message_id:
            await self.instance.recall_message(self.message_id, self.channel_id or self.user_id)

    async def wait(self, *args, **kwargs) -> WaitReturn:
        data, _ = await self.__wait_context(*args, **kwargs)
        return data

    async def wait_callback(self, *args, **kwargs) -> WaitCallbackReturn:
        return await self.__wait_context(*args, **kwargs)

    async def wait_channel(self, *args, **kwargs) -> WaitChannelReturn:
        data, _ = await self.__wait_channel_context(*args, **kwargs)
        return data

    async def wait_channel_callback(self, *args, **kwargs) -> WaitChannelCallbackReturn:
        return await self.__wait_channel_context(*args, **kwargs)

    async def __wait_channel_context(self,
                                     reply=None,
                                     force: bool = False,
                                     clean: bool = True,
                                     max_time: int = 30,
                                     data_filter: Callable = None):
        if self.is_direct:
            raise WaitEventException('direct message not support "wait_channel"')

        target_id = f'{self.instance.appid}_{self.channel_id}'

        callbacks: SendReturn = None
        if reply:
            callbacks = await self.send(reply)

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

                return ChannelMessagesItem(event, data), callbacks

        event.cancel()

        return None, callbacks

    async def __wait_context(self,
                             reply=None,
                             force: bool = False,
                             max_time: int = 30,
                             data_filter: Callable = None):
        if self.is_direct:
            target_id = f'{self.instance.appid}_{self.guild_id}_{self.user_id}'
        else:
            target_id = f'{self.instance.appid}_{self.channel_id}_{self.user_id}'

        callbacks: SendReturn = None
        if reply:
            callbacks = await self.send(reply)

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

                return data, callbacks

        event.cancel()

        return None, callbacks


class MessageMatch:
    @staticmethod
    def check_str(data: Message, text: str, level: int) -> Tuple[bool, int, Any]:
        if text.lower() in data.text.lower():
            return True, level or 1, text
        return False, 0, None

    @staticmethod
    def check_equal(data: Message, text: Equal, level: int) -> Tuple[bool, int, Any]:
        if text.content == data.text:
            return True, level or 10000, text
        return False, 0, None

    @staticmethod
    def check_reg(data: Message, reg: re.Pattern, level: int) -> Tuple[bool, int, Any]:
        r = re.search(reg, data.text)
        if r:
            return True, level or (r.re.groups or 1), list(r.groups())
        return False, 0, None


Waiter = Union[WaitEvent, ChannelWaitEvent, None]
EventType = Union[Event, EventList]
