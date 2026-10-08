import signal
import inspect
import asyncio
import threading

from typing import List, Callable


class SignalHandler:
    on_shutdown: List[Callable] = []

    _registered = False

    @classmethod
    def exec_shutdown_handlers(cls):
        for action in cls.on_shutdown:
            if inspect.iscoroutinefunction(action):
                asyncio.create_task(action())
            else:
                action()

    @classmethod
    def register(cls):
        """
        注册关停信号处理（SIGINT / SIGTERM），幂等。

        注意：signal.signal 只能在主线程调用，故此处做线程守卫，
        避免在非主线程 import 本模块时抛出 ValueError。
        """
        if cls._registered:
            return

        if threading.current_thread() is not threading.main_thread():
            return

        cls._registered = True

        signal.signal(signal.SIGINT, cls._shutdown_handler)
        signal.signal(signal.SIGTERM, cls._shutdown_handler)

    @staticmethod
    def _shutdown_handler(*args):
        SignalHandler.exec_shutdown_handlers()
        # sys.exit(0)
