import os
import logging
import traceback

from typing import Union, List, Type, Callable, Optional, Awaitable
from contextlib import asynccontextmanager, contextmanager
from amiyabot.util import create_dir

from .handlers import LogHandlers, LOG_FILE_SAVE_PATH


class LoggerManager:
    user_logger = None

    def __init__(self, name: str, save_path: str = LOG_FILE_SAVE_PATH, save_filename: str = 'running'):
        self.save_path = save_path

        self.__logger = logging.getLogger(name=name)
        self.__logger.setLevel(LogHandlers.level)

        LogHandlers.set_stream_handler(self.__logger)
        LogHandlers.set_file_handler(self.__logger, save_path, save_filename)

    @classmethod
    def use(cls, logger_cls):
        cls.user_logger = logger_cls()

    @property
    def logger(self):
        if self.user_logger and self != self.user_logger:
            return self.user_logger

        create_dir(self.save_path)

        return self.__logger

    @property
    def print_method(self):
        def method(text: str):
            if LogHandlers.debug_mode:
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
