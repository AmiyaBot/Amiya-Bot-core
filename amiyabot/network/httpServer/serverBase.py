import uvicorn
import pydantic

from typing import List
from amiyabot.log import LoggerManager
from amiyabot.signalHandler import SignalHandler

BaseModel = pydantic.BaseModel


class ServerLog:
    logger = LoggerManager('Server', save_filename='server')

    @classmethod
    def write(cls, text: str):
        cls.logger.info(text)


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

            SignalHandler.exec_shutdown_handlers()


LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'access': {
            '()': 'uvicorn.logging.AccessFormatter',
            'fmt': '%(client_addr)s - %(request_line)s %(status_code)s',
        },
        'default': {
            '()': 'uvicorn.logging.DefaultFormatter',
            'fmt': '%(message)s',
            'use_colors': None,
        },
    },
    'handlers': {
        'access': {
            'class': 'logging.StreamHandler',
            'formatter': 'access',
            'stream': 'ext://amiyabot.network.httpServer.ServerLog',
        },
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://amiyabot.network.httpServer.ServerLog',
        },
    },
    'loggers': {
        'uvicorn': {'handlers': ['default'], 'level': 'INFO'},
        'uvicorn.access': {'handlers': ['access'], 'level': 'INFO', 'propagate': False},
        'uvicorn.error': {'level': 'INFO'},
    },
}
