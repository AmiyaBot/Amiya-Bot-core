import re

from amiyabot.builtin.message import Event, File, Message
from amiyabot.adapters import BotAdapterProtocol

MESSAGE_CREATED = [
    'C2C_MESSAGE_CREATE',
    'GROUP_AT_MESSAGE_CREATE',
]

# 「群消息（全量模式）」事件：机器人开启「接收所有消息」后，
# 群内不 @ 机器人的消息也会推送，字段与 GROUP_AT_MESSAGE_CREATE 完全一致。
# https://bot.q.qq.com/wiki/develop/api-v2/autogen/event/group_message_create.html
FULL_MESSAGE_CREATED = [
    'GROUP_MESSAGE_CREATE',
]


def parse_reference_message_id(message: dict) -> str:
    """
    从 message_scene.ext 中解析被引用消息索引（message_type=103 引用消息）。
    官方格式为 key=value 的字符串列表，如 ref_msg_idx=REFIDX_xxx==
    """
    scene = message.get('message_scene')
    if not isinstance(scene, dict):
        return ''

    for item in scene.get('ext') or []:
        if not isinstance(item, str):
            continue
        if item.startswith('ref_msg_idx='):
            return item[len('ref_msg_idx=') :]

    return ''


def parse_attachments(data: Message, message: dict):
    """
    按 content_type 分流附件。
    官方取值：voice 语音 / image/* 图片 / video/mp4 视频 / file 群文件
    """
    for item in message.get('attachments') or []:
        content_type = item.get('content_type') or ''
        url = item.get('url') or ''

        if not url:
            continue

        if content_type.startswith('image'):
            data.image.append(url)
        elif content_type == 'voice':
            data.voice = url
        elif content_type.startswith('video'):
            data.video = url
        else:
            data.files.append(File(url, item.get('filename') or ''))


async def package_qq_group_message(instance: BotAdapterProtocol, event: str, message: dict, is_reference: bool = False):
    if event in MESSAGE_CREATED or event in FULL_MESSAGE_CREATED:
        data = Message(instance, message)
        data.is_direct = event == 'C2C_MESSAGE_CREATE'

        # 只有「@ 机器人」的消息才置 is_at；全量模式下的普通群消息保持 False。
        # 与 KOOK 等适配器一致：是否响应交由使用者的前缀触发词/关键字逻辑决定。
        data.is_at = event == 'GROUP_AT_MESSAGE_CREATE'

        data.message_id = message['id']
        data.user_id = message['author']['id']
        data.nickname = message['author'].get('username') or ''
        data.message_type = message.get('message_type', '')

        if data.is_direct:
            data.user_openid = message['author']['user_openid']
        else:
            data.user_openid = message['author']['member_openid']
            data.channel_id = message['group_id']
            data.channel_openid = message['group_openid']

        if message['author'].get('member_role') in ('admin', 'owner'):
            data.is_admin = True

        if 'attachments' in message:
            parse_attachments(data, message)

        # 全量模式下 @ 的对象列表（不含 @ 机器人自身）
        for user in message.get('mentions') or []:
            user_id = user.get('id')
            if user_id:
                data.at_target.append(user_id)

        data.reference_message_id = parse_reference_message_id(message)

        if 'content' in message:
            text = message['content']

            face_list = re.findall(r'<emoji:(\d+)>', text)
            if face_list:
                for fid in face_list:
                    data.face.append(fid)
                text = re.sub(r'<emoji:\d+>', '', text)

            data.set_text(text)

        return data

    return Event(instance, event, message)
