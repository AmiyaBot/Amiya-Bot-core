from amiyabot.builtin.message import Event, EventList, Message
from amiyabot.adapters import BotAdapterProtocol

from .api import OneBot12API


async def package_onebot12_message(instance: BotAdapterProtocol, data: dict):
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
        msg.avatar = await instance.api.get_user_avatar(data)

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
                    msg.image.append(await get_file(instance, chain_data))

                if chain['type'] == 'file':
                    msg.files.append(await get_file(instance, chain_data))

                if chain['type'] == 'voice':
                    msg.voice = await get_file(instance, chain_data)

                if chain['type'] == 'audio':
                    msg.audio = await get_file(instance, chain_data)

                if chain['type'] == 'video':
                    msg.video = await get_file(instance, chain_data)

        msg.set_text(text)
        return msg

    event_list = EventList([Event(instance, message_type, data)])

    if data['detail_type']:
        event_list.append(instance, '{type}.{detail_type}'.format(**data), data)

    return event_list


async def get_file(instance: BotAdapterProtocol, chain_data: dict):
    api: OneBot12API = instance.api

    return await api.get_file(chain_data['file_id'])
