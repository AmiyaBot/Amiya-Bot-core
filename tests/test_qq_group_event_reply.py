"""
QQ 群 / 单聊：event_id 锚定的被动消息（Event.reply）。

不依赖网络：`send_event_message` 被替换为记录 payload 的假实现，
断言只落在「最终 payload 长什么样」与「抛出了什么异常」。
"""

import pytest

from amiyabot.adapters.tencent.qqGroup import QQGroupBotInstance
from amiyabot.adapters.tencent.qqGroup.builder import (
    PayloadBuilder,
    QQGroupMessageError,
    SeqService,
    raise_for_send_error,
)
from amiyabot.builtin.message import Event, Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.keyboard import InlineKeyboard

GROUP_EVENT = {
    'id': 'EVENT_ID',
    'chat_type': 1,
    'group_openid': 'GROUP_OPENID',
    'group_id': 'GROUP_ID',
    'group_member_openid': 'MEMBER_OPENID',
}


class FakeAPI:
    def __init__(self):
        self.interactions = []

    async def put_interaction_response(self, interaction_id, code=0):
        self.interactions.append((interaction_id, code))
        return {'code': 0}


class FakeInstance:
    """只实现 send_event_message，避免真实的资源服务与 HTTP 调用。"""

    appid = '10000'

    def __init__(self):
        self.bot = None
        self.api = FakeAPI()
        self.seq_service = SeqService()
        self.sent = []

    def __str__(self):
        return 'QQGroup'

    async def send_event_message(self, chain, event_id='', is_sync=True):
        payloads = await PayloadBuilder(self.api, chain, self.seq_service).build()
        self.sent.append(
            {
                'chain': chain,
                'data': chain.data,
                'event_id': event_id,
                'payloads': payloads,
            }
        )
        return payloads


def make_message(instance, message_id='', event_id='', direct=False):
    data = Message(instance)
    data.message_id = message_id
    data.event_id = event_id
    data.channel_openid = 'GROUP_OPENID'
    data.user_openid = 'USER_OPENID'
    data.is_direct = direct
    return data


async def build_payloads(chain, instance, seq_service=None):
    return await PayloadBuilder(instance.api, chain, seq_service or SeqService()).build()


@pytest.mark.asyncio
async def test_group_event_reply_payload():
    instance = FakeInstance()

    keyboard = InlineKeyboard()
    keyboard.add_row().add_button(button='btn_1', render_label='按钮', action_type=1, action_data='callback')

    event = Event(instance, 'INTERACTION_CREATE', dict(GROUP_EVENT))
    chain = Chain(at=False).markdown_content('野地秘行是能天使的第一套皮肤。', keyboard=keyboard)

    await event.reply(chain)

    sent = instance.sent[0]
    assert sent['event_id'] == 'EVENT_ID'

    data = sent['data']
    assert data.event_id == 'EVENT_ID'
    assert data.message_id == ''
    assert data.channel_openid == 'GROUP_OPENID'
    assert data.channel_id == 'GROUP_ID'
    assert data.user_openid == 'MEMBER_OPENID'
    assert data.is_direct is False

    assert len(sent['payloads']) == 1

    payload = sent['payloads'][0]
    assert payload['msg_type'] == 2
    assert payload['markdown'] == {'content': '野地秘行是能天使的第一套皮肤。'}
    assert payload['keyboard'] == {'content': keyboard.dict()}
    assert payload['event_id'] == 'EVENT_ID'
    assert payload['msg_id'] is None
    assert payload['msg_seq'] == 1


@pytest.mark.asyncio
async def test_group_event_reply_fallback_channel_id():
    event_data = dict(GROUP_EVENT)
    event_data.pop('group_id')

    instance = FakeInstance()
    event = Event(instance, 'INTERACTION_CREATE', event_data)

    await event.reply(Chain(at=False).text('hi'))

    assert instance.sent[0]['data'].channel_id == 'GROUP_OPENID'


@pytest.mark.asyncio
async def test_c2c_event_reply():
    instance = FakeInstance()
    event = Event(instance, 'INTERACTION_CREATE', {'id': 'EVENT_C2C', 'chat_type': 2, 'user_openid': 'USER_OPENID'})

    await event.reply(Chain(at=False).markdown_content('hi'))

    data = instance.sent[0]['data']
    assert data.is_direct is True
    assert data.user_openid == 'USER_OPENID'
    assert data.channel_openid == ''
    assert data.event_id == 'EVENT_C2C'


@pytest.mark.asyncio
async def test_event_reply_seq_increments():
    instance = FakeInstance()
    event = Event(instance, 'INTERACTION_CREATE', dict(GROUP_EVENT))

    for _ in range(2):
        await event.reply(Chain(at=False).text('hi'))

    assert [item['payloads'][0]['msg_seq'] for item in instance.sent] == [1, 2]


