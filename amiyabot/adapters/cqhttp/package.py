import re

from amiyabot.builtin.message import Event, Message
from amiyabot.adapters import BotAdapterProtocol

from ..convert import text_convert


def package_cqhttp_message(instance: BotAdapterProtocol, account: str, data: dict):
    if 'post_type' not in data:
        return None

    if data['post_type'] == 'message':
        if data['message_type'] == 'private':
            msg = Message(instance, data)
            msg.message_type = 'private'
            msg.is_direct = True
            msg.nickname = data['sender']['nickname']

        elif data['message_type'] == 'group':
            msg = Message(instance, data)
            msg.message_type = 'group'
            msg.channel_id = data['group_id']
            msg.nickname = data['sender']['nickname']
            msg.is_admin = data['sender']['role'] in ['owner', 'admin']

        else:
            return None
    else:
        return Event(instance, data['post_type'], data)

    msg.message_id = data['message_id']
    msg.user_id = data['sender']['user_id']
    msg.avatar = f'https://q.qlogo.cn/headimg_dl?dst_uin={msg.user_id}&spec=100'

    message_chain = data['message']
    text = ''

    if message_chain:
        for chain in message_chain:
            chain_data = chain['data']

            if chain['type'] == 'at':
                if chain_data['qq'] == account:
                    msg.is_at = True
                else:
                    msg.at_target.append(chain_data['qq'])

            if chain['type'] == 'text':
                text += chain_data['text'].strip()

            if chain['type'] == 'face':
                msg.face.append(chain_data['id'])

            if chain['type'] == 'image':
                msg.image.append(chain_data['url'].strip())

    return text_convert(msg, text, text)
