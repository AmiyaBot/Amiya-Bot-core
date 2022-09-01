import re

from typing import Any, Dict, List, Tuple, Union, Optional, Callable, Coroutine
from dataclasses import dataclass, field
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.message import Event, Message, MessageMatch, Verify, Equal
from amiyabot.adapters import BotAdapterProtocol

PREFIX = Optional[Union[bool, List[str]]]
KEYWORDS = Union[str, Equal, re.Pattern, List[Union[str, Equal, re.Pattern]]]
FUNC_CORO = Callable[[Message], Coroutine[Any, Any, Optional[Chain]]]
EVENT_CORO = Callable[[Event, BotAdapterProtocol], Coroutine[Any, Any, None]]
AFTER_CORO = Callable[[Chain], Coroutine[Any, Any, None]]
BEFORE_CORO = Callable[[Message], Coroutine[Any, Any, bool]]
VERIFY_CORO = Callable[[Message], Coroutine[Any, Any, Union[bool, Tuple[bool, int]]]]
MIDDLE_WARE = Callable[[Message], Coroutine[Any, Any, Optional[Message]]]
EXCEPTION_CORO = Callable[[Exception, BotAdapterProtocol], Coroutine[Any, Any, None]]


@dataclass
class GroupConfig:
    group_id: str
    check_prefix: bool = True
    allow_direct: bool = False
    direct_only: bool = False


@dataclass
class GroupConfigManager:
    config: Dict[str, GroupConfig] = field(default_factory=dict)

    def get_config(self, config_id: str):
        return self.config.get(config_id, None) if config_id else None


@dataclass
class MessageHandlerItem:
    function: FUNC_CORO
    group_config: GroupConfigManager
    group_id: str = None
    keywords: KEYWORDS = None
    allow_direct: Optional[bool] = None
    direct_only: bool = False
    check_prefix: PREFIX = None
    custom_verify: VERIFY_CORO = None
    prefix_keywords: List[str] = None
    level: int = 0

    def __repr__(self):
        return f'<MessageHandlerItem, {self.custom_verify or self.keywords}>'

    def __check(self, data: Message, obj: KEYWORDS) -> Verify:
        methods = {
            str: MessageMatch.check_str,
            Equal: MessageMatch.check_equal,
            re.Pattern: MessageMatch.check_reg
        }
        t = type(obj)

        if t in methods.keys():
            method = methods[t]
            check = Verify(*method(data, obj, self.level))
            if check:
                return check

        elif t is list:
            for item in obj:
                check = self.__check(data, item)
                if check:
                    return check

        return Verify(False)

    async def verify(self, data: Message):
        group_config = self.group_config.get_config(self.group_id)

        direct_only = self.direct_only or (group_config and group_config.direct_only)

        if self.check_prefix is None:
            if group_config:
                need_check_prefix = group_config and group_config.check_prefix
            else:
                need_check_prefix = True
        else:
            need_check_prefix = self.check_prefix

        if data.is_direct:
            if not direct_only:

                # 检查是否支持私信
                if self.allow_direct is None:
                    if not group_config or not group_config.allow_direct:
                        return Verify(False)

                if self.allow_direct is False:
                    return Verify(False)

        else:

            # 是否仅支持私信
            if direct_only:
                return Verify(False)

            # 检查是否包含“前缀触发词”或被 @
            flag = False
            if need_check_prefix:
                if data.is_at:
                    flag = True
                else:
                    for word in (need_check_prefix if type(need_check_prefix) is list else self.prefix_keywords):
                        if data.text_origin.startswith(word):
                            flag = True
                            break

            # 若不通过以上检查，且关键字不为全等句式（Equal）
            # 则允许当关键字为列表时，筛选列表内的全等句式继续执行校验，否则校验不通过
            if need_check_prefix and not flag and not type(self.keywords) is Equal:
                equal_filter = [n for n in self.keywords if type(n) is Equal] if type(self.keywords) is list else []
                if equal_filter:
                    self.keywords = equal_filter
                else:
                    return Verify(False)

        # 执行自定义校验并修正其返回值
        if self.custom_verify:
            result = await self.custom_verify(data)

            if type(result) is bool or result is None:
                result = result, int(bool(result))

            elif type(result) is tuple:
                contrast = bool(result[0]), int(bool(result[0]))
                result = (result + contrast[len(result):])[:2]

            return Verify(*result)

        return self.__check(data, self.keywords)

    async def action(self, data: Message):
        return await self.function(data)
