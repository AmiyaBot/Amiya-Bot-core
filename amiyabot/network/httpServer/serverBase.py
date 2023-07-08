import asyncio
import uvicorn

from typing import List, Callable
from pydantic import BaseModel
from amiyabot.log import LoggerManager


class ServerLog:
    logger = LoggerManager('Server', save_filename='server')

    @classmethod
    def write(cls, text: str):
        cls.logger.info(text)


class ServerEventHandler:
    on_shutdown: List[Callable] = []


class ServerMeta(type):
    servers: List[uvicorn.Server] = []
    shutdown_lock = False

    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)

        cls.servers.append(instance.server)

        return instance

    def shutdown_all(cls, server: uvicorn.Server):
        if not cls.shutdown_lock:
            cls.shutdown_lock = True

            for item in cls.servers:
                if item != server:
                    item.should_exit = True

            for action in ServerEventHandler.on_shutdown:
                asyncio.create_task(action())
