import re

from amiyabot.builtin.message import Event, File, Message
from amiyabot.adapters import BotAdapterProtocol

# 全量群消息（GROUP_MESSAGE_CREATE）的 content 中 @成员 以 <@openid> 或 <@!openid> 标记，
# 且事件 mentions 列表不包含机器人自身，因此移除 mentions 后仍残留的 @ 标记即 @机器人
AT_MARK_PATTERN = re.compile(r'<@?!?(all|\w+)>')
EMOJI_PATTERN = re.compile(r'<emoji:(\d+)>')


async def package_qq_group_message(instance: BotAdapterProtocol, event: str, message: dict, is_reference: bool = False):
    message_created = [
        'C2C_MESSAGE_CREATE',
        'GROUP_AT_MESSAGE_CREATE',
        'GROUP_MESSAGE_CREATE',
    ]
    if event in message_created:
        data = Message(instance, message)
        data.is_direct = event == 'C2C_MESSAGE_CREATE'

        # 单聊与 @机器人消息（content 已由平台去除 @机器人前缀）恒视为被 @；
        # 全量群消息需自行从 @ 标记中识别是否 @ 了机器人
        data.is_at = event != 'GROUP_MESSAGE_CREATE'

        data.message_id = message['id']
        data.user_id = message['author']['id']
        data.nickname = message['author'].get('username', '')

        if message['author'].get('member_role') in ('admin', 'owner'):
            data.is_admin = True

        if data.is_direct:
            data.user_openid = message['author']['user_openid']
        else:
            data.user_openid = message['author']['member_openid']
            data.channel_id = message.get('group_id', message['group_openid'])
            data.channel_openid = message['group_openid']

        if 'attachments' in message:
            for item in message['attachments']:
                content_type = item.get('content_type', '')
                url = item.get('url', '')

                if content_type.startswith('image'):
                    data.image.append(url)
                elif content_type == 'voice' or item.get('voice_wav_url'):
                    data.voice = item.get('voice_wav_url') or url
                elif content_type.startswith('video'):
                    data.video = url
                else:
                    data.files.append(File(url=url, filename=item.get('filename', '')))

        scene_ext = (message.get('message_scene') or {}).get('ext') or {}
        if isinstance(scene_ext, dict) and scene_ext.get('ref_msg_idx'):
            data.reference_message_id = str(scene_ext['ref_msg_idx'])

        if 'content' in message:
            text = message['content']

            if event == 'GROUP_MESSAGE_CREATE':
                text = remove_at_mark(data, text, message.get('mentions') or [])

            face_list = EMOJI_PATTERN.findall(text)
            if face_list:
                for fid in face_list:
                    data.face.append(fid)

            data.set_text(text)

        return data

    return Event(instance, event, message)


def remove_at_mark(data: Message, text: str, mentions: list) -> str:
    for user in mentions:
        if not user.get('bot'):
            data.at_target.append(user['id'])

        for mark in (f"<@{user['id']}>", f"<@!{user['id']}>"):
            text = text.replace(mark, '')

    if '<@all>' in text:
        data.is_at_all = True
        text = text.replace('<@all>', '')

    if AT_MARK_PATTERN.search(text):
        data.is_at = True
        text = AT_MARK_PATTERN.sub('', text)

    return text
