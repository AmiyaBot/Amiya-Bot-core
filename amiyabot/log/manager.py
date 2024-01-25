import os
import sys
import inspect
import logging
import traceback

from typing import Union, Dict, List, Tuple, Type, Any, Callable, Optional, Awaitable
from contextlib import asynccontextmanager, contextmanager
from concurrent_log_handler import ConcurrentRotatingFileHandler
from amiyabot.util import argv

FETCHER = Callable[[str, str, Tuple[Any, ...], Dict[str, Any]], None]


class LoggerManager:
    user_logger = None
    log_fetchers: Dict[int, FETCHER] = {}

    def __init__(
        self,
        name: str = '',
        level: Optional[int] = None,
        formatter: str = '',
        save_path: str = './log',
        save_filename: str = 'running',
    ):
        self.handlers: Dict[str, logging.Logger] = {}

        self.name = name
        self.debug_mode = argv('debug', bool)

        self.level = level or (logging.DEBUG if self.debug_mode else logging.INFO)
        if formatter:
            self.formatter = formatter
        else:
            if name:
                self.formatter = '%(asctime)s [%(name)9s][%(levelname)9s]%(message)s'
            else:
                self.formatter = '%(asctime)s [%(levelname)9s]%(message)s'

        self.save_path = save_path
        self.save_filename = save_filename

    @classmethod
    def use(cls, logger_cls):
        cls.user_logger = logger_cls()

    @classmethod
    def add_fetcher(cls, func: FETCHER):
        cls.log_fetchers[id(func)] = func
        return func

    @classmethod
    def remove_fetcher(cls, func: FETCHER):
        if id(func) in cls.log_fetchers:
            del cls.log_fetchers[id(func)]

    @property
    def __handler(self):
        if self.user_logger and self != self.user_logger:
            return self.user_logger

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

    @property
    def print_method(self):
        def method(text: str, *args, **kwarg):
            if self.debug_mode:
                stack = traceback.extract_stack()
                source = stack[-3]
                filename = os.path.basename(source.filename)

                if filename == '__init__.py':
                    filename = '/'.join(source.filename.replace('\\', '/').split('/')[-2:])

                output = f'[{filename}:{source.lineno}] ' + text.strip('\n')
            else:
                output = ' ' + text.strip('\n')

            level = inspect.getframeinfo(inspect.currentframe().f_back)[2]

            for func in self.log_fetchers.values():
                func(text, level, *args, **kwarg)

            return output

        return method

    def info(self, text: str, *args, **kwarg):
        self.__handler.info(
            self.print_method(text, *args, **kwarg),
        )

    def debug(self, text: str, *args, **kwarg):
        self.__handler.debug(
            self.print_method(text, *args, **kwarg),
        )

    def warning(self, text: str, *args, **kwarg):
        self.__handler.warning(
            self.print_method(text, *args, **kwarg),
        )

    def error(self, err: Union[str, Exception], desc: Optional[str] = None, *args, **kwarg):
        text = traceback.format_exc() if isinstance(err, Exception) else str(err)

        if desc:
            text = f'{desc} {text}'

        self.__handler.error(
            self.print_method(text, desc=desc, *args, **kwarg),
        )

        return text

    def critical(self, err: Union[str, Exception], *args, **kwarg):
        text = traceback.format_exc() if isinstance(err, Exception) else str(err)

        self.__handler.critical(
            self.print_method(text, *args, **kwarg),
        )

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
