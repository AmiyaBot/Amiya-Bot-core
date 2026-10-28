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

# content 中 @成员 的标记形态：<@openid>（官方）/ <@!openid>（兼容频道形态）。
# openid 不保证为 \w（评审实测线上存在含 - 等字符的形态），按「非 > 与空白」匹配
AT_MARK_PATTERN = re.compile(r'<@!?[^>\s]+>')


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

        if content_type == 'voice':
            # 语音附件可能只有 voice_wav_url 而无 url（官方字段：voice_wav_url / asr_refer_text）
            voice = item.get('voice_wav_url') or url
            if voice:
                data.voice = voice
            continue

        if not url:
            continue

        if content_type.startswith('image'):
            data.image.append(url)
        elif content_type.startswith('video'):
            data.video = url
        else:
            data.files.append(File(url, item.get('filename') or ''))


def remove_at_mark(data: Message, text: str, mentions: list) -> str:
    """
    处理全量群消息（GROUP_MESSAGE_CREATE）content 中的 @ 标记：

    - mentions 成员（官方行为：不包含机器人自身）的标记从 text 剔除并计入 at_target；
    - 剔除后残留的 <@...> 标记只能是 @ 机器人 → 置 is_at 并剔除；
    - <@all> 置 is_at_all 并剔除（@全体不算 @ 机器人，不影响 is_at）；
    - 若平台将来在 mentions 中携带机器人自身（bot=True 条目），则按该条目 id 直接判定，
      且不计入 at_target。
    """
    bot_id = ''

    for user in mentions or []:
        uid = user.get('id')
        if not uid:
            continue

        if user.get('bot'):
            bot_id = uid
            continue

        data.at_target.append(uid)
        text = text.replace(f'<@{uid}>', '').replace(f'<@!{uid}>', '')

    if '<@all>' in text or '<@!all>' in text:
        data.is_at_all = True
        text = text.replace('<@all>', '').replace('<@!all>', '')

    if bot_id:
        if f'<@{bot_id}>' in text or f'<@!{bot_id}>' in text:
            data.is_at = True
        text = text.replace(f'<@{bot_id}>', '').replace(f'<@!{bot_id}>', '')
    elif AT_MARK_PATTERN.search(text):
        data.is_at = True
        text = AT_MARK_PATTERN.sub('', text)

    return text


async def package_qq_group_message(
    instance: BotAdapterProtocol,
    event: str,
    message: dict,
    is_reference: bool = False,
    event_id: str = '',
):
    if event in MESSAGE_CREATED or event in FULL_MESSAGE_CREATED:
        data = Message(instance, message)
        data.is_direct = event == 'C2C_MESSAGE_CREATE'

        # 既有语义保持不变（GROUP_AT_MESSAGE_CREATE 恒 True、C2C 恒 False）；
        # 全量事件默认 False，是否 @ 了机器人在下方 content 处理时按标记追加推断（remove_at_mark）
        data.is_at = event == 'GROUP_AT_MESSAGE_CREATE'

        data.message_id = message['id']
        data.user_id = message['author']['id']
        data.nickname = message['author'].get('username') or ''
        data.message_type = message.get('message_type', '')

        if data.is_direct:
            data.user_openid = message['author']['user_openid']
        else:
            data.user_openid = message['author']['member_openid']
            # 官方文档只保证 group_openid；group_id 为实际推送携带的附加字段，缺失时回退
            data.channel_id = message.get('group_id') or message['group_openid']
            data.channel_openid = message['group_openid']

        if message['author'].get('member_role') in ('admin', 'owner'):
            data.is_admin = True

        if 'attachments' in message:
            parse_attachments(data, message)

        if event not in FULL_MESSAGE_CREATED:
            # 全量事件的 at_target 收集与 @ 标记剔除统一在 remove_at_mark 中进行
            for user in message.get('mentions') or []:
                user_id = user.get('id')
                if user_id:
                    data.at_target.append(user_id)

        data.reference_message_id = parse_reference_message_id(message)

        # 不依赖 content 键是否存在：纯附件消息也可能携带 mentions，@ 判定与 at_target 收集照常执行
        text = message.get('content') or ''

        if event in FULL_MESSAGE_CREATED:
            # is_at 默认值见上方（GROUP_AT_MESSAGE_CREATE 恒 True 的语义不变），
            # 此处在全量事件里按 @ 标记追加推断，使「@ 机器人的全量消息」也能跳过前缀检查
            text = remove_at_mark(data, text, message.get('mentions') or [])

        if 'content' in message:
            face_list = re.findall(r'<emoji:(\d+)>', text)
            if face_list:
                for fid in face_list:
                    data.face.append(fid)
                text = re.sub(r'<emoji:\d+>', '', text)

            data.set_text(text)

        return data

    return Event(instance, event, message, event_id or '')
