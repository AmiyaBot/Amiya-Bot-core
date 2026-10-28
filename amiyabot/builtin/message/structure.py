import abc
import time
import jieba

from typing import Any, List, Union, Optional, Callable, Coroutine
from dataclasses import dataclass
from amiyabot.typeIndexes import *
from amiyautils import remove_punctuation, chinese_to_digits, EventLoop


def cut_by_jieba(text: str):
    return jieba.lcut(text.lower().replace(' ', ''))


class EventStructure:
    def __init__(self, instance: T_BotAdapterProtocol, event_name: str, data: dict, event_id: str = ''):
        self.instance = instance
        self.event_name = event_name
        self.data = data

        # 事件信封（WebSocket payload）最外层的 id，被动消息的 event_id 锚点。
        # 部分事件体（data）内不含 id，只能由适配器从信封透传。
        self.event_id = event_id

    def __str__(self):
        return f'Bot:{self.instance.appid} Event:{self.event_name}'

    async def ack_interaction(self, code: int = 0):
        """
        回应互动事件（按钮回调等）。

        收到 INTERACTION_CREATE 后需尽快调用，否则用户端会一直处于 loading 状态。

        :param code: 0=成功 1=操作失败 2=操作频繁 3=重复操作 4=没有权限 5=仅管理员操作
        """
        put_interaction_response = getattr(self.instance.api, 'put_interaction_response', None)

        if not callable(put_interaction_response):
            raise NotImplementedError(f'{self.instance} 不支持回应互动事件')

        interaction_id = self.data.get('id')
        if not interaction_id:
            raise ValueError(f'{self.event_name} 事件缺少 id，无法回应互动事件')

        return await put_interaction_response(interaction_id, code=code)

    async def reply(self, chain: T_Chain, is_sync: bool = True):
        """
        以事件为锚点回复被动消息（QQ 群 / 单聊）。

        按钮回调（INTERACTION_CREATE）等事件没有原消息 ID，只能使用事件最外层的 id 作为
        event_id 锚点；普通消息仍使用 message_id，二者由适配器二选一。

        事件有 5 分钟有效期，且同一事件最多回复 5 条。

        :param chain:   消息 Chain 对象（其 data 会被替换为事件构造的 Message）
        :param is_sync: 是否同步发送消息
        :return:        MessageCallback 列表
        """
        send_event_message = getattr(self.instance, 'send_event_message', None)

        if not callable(send_event_message):
            raise NotImplementedError(f'{self.instance} 不支持以事件为锚点回复消息')

        # 频道（guild）没有 event_id 语义
        if self.data.get('chat_type') == 0:
            raise NotImplementedError(f'{self.event_name} 事件属于频道场景，不支持 event_id 被动消息')

        data = self.__build_message()
        chain.data = data

        bot = getattr(self.instance, 'bot', None)
        if not bot:
            return await send_event_message(chain, event_id=data.event_id, is_sync=is_sync)

        async with bot.processing_context(chain):
            return await send_event_message(chain, event_id=data.event_id, is_sync=is_sync)

    def __build_message(self) -> 'MessageStructure':
        group_openid = self.data.get('group_openid') or ''
        user_openid = self.data.get('user_openid') or ''
        member_openid = self.data.get('group_member_openid') or self.data.get('op_member_openid') or ''

        if not group_openid and not user_openid:
            raise ValueError(f'{self.event_name} 事件缺少 group_openid / user_openid，无法确定回复目标')

        data = MessageStructure(self.instance)
        data.bot = getattr(self.instance, 'bot', None)

        # 被动消息锚点：优先事件信封 id，其次事件体内的 id
        data.event_id = self.event_id or self.data.get('id') or ''

        # 群聊：group_openid 是发送目标，group_id 仅作展示用途，缺失时回落到 group_openid
        data.channel_openid = group_openid
        data.channel_id = self.data.get('group_id') or group_openid

        # 单聊：user_openid 是发送目标；群聊里的操作者用 group_member_openid
        data.user_openid = user_openid or member_openid
        data.user_id = data.user_openid

        data.is_direct = bool(user_openid) and not group_openid

        return data


