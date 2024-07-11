import os

from typing import Dict
from amiyabot.builtin.message import *
from amiyabot.builtin.messageChain import Chain
from amiyabot.factory import MessageHandlerItem, BotHandlerFactory, EventHandlerType
from amiyabot.log.manager import LoggerManager, LOG_FILE_SAVE_PATH

ChoiceRes = Union[MessageHandlerItem, Waiter]

adapter_log: Dict[str, LoggerManager] = {}


async def message_handler(bot: BotHandlerFactory, data: Union[Message, Event, EventList]):
    appid = str(bot.appid)
    instance = bot.instance

    if appid not in adapter_log:
        adapter_log[appid] = LoggerManager(
            name=str(instance),
            save_path=os.path.join(LOG_FILE_SAVE_PATH, 'bots'),
            save_filename=appid,
        )

    _log = adapter_log[appid]

    # 执行事件响应
    if not isinstance(data, Message):
        # todo 生命周期 - event_created
        for method in bot.process_event_created:
            data = await method(data, instance) or data

        await event_handler(bot, data, _log)
        return None

    _log.info(
        data.__str__(),
        extra={
            'message_data': data,
        },
    )

    data.bot = bot

    # todo 生命周期 - message_created
    for method in bot.process_message_created:
        method_ret = await method(data, instance)

        if method_ret is False:
            return None

        if method_ret is not None:
            data = method_ret

    # 检查是否存在等待事件
    waiter = await find_wait_event(data)

    # 若存在等待事件并且等待事件设置了强制等待，则直接进入事件
    if waiter and waiter.force:
        # todo 生命周期 - message_before_waiter_set(1)
        for method in bot.process_message_before_waiter_set:
            data = await method(data, waiter, instance) or data

        waiter.set(data)
        return None

    # 选择功能或等待事件
    handler = await choice_handlers(data, bot.message_handlers, waiter)
    if not handler:
        return

    if isinstance(handler, MessageHandlerItem):
        factory_name = bot.message_handler_id_map[id(handler.function)]

        data.factory_name = factory_name

        # todo 生命周期 - message_before_handle
        flag = True
        for method in bot.process_message_before_handle:
            res = await method(data, factory_name, instance)
            if res is False:
                flag = False
        if not flag:
            return None

        # 执行功能，并取消存在的等待事件
        reply = await handler.action(data)
        if reply:
            if waiter and waiter.type == 'user':
                waiter.cancel()

            if isinstance(reply, str):
                reply = Chain(data, at=False).text(reply)

            await data.send(reply)

        # todo 生命周期 - message_after_handle
        for method in bot.process_message_after_handle:
            await method(reply, factory_name, instance)

        return None

    if isinstance(handler, WaitEvent):
        # todo 生命周期 - message_before_waiter_set(2)
        for method in bot.process_message_before_waiter_set:
            data = await method(data, handler, instance) or data

        handler.set(data)


async def event_handler(bot: BotHandlerFactory, data: Union[Event, EventList], _log: LoggerManager):
    methods = []
    if '__all_event__' in bot.event_handlers:
        methods += bot.event_handlers['__all_event__']

    if isinstance(data, Event):
        data = EventList([data])

    for item in data:
        sub_methods: List[EventHandlerType] = [*methods]

        if item.event_name in bot.event_handlers:
            sub_methods += bot.event_handlers[item.event_name]

        if sub_methods:
            _log.info(item.__str__())

            for method in sub_methods:
                async with _log.catch('event handler error:'):
                    await method(item, bot.instance)


async def choice_handlers(data: Message, handlers: List[MessageHandlerItem], waiter: Waiter) -> Optional[ChoiceRes]:
    candidate: List[Tuple[Verify, ChoiceRes]] = []

    if waiter:
        candidate.append((Verify(True, waiter.level), waiter))

    for item in handlers:
        check = await item.verify(data.copy())
        if check:
            candidate.append((check, item))

    if not candidate:
        return None

    # 选择排序第一的结果
    _sorted = sorted(candidate, key=lambda n: n[0].weight, reverse=True)
    selected = _sorted[0]

    # 将 Verify 结果赋值给 Message
    data.verify = selected[0]
    if data.verify.on_selected:
        data.verify.on_selected()

    return selected[1]


async def find_wait_event(data: Message) -> Waiter:
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
