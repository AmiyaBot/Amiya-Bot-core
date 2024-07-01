import json

from typing import List, Dict
from amiyabot.builtin.message import Event, Message, File
from amiyabot.adapters import BotAdapterProtocol


class RolePermissionCache:
    guild_role: Dict[str, Dict[str, int]] = {}
    cache_create_time: Dict[str, float] = {}


async def package_kook_message(instance: BotAdapterProtocol, message: dict):
    if message['type'] == 255:
        return Event(instance, message['extra']['type'], message)

    extra: dict = message['extra']
    user: dict = extra['author']

    if user['bot']:
        return None

    t: int = extra['type']

    data = Message(instance, message)

    data.message_id = message['msg_id']
    data.message_type = message['channel_type']

    data.is_at = instance.appid in extra['mention']
    data.is_at_all = bool(extra.get('mention_all') or extra.get('mention_here'))
    data.is_direct = message['channel_type'] == 'PERSON'

    data.user_id = user['id']
    data.guild_id = extra.get('guild_id', '')
    data.channel_id = message['target_id']
    data.nickname = user['nickname'] or user['username']
    data.avatar = user['vip_avatar'] or user['avatar']

    if data.guild_id in RolePermissionCache.guild_role:
        for item in user['roles']:
            if item not in RolePermissionCache.guild_role[data.guild_id]:
                continue

            permission = RolePermissionCache.guild_role[data.guild_id][item]
            if permission & (1 << 0) == (1 << 0) or permission & (1 << 1) == (1 << 1):
                data.is_admin = True

    for item in extra.get('emoji', []):
        data.face.append(list(item.keys())[0])

    for user_id in extra['mention']:
        data.at_target.append(user_id)

    text = ''

    if t == 2:
        data.image.append(message['content'])

    if t == 3:
        data.video = message['content']

    if t == 9:
        text = extra['kmarkdown']['raw_content']

    if t == 10:
        card: List[dict] = json.loads(message['content'])
        for item in card:
            modules: List[dict] = item.get('modules', [])

            for module in modules:
                if module['type'] == 'file' and module['canDownload']:
                    data.files.append(File(module['src'], module['title']))

    if extra.get('quote'):
        if extra['quote']['type'] == 2:
            data.image.append(extra['quote']['content'])

    data.set_text(text)
    return data
