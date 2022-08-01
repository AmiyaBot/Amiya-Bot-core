import jieba

from amiyabot.util import remove_punctuation, chinese_to_digits
from amiyabot.builtin.message import Message


def text_convert(message: Message, origin, initial):
    """
    消息文本的最终处理

    :param message:  Message 对象
    :param origin:   预处理消息文本
    :param initial:  未经预处理的原始消息文本
    :return:         Message 对象
    """
    message.text = remove_punctuation(origin)
    message.text_digits = chinese_to_digits(message.text)
    message.text_origin = origin
    message.text_initial = initial

    chars = cut_by_jieba(message.text) + cut_by_jieba(message.text_digits)

    words = list(set(chars))
    words = sorted(words, key=chars.index)

    message.text_words = words

    return message


def cut_by_jieba(text):
    return jieba.lcut(
        text.lower().replace(' ', '')
    )
