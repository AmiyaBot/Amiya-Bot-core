import os
import sys
import time
import logging
import traceback

from typing import Union, Dict, List, Type, Iterator, Callable, Coroutine
from contextlib import asynccontextmanager, contextmanager
from logging.handlers import TimedRotatingFileHandler


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

        if not os.path.exists(save_path):
            os.makedirs(save_path)

    def __handler(self, filename: str):
        if not filename:
            filename = self.default_file

        if filename not in self.handlers:
            formatter = logging.Formatter(self.formatter)

            file_handler = TimedRotatingFileHandler(
                encoding='utf-8',
                filename=f'{self.save_path}/{filename}.log',
                backupCount=7,
                when='D'
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

    def info(self, message: str, filename: str = None):
        self.__handler(filename).info(message.strip('\n'))

    def warning(self, message: str, filename: str = None):
        self.__handler(filename).warning(message.strip('\n'))

    def debug(self, message: str, filename: str = None):
        self.__handler(filename).debug(message.strip('\n'))

    def error(self, message: Union[str, Exception], desc: str = None, filename: str = None):
        handler = self.__handler(filename)

        text = message

        if isinstance(message, Exception):
            text = traceback.format_exc()
        if desc:
            text = f'{desc} {text}'

        handler.error(text.strip('\n'))

        return text

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


def download_progress(title: str, max_size: int, chunk_size: int, iter_content: Iterator):
    def print_bar():
        curr = int(curr_size / max_size * 100)

        used = time.time() - start_time
        c_size = round(curr_size / 1024 / 1024, 2)
        size = round(max_size / 1024 / 1024, 2)
        average = (c_size / used) if used and curr_size else 0

        average_text = f'{int(average)}mb/s'
        if average < 1:
            average_text = f'{int(average * 1024)}kb/s'

        block = int(curr / 4)
        bar = '=' * block + ' ' * (25 - block)

        msg = f'{title} [{bar}] {c_size} / {size}mb ({curr}%) {average_text}'

        print('\r', end='')
        print(msg, end='')

        sys.stdout.flush()

    curr_size = 0
    start_time = time.time()

    print_bar()
    for chunk in iter_content:
        yield chunk
        curr_size += chunk_size
        print_bar()

    print()


basic = LoggerManager('Bot')

info = basic.info
error = basic.error
debug = basic.debug
catch = basic.catch
warning = basic.warning
sync_catch = basic.sync_catch