@pytest.mark.asyncio
async def test_event_reply_limit():
    instance = FakeInstance()
    event = Event(instance, 'INTERACTION_CREATE', dict(GROUP_EVENT))

    for index in range(SeqService.EVENT_REPLY_LIMIT):
        await event.reply(Chain(at=False).text(f'message {index}'))

    assert len(instance.sent) == SeqService.EVENT_REPLY_LIMIT

    with pytest.raises(QQGroupMessageError) as context:
        await event.reply(Chain(at=False).text('the 6th'))

    assert '5' in str(context.value)
    assert context.value.code is None


@pytest.mark.asyncio
async def test_guild_event_not_supported():
    instance = FakeInstance()
    event = Event(instance, 'INTERACTION_CREATE', {'id': 'EVENT_GUILD', 'chat_type': 0, 'guild_id': 'GUILD_ID'})

    with pytest.raises(NotImplementedError):
        await event.reply(Chain(at=False).text('hi'))

    assert instance.sent == []


@pytest.mark.asyncio
async def test_adapter_without_event_support():
    class PlainInstance:
        appid = '1'

        def __str__(self):
            return 'Plain'

    event = Event(PlainInstance(), 'INTERACTION_CREATE', {'id': 'EVENT_ID'})

    with pytest.raises(NotImplementedError):
        await event.reply(Chain(at=False).text('hi'))


@pytest.mark.asyncio
async def test_unknown_scene():
    instance = FakeInstance()
    event = Event(instance, 'INTERACTION_CREATE', {'id': 'EVENT_ID'})

    with pytest.raises(ValueError):
        await event.reply(Chain(at=False).text('hi'))


@pytest.mark.asyncio
async def test_ack_interaction():
    instance = FakeInstance()
    event = Event(instance, 'INTERACTION_CREATE', dict(GROUP_EVENT))

    await event.ack_interaction()
    await event.ack_interaction(code=4)

    assert instance.api.interactions == [('EVENT_ID', 0), ('EVENT_ID', 4)]


@pytest.mark.asyncio
async def test_message_anchor_uses_msg_id():
    instance = FakeInstance()
    message = make_message(instance, message_id='MSG_ID')

    payloads = await build_payloads(Chain(message, at=False).text('hello'), instance)

    assert len(payloads) == 1
    assert payloads[0]['msg_id'] == 'MSG_ID'
    assert payloads[0]['event_id'] is None
    assert payloads[0]['msg_seq'] == 1


@pytest.mark.asyncio
async def test_event_id_anchor_wins():
    instance = FakeInstance()
    message = make_message(instance, message_id='MSG_ID', event_id='EVENT_ID')

    payloads = await build_payloads(Chain(message, at=False).text('hello'), instance)

    assert payloads[0]['event_id'] == 'EVENT_ID'
    assert payloads[0]['msg_id'] is None


@pytest.mark.asyncio
async def test_text_and_markdown_split():
    instance = FakeInstance()
    message = make_message(instance, message_id='MSG_ID')

    payloads = await build_payloads(Chain(message, at=False).text('hi').markdown_content('**md**'), instance)

    assert len(payloads) == 2

    text_payload, markdown_payload = payloads
    assert text_payload['content'] == 'hi'
    assert text_payload['msg_type'] == 0
    assert text_payload['markdown'] is None

    # 平台要求传 markdown 时 content 必须为空
    assert markdown_payload['content'] == ''
    assert markdown_payload['msg_type'] == 2
    assert markdown_payload['markdown'] == {'content': '**md**'}

    assert [item['msg_seq'] for item in payloads] == [1, 2]


@pytest.mark.asyncio
async def test_send_event_message_missing_event_id():
    # 跳过 __init__（会启动资源服务），只验证入参校验
    instance = object.__new__(QQGroupBotInstance)

    chain = Chain(at=False).text('hi')
    chain.data = Message(instance)

    with pytest.raises(ValueError):
        await instance.send_event_message(chain)


@pytest.mark.asyncio
async def test_send_event_message_missing_chain_data():
    instance = object.__new__(QQGroupBotInstance)

    with pytest.raises(TypeError):
        await instance.send_event_message(Chain(at=False))


def test_send_error_code_mapping():
    class Response:
        json = {'code': 40034026, 'message': 'event_id expired'}

    with pytest.raises(QQGroupMessageError) as context:
        raise_for_send_error(Response())

    assert context.value.code == 40034026

    class UnknownResponse:
        json = {'code': 40054005, 'message': 'duplicate message'}

    class EmptyResponse:
        json = None

    # 未映射的错误码与空响应保持原有行为（不抛异常）
    raise_for_send_error(UnknownResponse())
    raise_for_send_error(EmptyResponse())
    raise_for_send_error(None)
