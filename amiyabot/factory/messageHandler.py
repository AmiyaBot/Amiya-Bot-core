from typing import Dict, Union, Optional

from amiyabot.builtin.message import *
from amiyabot.factory import MessageHandlerItem, BotHandlerFactory, EventHandlerType
from amiyabot.log import LoggerManager

CHOICE = Optional[Tuple[Verify, MessageHandlerItem]]

adapter_log: Dict[str, LoggerManager] = {}


async def message_handler(bot: BotHandlerFactory, data: Union[Message, Event, EventList]):
    instance_name = str(bot.instance)
    if instance_name not in adapter_log:
        adapter_log[instance_name] = LoggerManager(name=instance_name)

    _log = adapter_log[instance_name]

    # 执行事件响应
    if type(data) is not Message:
        await event_handler(bot, data, _log)
        return None

    _log.info(data.__str__())

    # 执行中间处理函数
    if bot.message_handler_middleware:
        for middleware in bot.message_handler_middleware:
            data = await middleware(data) or data

    # 检查是否存在等待事件
    waiter = await find_wait_event(data)

    # 若存在等待事件并且等待事件设置了强制等待，则直接进入事件
    if waiter and waiter.force:
        waiter.set(data)
        return None

    # 选择功能
    choice = await choice_handlers(data, bot.message_handlers)
    if choice:
        handler = choice[1]
        factory_name = bot.handlers_id_map[id(handler.function)]

        # 执行前置处理函数
        flag = True
        if bot.before_reply_handlers:
            for action in bot.before_reply_handlers:
                res = await action(data, factory_name)
                if res is False:
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
                    await action(reply, factory_name)

            return None

    # 未选中任何功能或功能无法返回时，进入等待事件（若存在）
    if waiter:
        waiter.set(data)


async def event_handler(bot: BotHandlerFactory, data: Union[Event, EventList], _log: LoggerManager):
    methods = []
    if '__all_event__' in bot.event_handlers:
        methods += bot.event_handlers['__all_event__']

    if type(data) is Event:
        data = EventList([data])

    for item in data:
        sub_methods: List[EventHandlerType] = [*methods]

        if item.event_name in bot.event_handlers:
            sub_methods += bot.event_handlers[item.event_name]

        if sub_methods:
            _log.info(f'{item.__str__()} Handlers: {len(sub_methods)}')

            for method in sub_methods:
                async with _log.catch('event handler error:'):
                    await method(item, bot.instance)


async def choice_handlers(data: Message, handlers: List[MessageHandlerItem]) -> CHOICE:
    candidate: List[Tuple[Verify, MessageHandlerItem]] = []

    for item in handlers:
        check = await item.verify(data)
        if check:
            candidate.append((check, item))

    if not candidate:
        return None

    # 选择排序第一的结果
    selected = sorted(candidate, key=lambda n: len(n[0]), reverse=True)[0]

    # 将 Verify 结果赋值给 Message
    data.verify = selected[0]

    return selected


async def find_wait_event(data: Message) -> Union[WaitEvent, ChannelWaitEvent, None]:
    waiter = None

    if data.is_direct:
        # 私信等待事件
        target_id = f'{data.instance.appid}_{data.guild_id}_{data.user_id}'
        if target_id in wait_events_bucket:
            waiter = wait_events_bucket[target_id]
    else:
        # 子频道用户等待事件
        target_id = f'{data.instance.appid}_{data.channel_id}_{data.user_id}'
        if target_id in wait_events_bucket:
            waiter = wait_events_bucket[target_id]

        # 子频道全体等待事件
        channel_target_id = f'{data.instance.appid}_{data.channel_id}'
        if channel_target_id in wait_events_bucket:
            channel_waiter = wait_events_bucket[channel_target_id]

            # 如果没有用户事件或全体事件是强制等待的，则覆盖
            if not waiter or channel_waiter.force:
                waiter = channel_waiter

    # 检查等待事件是否活跃
    try:
        if waiter and not waiter.check_alive():
            waiter = None
    except WaitEventCancel:
        waiter = None

    return waiter
