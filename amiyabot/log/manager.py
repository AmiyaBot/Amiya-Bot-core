import os
import sys
import logging
import traceback

from typing import Union, Dict, List, Type, Any, Callable, Optional, Awaitable
from contextlib import asynccontextmanager, contextmanager
from concurrent_log_handler import ConcurrentRotatingFileHandler
from amiyabot.util import argv


class UserLogger:
    logger: Optional[Any] = None


class LoggerManager:
    def __init__(
        self,
        name: str,
        level: Optional[int] = None,
        formatter: str = '%(asctime)s [%(name)9s][%(levelname)9s]%(message)s',
        save_path: str = 'log',
        save_filename: str = 'running',
    ):
        self.handlers: Dict[str, logging.Logger] = {}

        self.name = name
        self._debug = argv('debug', bool)
        self.level = level or (logging.DEBUG if self._debug else logging.INFO)
        self.formatter = formatter
        self.save_path = save_path
        self.save_filename = save_filename

    @property
    def __handler(self):
        if UserLogger.logger:
            return UserLogger.logger

        if self.save_filename not in self.handlers:
            if not os.path.exists(self.save_path):
                os.makedirs(self.save_path)

            formatter = logging.Formatter(self.formatter)

            file_handler = ConcurrentRotatingFileHandler(
                filename=f'{self.save_path}/{self.save_filename}.log',
                encoding='utf-8',
                maxBytes=512 * 1024,
                backupCount=10,
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

            self.handlers[self.save_filename] = logger

        return self.handlers[self.save_filename]

    def __print_text(self, text: str):
        if self._debug:
            stack = traceback.extract_stack()
            source = stack[-3]
            filename = os.path.basename(source.filename)

            if filename == '__init__.py':
                filename = '/'.join(source.filename.replace('\\', '/').split('/')[-2:])

            return f'[{filename}:{source.lineno}] ' + text.strip('\n')

        return ' ' + text.strip('\n')

    def info(self, message: str):
        self.__handler.info(self.__print_text(message))

    def debug(self, message: str):
        self.__handler.debug(self.__print_text(message))

    def warning(self, message: str):
        self.__handler.warning(self.__print_text(message))

    def error(self, message: Union[str, Exception], desc: Optional[str] = None):
        text = message

        if isinstance(message, Exception):
            text = traceback.format_exc()

        if desc:
            text = f'{desc} {text}'

        self.__handler.error(self.__print_text(text))

        return text

    def critical(self, message: Union[str, Exception]):
        text = message

        if isinstance(message, Exception):
            text = traceback.format_exc()

        self.__handler.critical(self.__print_text(text))

    @asynccontextmanager
    async def catch(
        self,
        desc: Optional[str] = None,
        ignore: Optional[List[Union[Type[Exception], Type[BaseException]]]] = None,
        handler: Optional[Callable[[Exception], Awaitable[None]]] = None,
    ):
        try:
            yield
        except Exception as err:
            if ignore and type(err) in ignore:
                return

            error_message = self.error(err, desc)

            if handler and error_message:
                await handler(err)

    @contextmanager
    def sync_catch(
        self,
        desc: Optional[str] = None,
        ignore: Optional[List[Union[Type[Exception], Type[BaseException]]]] = None,
        handler: Optional[Callable[[Exception], None]] = None,
    ):
        try:
            yield
        except Exception as err:
            if ignore and type(err) in ignore:
                return

            error_message = self.error(err, desc)

            if handler and error_message:
                handler(err)
