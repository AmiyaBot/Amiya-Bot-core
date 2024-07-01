import re

from amiyabot.builtin.message import Event, Message
from amiyabot.adapters import BotAdapterProtocol

from .api import QQGuildAPI

ADMIN = ['2', '4', '5']


async def package_qq_guild_message(instance: BotAdapterProtocol, event: str, message: dict, is_reference: bool = False):
    message_created = [
        'MESSAGE_CREATE',
        'AT_MESSAGE_CREATE',
        'DIRECT_MESSAGE_CREATE',
    ]
    if event in message_created:
        if 'bot' in message['author'] and message['author']['bot'] and not is_reference:
            return None

        data = get_info(Message(instance, message), message)
        data.is_direct = 'direct_message' in message and message['direct_message']

        api: QQGuildAPI = instance.api
        bot = await api.get_me()

        if not data.is_direct:
            channel = await api.get_channel(data.channel_id)
            if not channel:
                return None

        if 'member' in message:
            if 'roles' in message['member'] and [n for n in message['member']['roles'] if n in ADMIN]:
                data.is_admin = True

        if 'attachments' in message:
            for item in message['attachments']:
                data.image.append('http://' + item['url'])

        if 'content' in message:
            text = message['content']

            if 'mentions' in message and message['mentions']:
                for user in message['mentions']:
                    text = text.replace('<@!{id}>'.format(**user), '')

                    if bot and user['id'] == bot.json['id']:
                        data.is_at = True
                        continue

                    if user['bot']:
                        continue

                    data.at_target.append(user['id'])

            face_list = re.findall(r'<emoji:(\d+)>', text)
            if face_list:
                for fid in face_list:
                    data.face.append(fid)

            data.set_text(text)

        if 'message_reference' in message:
            reference = await api.get_message(message['channel_id'], message['message_reference']['message_id'])
            if reference:
                reference_data = await package_qq_guild_message(instance, event, reference.json['message'], True)
                if reference_data:
                    data.image += reference_data.image

        return data

    return Event(instance, event, message)


def get_info(obj: Message, message: dict):
    author = message['author']

    obj.message_id = message['id']
    obj.user_id = author['id']
    obj.guild_id = message['guild_id']
    obj.src_guild_id = message['src_guild_id'] if 'src_guild_id' in message else message['guild_id']
    obj.channel_id = message['channel_id']
    obj.nickname = author['username']
    obj.avatar = author['avatar'] if 'avatar' in author else None

    return obj
