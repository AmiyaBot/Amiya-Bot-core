from amiyabot.builtin.message import Event, EventList, Message
from amiyabot.adapters import BotAdapterProtocol

from ..common import text_convert


def package_cqhttp_message(instance: BotAdapterProtocol, account: str, data: dict):
    if 'post_type' not in data:
        return None

    post_type = data['post_type']

    if post_type == 'message':
        sender: dict = data['sender']

        if data['message_type'] == 'private':
            msg = Message(instance, data)
            msg.message_type = 'private'
            msg.is_direct = True
            msg.nickname = sender.get('nickname')

        elif data['message_type'] == 'group':
            msg = Message(instance, data)
            msg.message_type = 'group'
            msg.channel_id = str(data['group_id'])
            msg.nickname = sender.get('card') or sender.get('nickname')
            msg.is_admin = sender.get('role') in ['owner', 'admin']

        else:
            return None
    else:
        event_list = EventList([Event(instance, post_type, data)])

        if post_type == 'meta_event':
            second_type = data['meta_event_type']
            event_list.append(instance, f'meta_event.{second_type}', data)

            if second_type == 'lifecycle':
                event_list.append(instance, f'meta_event.{second_type}.' + data['sub_type'], data)

        elif post_type == 'request':
            second_type = data['request_type']
            event_list.append(instance, f'request.{second_type}', data)

        elif post_type == 'notice':
            second_type = data['notice_type']
            event_list.append(instance, f'notice.{second_type}', data)

            if second_type == 'notify':
                event_list.append(instance, f'notice.{second_type}.' + data['sub_type'], data)

        return event_list

    msg.message_id = str(data['message_id'])
    msg.user_id = str(data['sender']['user_id'])
    msg.avatar = f'https://q.qlogo.cn/headimg_dl?dst_uin={msg.user_id}&spec=100'

    message_chain = data['message']
    text = ''

    if message_chain:
        for chain in message_chain:
            chain_data = chain['data']

            if chain['type'] == 'at':
                if str(chain_data['qq']) == str(account):
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
