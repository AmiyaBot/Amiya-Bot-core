import inspect

from itertools import chain
from amiyabot.factory.factoryTyping import *


class FactoryCore:
    def __init__(self):
        self.__container: Dict[str, Union[dict, list]] = {
            # 触发词
            'prefix_keywords': list(),

            # 响应器
            'event_handlers': dict(),
            'message_handlers': list(),
            'exception_handlers': dict(),

            # 消息响应器 ID 字典
            'message_handler_id_map': dict(),

            # 生命周期
            'process_event_created': list(),
            'process_message_created': list(),
            'process_message_before_waiter_set': list(),
            'process_message_before_handle': list(),
            'process_message_before_send': list(),
            'process_message_after_send': list(),
            'process_message_after_handle': list(),

            # 组设置
            'group_config': dict(),
        }

        self.plugins: Dict[str, FactoryCore] = dict()

        self.factory_name = 'default_factory'

    def get_container(self, key: str) -> Union[dict, list]:
        return self.__container[key]

    def get_with_plugins(self, attr_name: str = None):
        if not attr_name:
            attr_name = inspect.getframeinfo(inspect.currentframe().f_back)[2]

        self_attr = self.get_container(attr_name)
        attr_type = type(self_attr)

        if attr_type is list:
            return self_attr + list(
                chain(
                    *(getattr(plugin, attr_name) for _, plugin in self.plugins.items())
                )
            )

        if attr_type is dict:
            value = {**self_attr}
            for _, plugin in self.plugins.items():
                plugin_value: Union[dict, list] = getattr(plugin, attr_name)
                for k in plugin_value:
                    if k not in value:
                        value[k] = plugin_value[k]
                    else:
                        value[k] += plugin_value[k]

                    if isinstance(value[k], list):
                        value[k] = list(set(value[k]))

            return value

    @property
    def process_event_created(self) -> EventCreatedHandlers:
        return self.get_with_plugins()

    @property
    def process_message_created(self) -> MessageCreatedHandlers:
        return self.get_with_plugins()

    @property
    def process_message_before_waiter_set(self) -> BeforeWaiterSetHandlers:
        return self.get_with_plugins()

    @property
    def process_message_before_handle(self) -> BeforeHandleHandlers:
        return self.get_with_plugins()

    @property
    def process_message_before_send(self) -> BeforeSendHandlers:
        return self.get_with_plugins()

    @property
    def process_message_after_send(self) -> AfterSendHandlers:
        return self.get_with_plugins()

    @property
    def process_message_after_handle(self) -> AfterHandleHandlers:
        return self.get_with_plugins()

    def event_created(self, handler: EventCreatedHandlerType):
        self.get_container('process_event_created').append(handler)
        return handler

    def message_created(self, handler: MessageCreatedHandlerType):
        self.get_container('process_message_created').append(handler)
        return handler

    def message_before_waiter_set(self, handler: BeforeWaiterSetHandlerType):
        self.get_container('process_message_before_waiter_set').append(handler)
        return handler

    def message_before_handle(self, handler: BeforeHandleHandlerType):
        self.get_container('process_message_before_handle').append(handler)
        return handler

    def message_before_send(self, handler: BeforeSendHandlerType):
        self.get_container('process_message_before_send').append(handler)
        return handler

    def message_after_send(self, handler: AfterSendHandlerType):
        self.get_container('process_message_after_send').append(handler)
        return handler

    def message_after_handle(self, handler: AfterHandleHandlerType):
        self.get_container('process_message_after_handle').append(handler)
        return handler