class MessageStructure:
    def __init__(self, instance: T_BotAdapterProtocol, message: Optional[dict] = None):
        self.bot: Optional[T_BotHandlerFactory] = None
        self.instance = instance

        self.factory_name = ''

        self.message = message
        self.message_id = ''
        self.message_type = ''

        # 被动消息的另一种锚点（与 message_id 二选一）：事件最外层的 id。
        # 按钮回调 INTERACTION_CREATE、GROUP_ADD_ROBOT、GROUP_MSG_RECEIVE 等事件没有原消息 id，
        # 只能靠它回复；为空时回落到 message_id。
        self.event_id = ''

        # 被引用消息的索引（QQ 群/单聊 message_type=103 时由 message_scene.ext 的
        # ref_msg_idx 提供），可用于发送引用回复。
        self.reference_message_id = ''

        self.face: List[int] = []
        self.image: List[str] = []

        self.files: List[File] = []
        self.voice = ''
        self.audio = ''
        self.video = ''

        self.text = ''
        self.text_prefix = ''
        self.text_digits = ''
        self.text_unsigned = ''
        self.text_original = ''
        self.text_words: List[str] = []

        self.at_target: List[str] = []

        self.is_at = False
        self.is_at_all = False
        self.is_admin = False
        self.is_direct = False

        self.user_id = ''
        self.user_openid = ''

        self.channel_id = ''
        self.channel_openid = ''

        self.guild_id = ''
        self.src_guild_id = ''

        self.nickname = ''
        self.user_avatar = ''
        self.user_avatar_getter: Optional[Coroutine] = None

        self.verify: Optional[Verify] = None
        self.time = int(time.time())

    @property
    def avatar(self):
        if not self.user_avatar and self.user_avatar_getter:
            self.user_avatar = EventLoop.run(self.user_avatar_getter)
        return self.user_avatar

    @avatar.setter
    def avatar(self, value: str):
        self.user_avatar = value

    def __str__(self):
        text = self.text.replace('\n', ' ')
        face = ''.join([f'[face:{n}]' for n in self.face])
        image = '[image]' * len(self.image)

        return 'Bot:{bot}{channel} User:{user}{admin}{direct}{nickname}: {message}'.format(
            **{
                'bot': self.instance.appid,
                'channel': f' Channel:{self.channel_id}' if self.channel_id else '',
                'user': self.user_id,
                'admin': '(admin)' if self.is_admin else '',
                'direct': '(direct)' if self.is_direct else '',
                'nickname': f' {self.nickname}' if self.nickname else '',
                'message': text + face + image,
            }
        )

    def set_text(self, text: str, set_original: bool = True):
        if set_original:
            self.text_original = text

        self.text = text.strip()
        self.text_convert()

    def text_convert(self):
        self.text_digits = chinese_to_digits(self.text)
        self.text_unsigned = remove_punctuation(self.text)

        chars = cut_by_jieba(self.text) + cut_by_jieba(self.text_digits)

        words = list(set(chars))
        words = sorted(words, key=chars.index)

        self.text_words = words

    @abc.abstractmethod
    async def send(self, reply: T_Chain):
        raise NotImplementedError

    @abc.abstractmethod
    async def recall(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def wait(
        self,
        reply: Optional[T_Chain] = None,
        force: bool = False,
        max_time: int = 30,
        data_filter: Optional[Callable] = None,
        level: int = 0,
    ):
        raise NotImplementedError

    @abc.abstractmethod
    async def wait_channel(
        self,
        reply: Optional[T_Chain] = None,
        force: bool = False,
        clean: bool = True,
        max_time: int = 30,
        data_filter: Optional[Callable] = None,
        level: int = 0,
    ):
        raise NotImplementedError


class Verify:
    def __init__(self, result: bool, weight: Union[int, float] = 0, keypoint: Optional[Any] = None):
        self.result = result
        self.weight = weight
        self.keypoint = keypoint

        self.on_selected: Optional[Callable] = None

    def __bool__(self):
        return bool(self.result)

    def __repr__(self):
        return f'<Verify, {self.result}, {self.weight}>'

    def set_attrs(self, *attrs: Any):
        indexes = [
            'result',
            'weight',
            'keypoint',
        ]
        for index, value in zip(indexes, attrs):
            setattr(self, index, value)


@dataclass
class File:
    url: str
    filename: str = ''
