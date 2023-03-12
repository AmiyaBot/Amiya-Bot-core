from itertools import chain

from amiyabot.factory.factoryTyping import *


class FactoryContainer:
    def __init__(self):
        self.__container: Dict[str, Union[dict, list]] = {
            'prefix_keywords': list(),

            'event_handlers': dict(),
            'message_handlers': list(),
            'exception_handlers': dict(),

            'message_handler_id_map': dict(),

            'after_reply_handlers': list(),
            'before_reply_handlers': list(),
            'message_handler_middleware': list(),

            'group_config': dict(),
        }

        self.plugins = dict()

    def get_container(self, key: str) -> Union[dict, list]:
        return self.__container[key]

    def get_with_plugins(self, attr: str):
        self_attr = self.get_container(attr)
        attr_type = type(self_attr)

        if attr_type is list:
            return self_attr + list(
                chain(
                    *(plugin.get_container(attr) for _, plugin in self.plugins.items())
                )
            )
        elif attr_type is dict:
            value = {**self_attr}
            for _, plugin in self.plugins.items():
                plugin_value: Union[dict, list] = plugin.get_container(attr)
                for k in plugin_value:
                    if k not in value:
                        value[k] = plugin_value[k]
                    else:
                        value[k] += plugin_value[k]

                    if type(value[k]) is list:
                        value[k] = list(set(value[k]))

            return value


class ProcessControl(FactoryContainer):
    def __init__(self):
        super().__init__()

        # 事件处理生命周期
        # self._event_created = list()

        # 消息处理生命周期
        # self._message_created = list()
        # self._message_before_waiter_set = list()
        # self._message_before_handle = list()
        # self._message_before_send = list()
        # self._message_after_send = list()

    @property
    def after_reply_handlers(self) -> AfterReplyHandlers:
        return self.get_with_plugins('after_reply_handlers')

    @property
    def before_reply_handlers(self) -> BeforeReplyHandlers:
        return self.get_with_plugins('before_reply_handlers')

    @property
    def message_handler_middleware(self) -> MessageHandlerMiddleware:
        return self.get_with_plugins('message_handler_middleware')

    def before_bot_reply(self, handler: BeforeReplyHandlerType):
        """
        Bot 回复前处理，用于定义当 Bot 即将回复消息时的操作，该操作会在处理消息前执行

        :param handler: 处理函数
        :return:
        """
        self.get_container('before_reply_handlers').append(handler)

        return handler

    def after_bot_reply(self, handler: AfterReplyHandlerType):
        """
        Bot 回复后处理，用于定义当 Bot 回复消息后的操作，该操作会在发送消息后执行

        :param handler: 处理函数
        :return:
        """
        self.get_container('after_reply_handlers').append(handler)

        return handler

    def handler_middleware(self, handler: MessageHandlerMiddlewareType):
        """
        Message 对象与消息处理器的中间件，用于对 Message 作进一步的客制化处理，允许存在多个，但会根据加载顺序叠加使用

        :param handler: 处理函数
        :return:
        """
        self.get_container('message_handler_middleware').append(handler)

        return handler
