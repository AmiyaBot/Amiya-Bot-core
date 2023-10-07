import re
import abc

from typing import Any, Type, Dict, List, Tuple, Union, Optional, Callable, Awaitable
from dataclasses import dataclass
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.message import EventType, Message, Equal, Waiter, Verify
from amiyabot.adapters import BotAdapterProtocol

KeywordsType = Union[str, Equal, re.Pattern, List[Union[str, Equal, re.Pattern]]]
CheckPrefixType = Optional[Union[bool, List[str]]]

NoneReturn = Awaitable[None]
BoolReturn = Awaitable[Optional[bool]]
ChainReturn = Awaitable[Optional[Chain]]
EventReturn = Awaitable[Optional[EventType]]
MessageReturn = Awaitable[Optional[Message]]
MessageOrBoolReturn = Awaitable[Optional[Union[Message, bool]]]
VerifyResultReturn = Awaitable[Union[bool, Tuple[bool, int], Tuple[bool, int, Any]]]

FunctionType = Callable[[Message], ChainReturn]
VerifyMethodType = Callable[[Message], VerifyResultReturn]
EventHandlerType = Callable[[EventType, BotAdapterProtocol], NoneReturn]
ExceptionHandlerType = Callable[[Exception, BotAdapterProtocol, Union[Message, EventType]], NoneReturn]

EventCreatedHandlerType = Callable[[EventType, BotAdapterProtocol], EventReturn]
MessageCreatedHandlerType = Callable[[Message, BotAdapterProtocol], MessageOrBoolReturn]
BeforeWaiterSetHandlerType = Callable[[Message, Waiter, BotAdapterProtocol], MessageReturn]
BeforeHandleHandlerType = Callable[[Message, str, BotAdapterProtocol], BoolReturn]
BeforeSendHandlerType = Callable[[Chain, str, BotAdapterProtocol], ChainReturn]
AfterSendHandlerType = Callable[[Chain, str, BotAdapterProtocol], NoneReturn]
AfterHandleHandlerType = Callable[[Optional[Chain], str, BotAdapterProtocol], NoneReturn]


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

    group_id: Optional[str] = None
    group_config: Optional[GroupConfig] = None
    keywords: Optional[KeywordsType] = None
    allow_direct: Optional[bool] = None
    direct_only: bool = False
    check_prefix: Optional[CheckPrefixType] = None
    custom_verify: Optional[VerifyMethodType] = None
    level: Optional[int] = None

    def __repr__(self):
        return f'<MessageHandlerItem, {self.custom_verify or self.keywords}>'

    @abc.abstractmethod
    async def verify(self, data: Message) -> Verify:
        raise NotImplementedError

    @abc.abstractmethod
    async def action(self, data: Message) -> Optional[Union[Chain, str]]:
        raise NotImplementedError


PrefixKeywords = List[str]
EventHandlers = Dict[str, List[EventHandlerType]]
MessageHandlers = List[MessageHandlerItem]
ExceptionHandlers = Dict[Type[Exception], List[ExceptionHandlerType]]
MessageHandlersIDMap = Dict[int, str]

EventCreatedHandlers = List[EventCreatedHandlerType]
MessageCreatedHandlers = List[MessageCreatedHandlerType]
BeforeWaiterSetHandlers = List[BeforeWaiterSetHandlerType]
BeforeHandleHandlers = List[BeforeHandleHandlerType]
BeforeSendHandlers = List[BeforeSendHandlerType]
AfterSendHandlers = List[AfterSendHandlerType]
AfterHandleHandlers = List[AfterHandleHandlerType]
