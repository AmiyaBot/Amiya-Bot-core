from amiyabot.builtin.message import Event, EventList, Message
from amiyabot.adapters import BotAdapterProtocol

from ..common import text_convert


def package_onebot12_message(instance: BotAdapterProtocol, data: dict):
    message_type = data['type']

    if message_type == 'message':
        msg = Message(instance, data)

        if data['detail_type'] == 'private':
            msg.is_direct = True
            msg.message_type = 'private'
            msg.nickname = str(data['user_id'])

        elif data['detail_type'] == 'group':
            msg.message_type = 'group'
            msg.channel_id = str(data['group_id'])
            msg.nickname = str(data['user_id'])

        else:
            return None

        msg.message_id = str(data['message_id'])
        msg.user_id = str(data['user_id'])
        msg.avatar = instance.get_user_avatar(data)

        message_chain = data['message']
        text = ''

        if message_chain:
            for chain in message_chain:
                chain_data = chain['data']

                if chain['type'] == 'mention_all':
                    msg.is_at_all = True

                if chain['type'] == 'mention':
                    if str(chain_data['user_id']) == str(data['self']['user_id']):
                        msg.is_at = True
                    else:
                        msg.at_target.append(chain_data['user_id'])

                if chain['type'] == 'text':
                    text += chain_data['text'].strip()

                if chain['type'] == 'image':
                    msg.image.append(chain_data['file_id'])

                if chain['type'] == 'file':
                    msg.files.append(chain_data['file_id'])

                if chain['type'] == 'voice':
                    msg.voice = chain_data['file_id']

                if chain['type'] == 'audio':
                    msg.audio = chain_data['file_id']

                if chain['type'] == 'video':
                    msg.video = chain_data['file_id']

        return text_convert(msg, text, text)

    else:
        event_list = EventList([Event(instance, message_type, data)])

        if data['detail_type']:
            event_list.append(instance, '{type}.{detail_type}'.format(**data), data)

        return event_list
