import os
import sys
import time
import logging
import traceback

from typing import Union, Dict, List, Type, Iterator, Callable, Coroutine
from contextlib import asynccontextmanager, contextmanager
from logging.handlers import TimedRotatingFileHandler

save_path = 'log'
default_file = 'running'
formatter = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(level=logging.INFO,
                    format=formatter,
                    datefmt='%Y-%m-%d %H:%M:%S')


class LoggerManager:
    handlers: Dict[str, logging.Logger] = {}

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    @classmethod
    def create_handler(cls, filename: str):
        file_handler = TimedRotatingFileHandler(
            encoding='utf-8',
            filename=f'{save_path}/{filename}.log',
            backupCount=7,
            when='D'
        )
        file_handler.setFormatter(logging.Formatter(formatter))
        file_handler.setLevel(logging.DEBUG)

        cls.handlers[filename] = logging.getLogger()
        cls.handlers[filename].addHandler(file_handler)

    @classmethod
    def info(cls, message: str, filename: str = default_file):
        if filename not in cls.handlers:
            cls.create_handler(filename)

        cls.handlers[filename].info(message.strip('\n'))

    @classmethod
    def warning(cls, message: str, filename: str = default_file):
        if filename not in cls.handlers:
            cls.create_handler(filename)

        cls.handlers[filename].warning(message.strip('\n'))

    @classmethod
    def debug(cls, message: str, filename: str = default_file):
        if filename not in cls.handlers:
            cls.create_handler(filename)

        cls.handlers[filename].debug(message.strip('\n'))

    @classmethod
    def error(cls, message: Union[str, Exception], desc: str = None, filename: str = default_file):
        if filename not in cls.handlers:
            cls.create_handler(filename)

        text = message

        if isinstance(message, Exception):
            text = traceback.format_exc()
        if desc:
            text = f'{desc} {text}'

        cls.handlers[filename].error(text)

        return text

    @classmethod
    @asynccontextmanager
    async def catch(cls,
                    desc: str = None,
                    ignore: List[Union[Type[Exception], Type[BaseException]]] = None,
                    handler: Callable[[Exception], Coroutine] = None):
        try:
            yield
        except Exception as err:
            if ignore and type(err) in ignore:
                return

            error_message = cls.error(err, desc)

            if handler and error_message:
                await handler(err)

    @classmethod
    @contextmanager
    def sync_catch(cls,
                   desc: str = None,
                   ignore: List[Union[Type[Exception], Type[BaseException]]] = None,
                   handler: Callable[[Exception], None] = None):
        try:
            yield
        except Exception as err:
            if ignore and type(err) in ignore:
                return

            error_message = cls.error(err, desc)

            if handler and error_message:
                handler(err)


class ServerLog:
    @classmethod
    def write(cls, text: str):
        LoggerManager.info(text, 'server')


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


info = LoggerManager.info
error = LoggerManager.error
debug = LoggerManager.debug
catch = LoggerManager.catch
warning = LoggerManager.warning
sync_catch = LoggerManager.sync_catch
