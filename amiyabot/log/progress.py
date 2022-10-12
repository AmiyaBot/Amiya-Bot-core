import sys
import time

from typing import Iterator


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
