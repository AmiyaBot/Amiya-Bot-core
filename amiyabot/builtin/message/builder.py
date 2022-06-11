import re
import qqbot
import jieba

from qqbot.model.ws_context import WsContext
from amiyabot.builtin.message import Message
from amiyabot.adapter import BotInstance
from amiyabot.util import remove_punctuation, chinese_to_digits
from amiyabot import log

ADMIN = ['2', '4', '5']

jieba.setLogLevel(jieba.logging.INFO)


async def package_message(instance: BotInstance, event: WsContext, message: qqbot.Message, is_reference: bool = False):
    """
    预处理并封装消息对象

    :param instance:     AmiyaBot 实例
    :param is_reference: 是否是引用的消息
    :param event:        原 qqbot WsContext 对象
    :param message:      原 qqbot Message 对象
    :return:             Message 对象
    """
    if event.event_type in ['AT_MESSAGE_CREATE', 'MESSAGE_CREATE']:
        if message.author.bot and not is_reference:
            return None

        data = Message(instance, message)

        if hasattr(message, 'member') and hasattr(message.member, 'roles'):
            if [n for n in message.member.roles if n in ADMIN]:
                data.is_admin = True

        if hasattr(message, 'attachments'):
            for item in message.attachments:
                data.image.append('http://' + item.url)

        if hasattr(message, 'content'):
            text = message.content

            if hasattr(message, 'mentions') and message.mentions:
                me = await instance.get_me()
                for user in message.mentions:
                    text = text.replace(f'<@!{user.id}>', '')
                    if user.id == me.id:
                        data.is_at = True
                        continue
                    if user.bot:
                        continue
                    data.at_target.append(user.id)

            face_list = re.findall(r'<emoji:(\d+)>', text)
            if face_list:
                for fid in face_list:
                    data.face.append(fid)

            data = text_convert(data, text.strip(), message.content)

        if hasattr(message, 'message_reference'):
            reference = await instance.message_api.get_message(message.channel_id,
                                                               message.message_reference.message_id)
            reference_data = await package_message(instance, event, reference.message, True)

            if reference_data:
                data.image += reference_data.image

        log.info(data.__str__())

        return data


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
