import re

from typing import Any, Type, List, Dict, Tuple, Union, Optional, Callable, Coroutine
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.message import Message, MessageMatch, Verify, Equal
from amiyabot.adapter import BotInstance

PREFIX = Union[bool, List[str]]
KEYWORDS = Union[str, Equal, re.Pattern, List[Union[str, Equal, re.Pattern]]]
FUNC_CORO = Callable[[Message], Coroutine[Any, Any, Optional[Chain]]]
AFTER_CORO = Callable[[Chain], Coroutine[Any, Any, None]]
BEFORE_CORO = Callable[[Message], Coroutine[Any, Any, bool]]
VERIFY_CORO = Callable[[Message], Coroutine[Any, Any, Union[bool, Tuple[bool, int]]]]
MIDDLE_WARE = Callable[[Message], Coroutine[Any, Any, Optional[Message]]]
EXCEPTION_CORO = Callable[[Exception, BotInstance], Coroutine[Any, Any, None]]


class BotHandlerFactory:
    def __init__(self, appid: str = None, token: str = None, create_instance: bool = True):
        self.instance: Optional[BotInstance] = None
        if create_instance:
            self.instance = BotInstance(appid, token)

        self.appid = appid
        self.prefix_keywords = list()
        self.message_handlers = list()
        self.exception_handlers: Dict[Type[Exception], List[EXCEPTION_CORO]] = dict()
        self.after_reply_handlers: List[AFTER_CORO] = list()
        self.before_reply_handlers: List[BEFORE_CORO] = list()
        self.message_handler_middleware: List[MIDDLE_WARE] = list()

    def on_message(self,
                   keywords: KEYWORDS = None,
                   verify: VERIFY_CORO = None,
                   check_prefix: PREFIX = True,
                   level: int = 0):
        """
        注册消息处理器

        :param keywords:      触发关键字
        :param verify:        自定义校验方法
        :param check_prefix:  是否校验前缀或指定需要校验的前缀
        :param level:         关键字校验成功后函数的候选默认等级
        :return:              注册函数的装饰器
        """

        def register(func: FUNC_CORO):
            _handler = MessageHandlerItem(func,
                                          level=level,
                                          check_prefix=check_prefix,
                                          prefix_keywords=self.prefix_keywords)
            if verify:
                _handler.custom_verify = verify
            else:
                _handler.keywords = keywords

            self.message_handlers.append(_handler)

        return register

    def on_exception(self, exceptions: Union[Type[Exception], List[Type[Exception]]] = Exception):
        """
        注册异常处理器，参数为异常类型或异常类型列表，在执行通过本实例注册的所有方法产生异常时会被调用

        :param exceptions: 异常类型或异常类型列表
        :return:           注册函数的装饰器
        """

        def handler(func: EXCEPTION_CORO):
            nonlocal exceptions
            if type(exceptions) is not list:
                exceptions = [exceptions]

            for item in exceptions:
                if item not in self.exception_handlers:
                    self.exception_handlers[item] = []

                self.exception_handlers[item].append(func)

        return handler

    def before_bot_reply(self, handler: BEFORE_CORO):
        """
        Bot 回复前处理，用于定义当 Bot 即将回复消息时的操作，该操作会在处理消息前执行

        :param handler: 处理函数
        :return:
        """
        self.before_reply_handlers.append(handler)

    def after_bot_reply(self, handler: AFTER_CORO):
        """
        Bot 回复后处理，用于定义当 Bot 回复消息后的操作，该操作会在发送消息后执行

        :param handler: 处理函数
        :return:
        """
        self.after_reply_handlers.append(handler)

    def handler_middleware(self, handler: MIDDLE_WARE):
        """
        Message 对象与消息处理器的中间件，用于对 Message 作进一步的客制化处理，允许存在多个，但会根据加载顺序叠加使用

        :param handler: 处理函数
        :return:
        """
        self.message_handler_middleware.append(handler)


class MessageHandlerItem:
    def __init__(self,
                 function: FUNC_CORO,
                 keywords: KEYWORDS = None,
                 check_prefix: PREFIX = True,
                 custom_verify: VERIFY_CORO = None,
                 prefix_keywords: List[str] = None,
                 level: int = 0):
        """
        处理器对象
        将注册到功能候选列表的功能处理器，提供给消息处理器（message_handler）筛选出功能轮候列表。
        不必主动实例化本类，请使用注册器注册功能函数。

        :param function:        功能函数
        :param keywords:        内置校验方法的关键字，支持字符串、正则、全等句（Equal）或由它们构成的列表
        :param check_prefix:    是否校验前缀或指定需要校验的前缀
        :param custom_verify:   自定义校验方法
        :param prefix_keywords: 初始的前缀校验关键词
        :param level:           关键字校验成功后函数的候选默认等级
        """
        self.function = function
        self.keywords = keywords
        self.check_prefix = check_prefix
        self.custom_verify = custom_verify
        self.prefix_keywords = prefix_keywords
        self.level = level

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
        # 检查是否包含前缀触发词，包括 @
        flag = False
        if self.check_prefix:
            if data.is_at:
                flag = True
            else:
                for word in (self.check_prefix if type(self.check_prefix) is list else self.prefix_keywords):
                    if data.text_origin.startswith(word):
                        flag = True
                        break

        # 若不包含前缀触发词，且关键字不为全等句式（Equal）
        # 则允许当关键字为列表时，筛选列表内的全等句式继续执行校验
        if self.check_prefix and not flag and not type(self.keywords) is Equal:
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
