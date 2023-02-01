import re

from typing import Any, Type, Dict, List, Tuple, Union, Optional, Callable, Coroutine
from dataclasses import dataclass
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.message import Event, Message, MessageMatch, Verify, Equal
from amiyabot.adapters import BotAdapterProtocol

KeywordsType = Union[str, Equal, re.Pattern, List[Union[str, Equal, re.Pattern]]]
FunctionType = Callable[[Message], Coroutine[Any, Any, Optional[Chain]]]
CheckPrefixType = Optional[Union[bool, List[str]]]
VerifyMethodType = Callable[[Message], Coroutine[Any, Any, Union[bool, Tuple[bool, int], Tuple[bool, int, Any]]]]
EventHandlerType = Callable[[Event, BotAdapterProtocol], Coroutine[Any, Any, None]]
ExceptionHandlerType = Callable[[Exception, BotAdapterProtocol, Union[Message, Event]], Coroutine[Any, Any, None]]
AfterReplyHandlerType = Callable[[Optional[Chain], str], Coroutine[Any, Any, None]]
BeforeReplyHandlerType = Callable[[Message, str], Coroutine[Any, Any, bool]]
MessageHandlerMiddlewareType = Callable[[Message], Coroutine[Any, Any, Optional[Message]]]


@dataclass
class GroupConfig:
    group_id: str
    check_prefix: bool = True
    allow_direct: bool = False
    direct_only: bool = False

    def __str__(self):
        return self.group_id


@dataclass
class MessageHandlerItem:
    function: FunctionType
    prefix_keywords: Callable[[], List[str]]

    group_id: str = None
    group_config: GroupConfig = None
    keywords: KeywordsType = None
    allow_direct: Optional[bool] = None
    direct_only: bool = False
    check_prefix: CheckPrefixType = None
    custom_verify: VerifyMethodType = None
    level: int = 0

    def __repr__(self):
        return f'<MessageHandlerItem, {self.custom_verify or self.keywords}>'

    def __check(self, data: Message, obj: KeywordsType) -> Verify:
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
        direct_only = self.direct_only or (self.group_config and self.group_config.direct_only)

        if self.check_prefix is None:
            if self.group_config:
                need_check_prefix = self.group_config and self.group_config.check_prefix
            else:
                need_check_prefix = True
        else:
            need_check_prefix = self.check_prefix

        if data.is_direct:
            if not direct_only:
                # 检查是否支持私信
                if self.allow_direct is None:
                    if not self.group_config or not self.group_config.allow_direct:
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
                prefix_keywords = need_check_prefix if type(need_check_prefix) is list else self.prefix_keywords()

                # 未设置前缀触发词允许直接通过
                if not prefix_keywords:
                    flag = True

                for word in prefix_keywords:
                    if data.text.startswith(word):
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
                result = result, int(bool(result)), None

            elif type(result) is tuple:
                contrast = bool(result[0]), int(bool(result[0])), None
                result = (result + contrast[len(result):])[:3]

            return Verify(*result)

        return self.__check(data, self.keywords)

    async def action(self, data: Message):
        return await self.function(data)


PrefixKeywords = List[str]
EventHandlers = Dict[str, List[EventHandlerType]]
MessageHandlers = List[MessageHandlerItem]
ExceptionHandlers = Dict[Type[Exception], List[ExceptionHandlerType]]
AfterReplyHandlers = List[AfterReplyHandlerType]
BeforeReplyHandlers = List[BeforeReplyHandlerType]
MessageHandlerMiddleware = List[MessageHandlerMiddlewareType]
HandlersIDMap = Dict[int, str]
