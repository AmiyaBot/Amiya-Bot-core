import re
import abc

from typing import Any, Type, Dict, List, Tuple, Union, Optional, Callable, Coroutine
from dataclasses import dataclass
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.message import Event, Message, Equal
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

    @abc.abstractmethod
    async def verify(self, data: Message):
        raise NotImplementedError

    @abc.abstractmethod
    async def action(self, data: Message):
        raise NotImplementedError


PrefixKeywords = List[str]
EventHandlers = Dict[str, List[EventHandlerType]]
MessageHandlers = List[MessageHandlerItem]
ExceptionHandlers = Dict[Type[Exception], List[ExceptionHandlerType]]
MessageHandlersIDMap = Dict[int, str]

AfterReplyHandlers = List[AfterReplyHandlerType]
BeforeReplyHandlers = List[BeforeReplyHandlerType]
MessageHandlerMiddleware = List[MessageHandlerMiddlewareType]
