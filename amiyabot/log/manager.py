import os
import sys
import inspect
import logging
import traceback

from typing import Union, Dict, List, Tuple, Type, Any, Callable, Optional, Awaitable
from contextlib import asynccontextmanager, contextmanager
from concurrent_log_handler import ConcurrentRotatingFileHandler
from amiyabot.util import argv, create_dir

FETCHER = Callable[[str, str, Tuple[Any, ...], Dict[str, Any]], None]


class LoggerManager:
    user_logger = None

    log_fetchers: List[FETCHER] = []
    log_handlers: List[logging.Handler] = []

    def __init__(
        self,
        name: str = '',
        level: Optional[int] = None,
        formatter: str = '',
        save_path: str = './log',
        save_filename: str = 'running',
    ):
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

        formatter = logging.Formatter(self.formatter)

        self.file_handler = ConcurrentRotatingFileHandler(
            filename=f'{self.save_path}/{self.save_filename}.log',
            encoding='utf-8',
            maxBytes=512 * 1024,
            backupCount=10,
        )
        self.file_handler.setFormatter(formatter)
        self.file_handler.setLevel(self.level)

        self.stream_handler = logging.StreamHandler(stream=sys.stdout)
        self.stream_handler.setFormatter(formatter)
        self.stream_handler.setLevel(self.level)

        self.loggers: Dict[str, logging.Logger] = {}

    @classmethod
    def use(cls, logger_cls):
        cls.user_logger = logger_cls()

    @classmethod
    def add_fetcher(cls, func: FETCHER):
        cls.log_fetchers.append(func)
        return func

    @classmethod
    def remove_fetcher(cls, func: FETCHER):
        if func in cls.log_fetchers:
            cls.log_fetchers.remove(func)

    @classmethod
    def add_handler(cls, handler: logging.Handler):
        cls.log_handlers.append(handler)
        return handler

    @classmethod
    def remove_handler(cls, handler: logging.Handler):
        if handler in cls.log_handlers:
            cls.log_handlers.remove(handler)

    @property
    def __logger(self):
        if self.user_logger and self != self.user_logger:
            return self.user_logger

        if self.save_filename not in self.loggers:
            logger = logging.getLogger(name=self.name)
            logger.setLevel(self.level)

            if not logger.hasHandlers():
                logger.addHandler(self.file_handler)
                logger.addHandler(self.stream_handler)

            self.loggers[self.save_filename] = logger

        create_dir(self.save_path)
        _logger = self.loggers[self.save_filename]

        for h in set(self.log_handlers) - set(_logger.handlers):
            _logger.addHandler(h)

        for h in set(_logger.handlers) - set(self.log_handlers):
            if h != self.file_handler and h != self.stream_handler:
                _logger.removeHandler(h)

        return _logger

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

            for func in self.log_fetchers:
                func(text, level, *args, **kwarg)

            return output

        return method

    def info(self, text: str, *args, **kwarg):
        self.__logger.info(
            self.print_method(text, *args, **kwarg),
        )

    def debug(self, text: str, *args, **kwarg):
        self.__logger.debug(
            self.print_method(text, *args, **kwarg),
        )

    def warning(self, text: str, *args, **kwarg):
        self.__logger.warning(
            self.print_method(text, *args, **kwarg),
        )

    def error(self, err: Union[str, Exception], desc: Optional[str] = None, *args, **kwarg):
        text = traceback.format_exc() if isinstance(err, Exception) else str(err)

        if desc:
            text = f'{desc} {text}'

        self.__logger.error(
            self.print_method(text, desc=desc, *args, **kwarg),
        )

        return text

    def critical(self, err: Union[str, Exception], *args, **kwarg):
        text = traceback.format_exc() if isinstance(err, Exception) else str(err)

        self.__logger.critical(
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
