import os
import sys
import logging
import traceback

from typing import Union, Dict, List, Type, Any, Callable, Coroutine
from contextlib import asynccontextmanager, contextmanager
from concurrent_log_handler import ConcurrentRotatingFileHandler


class UserLogger:
    logger: Any = None


class LoggerManager:
    def __init__(self,
                 name: str,
                 level: int = logging.DEBUG,
                 formatter: str = '%(asctime)s [%(name)8s][%(levelname)8s] %(message)s',
                 save_path: str = 'log',
                 default_file: str = 'running'):

        self.handlers: Dict[str, logging.Logger] = {}

        self.name = name
        self.level = level
        self.formatter = formatter
        self.save_path = save_path
        self.default_file = default_file

    def __handler(self, filename: str):
        if UserLogger.logger:
            return UserLogger.logger

        if not filename:
            filename = self.default_file

        if filename not in self.handlers:
            if not os.path.exists(self.save_path):
                os.makedirs(self.save_path)

            formatter = logging.Formatter(self.formatter)

            file_handler = ConcurrentRotatingFileHandler(
                filename=f'{self.save_path}/{filename}.log',
                encoding='utf-8',
                maxBytes=512 * 1024,
                backupCount=10
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(self.level)

            stream_handler = logging.StreamHandler(stream=sys.stdout)
            stream_handler.setFormatter(formatter)
            stream_handler.setLevel(self.level)

            logger = logging.getLogger(name=self.name)
            logger.setLevel(self.level)

            if not logger.handlers:
                logger.addHandler(file_handler)
                logger.addHandler(stream_handler)

            self.handlers[filename] = logger

        return self.handlers[filename]

    def debug(self, message: str, filename: str = None):
        self.__handler(filename).debug(message.strip('\n'))

    def info(self, message: str, filename: str = None):
        self.__handler(filename).info(message.strip('\n'))

    def warning(self, message: str, filename: str = None):
        self.__handler(filename).warning(message.strip('\n'))

    def error(self, message: Union[str, Exception], desc: str = None, filename: str = None):
        handler = self.__handler(filename)

        text = message

        if isinstance(message, Exception):
            text = traceback.format_exc()
        if desc:
            text = f'{desc} {text}'

        handler.error(text.strip('\n'))

        return text

    def critical(self, message: str, filename: str = None):
        self.__handler(filename).critical(message.strip('\n'))

    @asynccontextmanager
    async def catch(self,
                    desc: str = None,
                    ignore: List[Union[Type[Exception], Type[BaseException]]] = None,
                    handler: Callable[[Exception], Coroutine] = None):
        try:
            yield
        except Exception as err:
            if ignore and type(err) in ignore:
                return

            error_message = self.error(err, desc)

            if handler and error_message:
                await handler(err)

    @contextmanager
    def sync_catch(self,
                   desc: str = None,
                   ignore: List[Union[Type[Exception], Type[BaseException]]] = None,
                   handler: Callable[[Exception], None] = None):
        try:
            yield
        except Exception as err:
            if ignore and type(err) in ignore:
                return

            error_message = self.error(err, desc)

            if handler and error_message:
                handler(err)
