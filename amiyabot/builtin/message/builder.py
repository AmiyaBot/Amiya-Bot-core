import re
import jieba

from amiyabot.builtin.message import Event, Message
from amiyabot.adapter import BotInstance
from amiyabot.util import remove_punctuation, chinese_to_digits

ADMIN = ['2', '4', '5']

jieba.setLogLevel(jieba.logging.INFO)


async def package_message(instance: BotInstance,
                          event: str,
                          message: dict,
                          is_reference: bool = False):
    """
    预处理并封装消息对象

    :param instance:     AmiyaBot 实例
    :param is_reference: 是否是引用的消息
    :param event:        事件名
    :param message:      消息对象
    """
    message_created = [
        'MESSAGE_CREATE',
        'AT_MESSAGE_CREATE',
        'DIRECT_MESSAGE_CREATE'
    ]
    if event in message_created:
        if 'bot' in message['author'] and message['author']['bot'] and not is_reference:
            return None

        data = Message(instance, message)
        data.is_direct = 'direct_message' in message and message['direct_message']

        if 'member' in message:
            if 'roles' in message['member'] and [n for n in message['member']['roles'] if n in ADMIN]:
                data.is_admin = True
            data.joined_at = message['member']['joined_at']

        if 'attachments' in message:
            for item in message['attachments']:
                data.image.append('http://' + item['url'])

        if 'content' in message:
            text = message['content']

            if 'mentions' in message and message['mentions']:
                me = await instance.get_me()
                for user in message['mentions']:
                    text = text.replace('<@!{id}>'.format(**user), '')
                    if user['id'] == me['id']:
                        data.is_at = True
                        continue
                    if user['bot']:
                        continue
                    data.at_target.append(user['id'])

            face_list = re.findall(r'<emoji:(\d+)>', text)
            if face_list:
                for fid in face_list:
                    data.face.append(fid)

            data = text_convert(data, text.strip(), message['content'])

        if 'message_reference' in message:
            reference = await instance.get_message(message['channel_id'],
                                                   message['message_reference']['message_id'])
            reference_data = await package_message(instance, event, reference['message'], True)

            if reference_data:
                data.image += reference_data.image

        return data
    else:
        return Event(instance.appid, event, message)


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
