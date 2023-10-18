import signal
import inspect
import asyncio

from typing import List, Callable


class SignalHandler:
    on_shutdown: List[Callable] = []

    @classmethod
    def exec_shutdown_handlers(cls):
        for action in cls.on_shutdown:
            if inspect.iscoroutinefunction(action):
                asyncio.create_task(action())
            else:
                action()


def sigint_handler(*args):
    SignalHandler.exec_shutdown_handlers()
    # sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)
