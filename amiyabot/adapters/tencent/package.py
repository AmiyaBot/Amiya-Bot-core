import re
import jieba

from amiyabot.builtin.message import Event, Message
from amiyabot.adapters.tencent.api import TencentAPI

from ..common import text_convert

ADMIN = ['2', '4', '5']

jieba.setLogLevel(jieba.logging.INFO)


async def package_tencent_message(instance: TencentAPI,
                                  event: str,
                                  message: dict,
                                  is_reference: bool = False):
    message_created = [
        'MESSAGE_CREATE',
        'AT_MESSAGE_CREATE',
        'DIRECT_MESSAGE_CREATE'
    ]
    if event in message_created:
        if 'bot' in message['author'] and message['author']['bot'] and not is_reference:
            return None

        data = get_info(Message(instance, message), message)
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
                    if me and user['id'] == me['id']:
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
            if reference:
                reference_data = await package_tencent_message(instance, event, reference['message'], True)
                if reference_data:
                    data.image += reference_data.image

        return data
    else:
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
