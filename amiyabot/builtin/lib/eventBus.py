import asyncio
import inspect

from typing import Any, Dict, Union, Optional, Callable, Coroutine

Subscriber = Callable[[Optional[Any]], Union[Coroutine[Any, Any, None], None]]
SubscriberID = int
EventName = str


class EventBus:
    def __init__(self):
        self.__subscriber: Dict[EventName, Dict[SubscriberID, Subscriber]] = dict()

    def publish(self, event_name: EventName, data: Optional[Any] = None):
        if event_name in self.__subscriber:
            for _, method in self.__subscriber[event_name].items():
                if inspect.iscoroutinefunction(method):
                    asyncio.create_task(method(data))
                else:
                    method(data)

    def subscribe(self, event_name: EventName, method: Optional[Subscriber] = None):
        if event_name not in self.__subscriber:
            self.__subscriber[event_name] = dict()

        if method:
            self.__subscriber[event_name][id(method)] = method
            return

        def register(func: Subscriber):
            self.__subscriber[event_name][id(func)] = func

            return func

        return register

    def unsubscribe(self, event_name: EventName, method: Subscriber):
        if event_name in self.__subscriber:
            method_id = id(method)
            if method_id in self.__subscriber[event_name]:
                del self.__subscriber[event_name][method_id]


event_bus = EventBus()
