import re
import asyncio

from typing import Callable, List, Tuple, Any
from dataclasses import dataclass

from .callback import MessageCallback
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


@dataclass
class Equal:
    content: str


class Event(EventStructure):
    ...


class Message(MessageStructure):
    async def send(self, reply):
        callbacks: List[MessageCallback] = await self.instance.send_chain_message(reply, use_http=True)

        if not callbacks:
            return None

        return callbacks if len(callbacks) > 1 else callbacks[0]

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

    async def recall(self):
        if self.message_id:
            await self.instance.recall_message(self.message_id, self.channel_id or self.user_id)


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
            return True, level or (r.re.groups or 1), [item for item in r.groups()]
        return False, 0, None
