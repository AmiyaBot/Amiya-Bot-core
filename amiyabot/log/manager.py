import os
import sys
import logging
import traceback

from typing import Union, Dict, List, Type, Callable, Optional, Awaitable
from contextlib import asynccontextmanager, contextmanager
from concurrent_log_handler import ConcurrentRotatingFileHandler
from amiyabot.util import argv, create_dir

LOG_FILE_MAX_BYTES = argv('log-file-max-bytes', int) or (512 * 1024)
LOG_FILE_BACKUP_COUNT = argv('log-file-backup-count', int) or 10


class LoggerManager:
    user_logger = None

    log_handlers: List[logging.Handler] = []

    def __init__(
        self,
        name: str = '',
        level: Optional[int] = None,
        formatter: str = '',
        save_path: str = './log',
        save_filename: str = 'running',
    ):
        self.debug_mode = argv('debug', bool)

        self.level = level or (logging.DEBUG if self.debug_mode else logging.INFO)

        if not formatter:
            n = '[%(name)9s]' if name else ''
            formatter = f'%(asctime)s {n}[%(levelname)9s]%(message)s'

        fmt = logging.Formatter(formatter)

        self.save_path = save_path
        self.file_handler = ConcurrentRotatingFileHandler(
            filename=f'{self.save_path}/{save_filename}.log',
            encoding='utf-8',
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT,
        )
        self.file_handler.setFormatter(fmt)
        self.file_handler.setLevel(self.level)

        self.stream_handler = logging.StreamHandler(stream=sys.stdout)
        self.stream_handler.setFormatter(fmt)
        self.stream_handler.setLevel(self.level)

        self.__logger = logging.getLogger(name=name)
        self.__logger.setLevel(self.level)
        self.__logger.addHandler(self.file_handler)
        self.__logger.addHandler(self.stream_handler)

    @classmethod
    def use(cls, logger_cls):
        cls.user_logger = logger_cls()

    @classmethod
    def add_handler(cls, handler: logging.Handler):
        cls.log_handlers.append(handler)
        return handler

    @classmethod
    def remove_handler(cls, handler: logging.Handler):
        if handler in cls.log_handlers:
            cls.log_handlers.remove(handler)

    @property
    def logger(self):
        if self.user_logger and self != self.user_logger:
            return self.user_logger

        create_dir(self.save_path)

        for h in set(self.log_handlers) - set(self.__logger.handlers):
            self.__logger.addHandler(h)

        for h in set(self.__logger.handlers) - set(self.log_handlers):
            if h not in (self.file_handler, self.stream_handler):
                self.__logger.removeHandler(h)

        return self.__logger

    @property
    def print_method(self):
        def method(text: str):
            if self.debug_mode:
                stack = traceback.extract_stack()
                source = stack[-3]
                filename = os.path.basename(source.filename)

                if filename == '__init__.py':
                    filename = '/'.join(source.filename.replace('\\', '/').split('/')[-2:])

                output = f'[{filename}:{source.lineno}] ' + text.strip('\n')
            else:
                output = ' ' + text.strip('\n')

            return output

        return method

    def info(self, text: str, *args, **kwarg):
        self.logger.info(
            self.print_method(text),
            *args,
            **kwarg,
        )

    def debug(self, text: str, *args, **kwarg):
        self.logger.debug(
            self.print_method(text),
            *args,
            **kwarg,
        )

    def warning(self, text: str, *args, **kwarg):
        self.logger.warning(
            self.print_method(text),
            *args,
            **kwarg,
        )

    def error(self, err: Union[str, Exception], desc: Optional[str] = None, *args, **kwarg):
        text = traceback.format_exc() if isinstance(err, Exception) else str(err)

        if desc:
            text = f'{desc} {text}'

        self.logger.error(
            self.print_method(text),
            *args,
            **kwarg,
        )

        return text

    def critical(self, err: Union[str, Exception], *args, **kwarg):
        text = traceback.format_exc() if isinstance(err, Exception) else str(err)

        self.logger.critical(
            self.print_method(text),
            *args,
            **kwarg,
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
