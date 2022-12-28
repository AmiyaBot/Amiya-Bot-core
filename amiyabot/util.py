import os
import re
import sys
import random
import string
import zipfile
import asyncio

from typing import List
from string import punctuation
from functools import partial
from contextlib import contextmanager
from zhon.hanzi import punctuation as punctuation_cn
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(min(32, (os.cpu_count() or 1) + 4))


class Singleton(type):
    instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.instances:
            cls.instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instances[cls]


async def run_in_thread_pool(block_func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, partial(block_func, *args, **kwargs))


@contextmanager
def temp_sys_path(path: str):
    sys.path.insert(0, path)
    yield
    sys.path.remove(path)


def append_sys_path(path: str):
    if path not in sys.path:
        sys.path.append(path)


def argv(name, formatter=str):
    key = f'--{name}'
    if key in sys.argv:
        index = sys.argv.index(key) + 1

        if index >= len(sys.argv):
            return True

        if sys.argv[index].startswith('--'):
            return True
        else:
            return formatter(sys.argv[index])


def create_dir(path: str, is_file: bool = False):
    if is_file:
        path = os.path.dirname(path)

    if path and not os.path.exists(path):
        os.makedirs(path)

    return path


def random_code(length):
    pool = string.digits + string.ascii_letters
    code = ''
    for i in range(length):
        code += random.choice(pool)
    return code


def remove_punctuation(text: str):
    for i in punctuation:
        text = text.replace(i, '')
    for i in punctuation_cn:
        text = text.replace(i, '')
    return text


def chinese_to_digits(text: str):
    character_relation = {
        '零': 0,
        '一': 1,
        '二': 2,
        '两': 2,
        '三': 3,
        '四': 4,
        '五': 5,
        '六': 6,
        '七': 7,
        '八': 8,
        '九': 9,
        '十': 10,
        '百': 100,
        '千': 1000,
        '万': 10000,
        '亿': 100000000
    }
    start_symbol = ['一', '二', '两', '三', '四', '五', '六', '七', '八', '九', '十']
    more_symbol = list(character_relation.keys())

    symbol_str = ''
    found = False

    def _digits(chinese: str):
        total = 0
        r = 1
        for i in range(len(chinese) - 1, -1, -1):
            val = character_relation[chinese[i]]
            if val >= 10 and i == 0:
                if val > r:
                    r = val
                    total = total + val
                else:
                    r = r * val
            elif val >= 10:
                if val > r:
                    r = val
                else:
                    r = r * val
            else:
                total = total + r * val
        return total

    for item in text:
        if item in start_symbol:
            if not found:
                found = True
            symbol_str += item
        else:
            if found:
                if item in more_symbol:
                    symbol_str += item
                    continue
                else:
                    digits = str(_digits(symbol_str))
                    text = text.replace(symbol_str, digits, 1)
                    symbol_str = ''
                    found = False

    if symbol_str:
        digits = str(_digits(symbol_str))
        text = text.replace(symbol_str, digits, 1)

    return text


def pascal_case_to_snake_case(camel_case: str):
    snake_case = re.sub(r'(?P<key>[A-Z])', r'_\g<key>', camel_case)
    return snake_case.lower().strip('_')


def snake_case_to_pascal_case(snake_case: str):
    words = snake_case.split('_')
    return ''.join(word.title() if i > 0 else word.lower() for i, word in enumerate(words))


def support_gbk_zip(zip_file: zipfile.ZipFile):
    name_to_info = zip_file.NameToInfo
    for name, info in name_to_info.copy().items():
        real_name = name.encode('cp437').decode('gbk')
        if real_name != name:
            info.filename = real_name
            del name_to_info[name]
            name_to_info[real_name] = info

    return zip_file


def extract_zip(file: str, dest: str, overwrite: bool = False, ignore: List[re.Pattern] = None):
    create_dir(dest)
    pack = zipfile.ZipFile(file)
    for pack_file in support_gbk_zip(pack).namelist():
        dest_file = os.path.join(dest, pack_file)
        if ignore:
            for reg in ignore:
                if re.search(reg, dest_file):
                    continue

        if os.path.exists(dest_file) and not overwrite:
            continue
        pack.extract(pack_file, dest)


def is_valid_url(url: str):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
