import os
import sys
import time
import logging
import traceback

from typing import Union, List, Type, Callable, Coroutine, Iterator
from contextlib import asynccontextmanager
from logging.handlers import TimedRotatingFileHandler

if not os.path.exists('log'):
    os.makedirs('log')

formatter = '%(asctime)s [%(levelname)s] %(message)s'
file_handler = TimedRotatingFileHandler(
    filename='log/amiyabot.log',
    backupCount=7,
    when='D'
)
file_handler.setFormatter(logging.Formatter(formatter))
file_handler.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO,
                    format=formatter,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()
logger.addHandler(file_handler)


def info(message: str):
    logger.info(message)


def error(message: Union[str, Exception], desc: str = None):
    text = message

    if isinstance(message, Exception):
        text = traceback.format_exc()
    if desc:
        text = f'{desc} {text}'

    logger.error(text)

    return text


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


@asynccontextmanager
async def catch(desc: str = None,
                ignore: List[Union[Type[Exception], Type[BaseException]]] = None,
                handler: Callable[[Exception], Coroutine] = None):
    try:
        yield
    except Exception as err:
        if ignore and type(err) in ignore:
            return

        error_message = error(err, desc)

        if handler and error_message:
            await handler(err)
