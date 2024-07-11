import re
import abc
import copy
import asyncio

from typing import Callable, Optional, Union, List, Tuple, Any
from dataclasses import dataclass
from amiyabot.typeIndexes import T_Chain, T_BotAdapterProtocol
from amiyabot.network.httpRequests import Response

from .structure import EventStructure, MessageStructure, Verify, File
from .waitEvent import (
    WaitEvent,
    WaitEventsBucket,
    WaitEventCancel,
    WaitEventException,
    WaitEventOutOfFocus,
    ChannelWaitEvent,
    ChannelMessagesItem,
    wait_events_bucket,
)

WaitReturn = Optional[MessageStructure]
WaitChannelReturn = Optional[ChannelMessagesItem]
MatchReturn = Tuple[bool, int, Any]


@dataclass
class Equal:
    content: str


class Event(EventStructure):
    ...


class EventList:
    def __init__(self, events: Optional[list] = None):
        self.events: List[Event] = events or list()

    def __iter__(self):
        return iter(self.events)

    def append(self, instance, event_name, data):
        self.events.append(Event(instance, event_name, data))


class Message(MessageStructure):
    async def send(self, reply: T_Chain) -> Optional['MessageCallbackType']:
        async with self.bot.processing_context(reply, self.factory_name):
            callbacks: List[MessageCallback] = await self.instance.send_chain_message(reply, is_sync=True)

        if not callbacks:
            return None

        return callbacks if len(callbacks) > 1 else callbacks[0]

    async def recall(self):
        if self.message_id:
            await self.instance.recall_message(self.message_id, self)

    async def wait(
        self,
        reply=None,
        force: bool = False,
        max_time: int = 30,
        data_filter: Optional[Callable] = None,
        level: int = 0,
    ) -> WaitReturn:
        if self.is_direct:
            target_id = f'{self.instance.appid}_{self.guild_id}_{self.user_id}'
        else:
            target_id = f'{self.instance.appid}_{self.channel_id}_{self.user_id}'

        if reply:
            await self.send(reply)

        event: WaitEvent = await wait_events_bucket.set_event(target_id, force, False, level)
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

        return None

    async def wait_channel(
        self,
        reply=None,
        force: bool = False,
        clean: bool = True,
        max_time: int = 30,
        data_filter: Optional[Callable] = None,
        level: int = 0,
    ) -> WaitChannelReturn:
        if self.is_direct:
            raise WaitEventException('direct message not support "wait_channel"')

        target_id = f'{self.instance.appid}_{self.channel_id}'

        if reply:
            await self.send(reply)

        if target_id not in wait_events_bucket:
            event: ChannelWaitEvent = await wait_events_bucket.set_event(target_id, force, True, level)
            asyncio.create_task(event.timer(max_time))
        else:
            event: ChannelWaitEvent = wait_events_bucket[target_id]
            if event.check_alive():
                event.reset()
                if clean:
                    event.clean()
            else:
                event.cancel()
                event: ChannelWaitEvent = await wait_events_bucket.set_event(target_id, force, True, level)
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

        return None

    def copy(self):
        bot = self.bot
        instance = self.instance

        self.bot = None
        self.instance = None

        new_data = copy.deepcopy(self)
        new_data.bot = bot
        new_data.instance = instance

        self.bot = bot
        self.instance = instance

        return new_data


class MessageMatch:
    @staticmethod
    def check_str(data: Message, text: str, level: Optional[int] = None) -> MatchReturn:
        if text.lower() in data.text.lower():
            return True, level if level is not None else 1, text
        return False, 0, None

    @staticmethod
    def check_equal(data: Message, text: Equal, level: Optional[int] = None) -> MatchReturn:
        if text.content == data.text:
            return True, level if level is not None else float('inf'), text
        return False, 0, None

    @staticmethod
    def check_reg(data: Message, reg: re.Pattern, level: Optional[int] = None) -> MatchReturn:
        r = re.search(reg, data.text)
        if r:
            return (
                True,
                level if level is not None else (r.re.groups or 1),
                list(r.groups()),
            )
        return False, 0, None


class MessageCallback:
    def __init__(self, data: MessageStructure, instance: T_BotAdapterProtocol, response: Union[Response, Any]):
        self.data = data
        self.instance = instance
        self.response = response

    @abc.abstractmethod
    async def recall(self) -> None:
        """
        撤回本条消息

        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_message(self) -> Optional[Message]:
        """
        获取本条消息的 Message 对象

        :return:
        """
        raise NotImplementedError


Waiter = Union[WaitEvent, ChannelWaitEvent, None]
EventType = Union[Event, EventList]
MessageCallbackType = Union[MessageCallback, List[MessageCallback]]
