import qqbot

from typing import List, Tuple, Union, Optional
from qqbot.model.ws_context import WsContext
from amiyabot.builtin.message.builder import package_message
from amiyabot.builtin.message import Message, Verify, WaitEvent, ChannelWaitEvent, WaitEventCancel, wait_events_bucket
from amiyabot.handler import MessageHandlerItem, BotHandlerFactory

CHOICE = Optional[Tuple[Verify, MessageHandlerItem]]


async def message_handler(bot: BotHandlerFactory, event: WsContext, message: qqbot.Message):
    instance = bot.instance
    data = await package_message(instance, event, message)

    if not data:
        return None

    # 执行中间处理函数
    if bot.message_handler_middleware:
        for middleware in bot.message_handler_middleware:
            data = await middleware(data) or data

    waiter: Union[WaitEvent, ChannelWaitEvent, None] = None

    channel_waiter = None
    if data.channel_id:
        user_waiter = f'{instance.appid}_{data.channel_id}_{data.user_id}'
        channel_waiter = f'{instance.appid}_{data.channel_id}'
    else:
        user_waiter = f'{instance.appid}_{data.user_id}'

    # 寻找是否存在等待事件
    if user_waiter in wait_events_bucket:
        waiter = wait_events_bucket[user_waiter]
    if channel_waiter and channel_waiter in wait_events_bucket:
        waiter = wait_events_bucket[channel_waiter]

    # 检查等待事件是否活跃
    try:
        if waiter and not waiter.check_alive():
            waiter = None
    except WaitEventCancel:
        waiter = None

    # 若存在等待事件并且等待事件设置了强制等待，则直接进入事件
    if waiter and waiter.force:
        waiter.set(data)
        return None

    choice = await choice_handlers(data, bot.message_handlers)
    if choice:
        handler = choice[1]

        # 执行前置处理函数
        flag = True
        if bot.before_reply_handlers:
            for action in bot.before_reply_handlers:
                res = await action(data)
                if not res:
                    flag = False
        if not flag:
            return None

        # 执行功能，若存在等待事件，则取消
        reply = await handler.action(data)
        if reply:
            if waiter and waiter.type == 'user':
                waiter.cancel()
            await data.send(reply)

            # 执行后置处理函数
            if bot.after_reply_handlers:
                for action in bot.after_reply_handlers:
                    await action(reply)

            return None

    # 未选中任何功能或功能无法返回时，进入等待事件（若存在）
    if waiter:
        waiter.set(data)


async def choice_handlers(data: Message, handlers: List[MessageHandlerItem]) -> CHOICE:
    candidate: List[Tuple[Verify, MessageHandlerItem]] = []

    for item in handlers:
        check = await item.verify(data)
        if check:
            candidate.append((check, item))

    if not candidate:
        return None

    return sorted(candidate, key=lambda n: len(n[0]), reverse=True)[0]
