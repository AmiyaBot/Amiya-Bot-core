"""
QQ 群适配器打包回归测试（缺陷：全量群消息模式下 is_at 恒为 False）。

运行：python -m pytest tests/test_qq_group_package.py
（项目无测试基础设施，本文件自包含，不进入 CI 门禁，仅用于回归验证。）
"""

from unittest.mock import MagicMock

import pytest

from amiyabot.adapters.tencent.qqGroup.package import (
    FULL_MESSAGE_CREATED,
    package_qq_group_message,
    remove_at_mark,
)
from amiyabot.adapters.tencent.qqGlobal.package import package_qq_global_message
from amiyabot.builtin.message import Event, Message

GROUP_OPENID = 'GROUP_OPENID_X'


def make_message(content, mentions=None, **extra):
    message = {
        'id': 'msg_id',
        'author': {'id': 'author_id', 'username': 'alice', 'member_openid': 'member_openid'},
        'content': content,
        'group_id': 'group_id',
        'group_openid': GROUP_OPENID,
    }
    if mentions is not None:
        message['mentions'] = mentions
    message.update(extra)
    return message


def make_instance():
    instance = MagicMock()
    instance.appid = 'appid'
    return instance


FULL = FULL_MESSAGE_CREATED[0]

pytestmark = pytest.mark.asyncio

# (名称, event, mentions, content, 期望 is_at, 期望 is_at_all, 期望 text, 期望 at_target)
CASES = [
    ('@机器人', FULL, [{'id': 'A', 'username': 'uA'}], '<@!BOT_ID> 你好', True, False, '你好', ['A']),
    ('不@', FULL, [], '今天天气不错', False, False, '今天天气不错', []),
    ('@群友', FULL, [{'id': 'A', 'username': 'uA'}], '<@A> 你看这个', False, False, '你看这个', ['A']),
    ('@全体', FULL, [], '<@all> 开会', False, True, '开会', []),
    ('纯@无正文', FULL, [], '<@BOT_ID>', True, False, '', []),
    ('旧事件回归', 'GROUP_AT_MESSAGE_CREATE', [], '你好', True, False, '你好', []),
]


@pytest.mark.parametrize('name,event,mentions,content,is_at,is_at_all,text,at_target', CASES)
async def test_package_cases(name, event, mentions, content, is_at, is_at_all, text, at_target):
    data = await package_qq_group_message(make_instance(), event, make_message(content, mentions))

    assert isinstance(data, Message)
    assert data.is_at is is_at, name
    assert data.is_at_all is is_at_all, name
    assert data.text == text, name
    assert data.at_target == at_target, name


async def test_full_message_text_has_no_at_mark_residue():
    data = await package_qq_group_message(
        make_instance(),
        FULL,
        make_message('<@A> <@!BOT> <@all> <@B> 都来看看', [{'id': 'A'}, {'id': 'B'}]),
    )
    assert '<@' not in data.text
    assert data.is_at is True
    assert data.is_at_all is True
    assert data.at_target == ['A', 'B']


async def test_mentions_carrying_bot_entry():
    """平台将来在 mentions 携带机器人自身（bot=True）时按条目直接判定，且不计入 at_target"""
    data = await package_qq_group_message(
        make_instance(),
        FULL,
        make_message('<@BOT_ID> 查天气', [{'id': 'BOT_ID', 'bot': True}, {'id': 'A'}]),
    )
    assert data.is_at is True
    assert data.text == '查天气'
    assert data.at_target == ['A']


async def test_at_mark_variants():
    data = await package_qq_group_message(make_instance(), FULL, make_message('<@BOT_ID>你好'))
    assert data.is_at is True and data.text == '你好'


async def test_c2c_regression():
    data = await package_qq_group_message(
        make_instance(),
        'C2C_MESSAGE_CREATE',
        {
            'id': 'm',
            'author': {'id': 'u', 'user_openid': 'uo'},
            'content': '你好',
        },
    )
    assert data.is_direct is True
    assert data.is_at is False  # 与 2.1.3 现状一致，不在本缺陷范围内改动
    assert data.text == '你好'


async def test_qq_global_delegates():
    data = await package_qq_global_message(make_instance(), FULL, make_message('<@!BOT_ID> 你好', [{'id': 'A'}]))
    assert isinstance(data, Message)
    assert data.is_at is True
    assert data.text == '你好'
    assert data.channel_openid == GROUP_OPENID


async def test_other_event_still_event():
    assert isinstance(
        await package_qq_group_message(make_instance(), 'GROUP_JOIN_REQUEST', {}),
        Event,
    )


async def test_remove_at_mark_pure_function():
    data = Message(make_instance())
    text = remove_at_mark(data, '<@A> <@all> <@!BOT> hi', [{'id': 'A'}])
    assert text.strip() == 'hi'  # 纯函数不去空白，set_text 才负责 strip
    assert data.is_at is True and data.is_at_all is True and data.at_target == ['A']


async def test_old_event_mentions_still_collected():
    """GROUP_AT_MESSAGE_CREATE 的 mentions 照旧计入 at_target，文本不做 @ 标记剔除（零行为变化）"""
    data = await package_qq_group_message(
        make_instance(),
        'GROUP_AT_MESSAGE_CREATE',
        make_message('<@A> 你好', [{'id': 'A'}, {'id': 'B'}]),
    )
    assert data.at_target == ['A', 'B']
    assert data.is_at is True
    assert data.text == '<@A> 你好'


# ===== 评审补充用例（PR #122 review）=====


async def test_at_mark_with_non_word_openid():
    """openid 含非 \\w 字符（如 -）时仍能识别与剔除（评审 P2-1）"""
    data = await package_qq_group_message(make_instance(), FULL, make_message('<@A-BCDEF> hi'))
    assert data.is_at is True and data.text == 'hi'

    data2 = await package_qq_group_message(make_instance(), FULL, make_message('<@A-BCDEF> 你看', [{'id': 'A-BCDEF'}]))
    assert data2.is_at is False and data2.at_target == ['A-BCDEF'] and data2.text == '你看'


async def test_at_all_bang_form():
    """<@!all> 是 @全体而非 @机器人（评审 P2-2）"""
    data = await package_qq_group_message(make_instance(), FULL, make_message('<@!all> 开会'))
    assert data.is_at is False and data.is_at_all is True and data.text == '开会'

    mixed = await package_qq_group_message(make_instance(), FULL, make_message('<@!BOT><@!all> 开会'))
    assert mixed.is_at is True and mixed.is_at_all is True and mixed.text == '开会'


async def test_full_message_without_content_key():
    """纯附件消息无 content 键时，mentions 的 at_target 收集与 @ 判定仍执行（评审 P3-4）"""
    message = make_message('', [{'id': 'A'}])
    del message['content']
    data = await package_qq_group_message(make_instance(), FULL, message)
    assert data.at_target == ['A'] and data.is_at is False and data.text == ''

    message2 = make_message('', [{'id': 'A'}])
    del message2['content']
    data2 = await package_qq_group_message(make_instance(), FULL, {**message2, 'content': ''})  # content 为空串同理
    assert data2.at_target == ['A']
