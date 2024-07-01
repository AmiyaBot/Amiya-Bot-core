import re
import dhash
import jieba
import string
import random

from typing import List
from string import punctuation
from zhon.hanzi import punctuation as punctuation_cn
from io import BytesIO
from PIL import Image


def random_code(length):
    pool = string.digits + string.ascii_letters
    code = ''
    for _ in range(length):
        code += random.choice(pool)
    return code


def remove_punctuation(text: str):
    for i in punctuation:
        text = text.replace(i, '')
    for i in punctuation_cn:
        text = text.replace(i, '')
    return text


def remove_prefix_once(sentence: str, prefix_keywords: List[str]):
    for prefix in prefix_keywords:
        if sentence.startswith(prefix):
            return sentence[len(prefix) :], prefix
    return sentence, ''


def cut_by_jieba(text: str):
    return jieba.lcut(text.lower().replace(' ', ''))


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
        '亿': 100000000,
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


def dhash_image(image: bytes, size: int = 8):
    return dhash.dhash_int(image=Image.open(BytesIO(image)), size=size)
