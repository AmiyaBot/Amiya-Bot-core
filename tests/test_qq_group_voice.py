"""
QQ 群语音附件 / 发送者机器人标记的解包回归（issue #128）。

- `attachments[].asr_refer_text`（平台侧语音转写）此前被整条丢弃；
- `author.bot`（发送者是否为机器人）此前未读取，下游无法拦截机器人互相 @ 的死循环。

断言只落在「解析后的 Message 字段」与「日志渲染结果」上，不触网。
"""

from unittest.mock import MagicMock

import pytest

from amiyabot.adapters.tencent.qqGroup.package import (
    package_qq_group_message,
    parse_attachments,
)
from amiyabot.builtin.message import Message

GROUP_OPENID = 'GROUP_OPENID_X'
VOICE_URL = 'https://example.com/voice.wav'
ASR_TEXT = '银灰精二需要什么材料'


def make_instance():
    instance = MagicMock()
    instance.appid = 'appid'
    return instance


def make_data():
    return Message(make_instance(), {})


# ---------------------------------------------------------------------------
# 语音附件
# ---------------------------------------------------------------------------


def test_parse_voice_reads_asr_text():
    data = make_data()

    parse_attachments(
        data,
        {
            'attachments': [
                {
                    'content_type': 'voice',
                    'voice_wav_url': VOICE_URL,
                    'asr_refer_text': ASR_TEXT,
                }
            ]
        },
    )

    assert data.voice == VOICE_URL
    assert data.voice_text == ASR_TEXT


def test_parse_voice_without_asr_text_keeps_url():
    # 平台未转写时不能抛错，voice_text 留空、voice 照常
    data = make_data()

    parse_attachments(data, {'attachments': [{'content_type': 'voice', 'voice_wav_url': VOICE_URL}]})

    assert data.voice == VOICE_URL
    assert data.voice_text == ''


def test_parse_voice_falls_back_to_url():
    # #120 的回归：只有 url、无 voice_wav_url 时仍要取到语音地址
    data = make_data()

    parse_attachments(
        data,
        {'attachments': [{'content_type': 'voice', 'url': VOICE_URL, 'asr_refer_text': ASR_TEXT}]},
    )

    assert data.voice == VOICE_URL
    assert data.voice_text == ASR_TEXT


def test_parse_voice_asr_text_is_stripped():
    data = make_data()

    parse_attachments(
        data,
        {'attachments': [{'content_type': 'voice', 'voice_wav_url': VOICE_URL, 'asr_refer_text': f'  {ASR_TEXT}  '}]},
    )

    assert data.voice_text == ASR_TEXT


def test_parse_voice_first_attachment_wins():
    # 多个语音附件时与 data.voice 的既有语义一致：首个非空值胜出
    data = make_data()

    parse_attachments(
        data,
        {
            'attachments': [
                {'content_type': 'voice', 'voice_wav_url': VOICE_URL, 'asr_refer_text': ASR_TEXT},
                {
                    'content_type': 'voice',
                    'voice_wav_url': 'https://example.com/second.wav',
                    'asr_refer_text': '第二条',
                },
            ]
        },
    )

    assert data.voice == VOICE_URL
    assert data.voice_text == ASR_TEXT


# ---------------------------------------------------------------------------
# 发送者机器人标记
# ---------------------------------------------------------------------------


def make_message(**author_extra):
    author = {
        'id': 'author_id',
        'username': 'alice',
        'member_openid': 'member_openid',
        **author_extra,
    }
    return {
        'id': 'msg_id',
        'author': author,
        'content': '你好',
        'group_id': 'group_id',
        'group_openid': GROUP_OPENID,
    }


@pytest.mark.asyncio
async def test_author_bot_flag_true():
    data = await package_qq_group_message(make_instance(), 'GROUP_AT_MESSAGE_CREATE', make_message(bot=True))

    assert data.is_bot is True


@pytest.mark.asyncio
async def test_author_bot_flag_absent():
    data = await package_qq_group_message(make_instance(), 'GROUP_AT_MESSAGE_CREATE', make_message())

    assert data.is_bot is False


@pytest.mark.asyncio
async def test_author_bot_flag_false_value():
    data = await package_qq_group_message(make_instance(), 'GROUP_AT_MESSAGE_CREATE', make_message(bot=False))

    assert data.is_bot is False


# ---------------------------------------------------------------------------
# 日志渲染
# ---------------------------------------------------------------------------


def test_str_renders_voice():
    data = make_data()
    parse_attachments(data, {'attachments': [{'content_type': 'voice', 'voice_wav_url': VOICE_URL}]})

    assert '[voice]' in str(data)


def test_str_renders_voice_text_only():
    # 只有转写没有 URL 时也要能看出这是一条语音
    data = make_data()
    data.voice_text = ASR_TEXT

    assert '[voice]' in str(data)


def test_str_renders_video_and_files():
    data = make_data()
    parse_attachments(
        data,
        {
            'attachments': [
                {'content_type': 'video/mp4', 'url': 'https://example.com/v.mp4'},
                {'content_type': 'file', 'url': 'https://example.com/f.pdf', 'filename': 'f.pdf'},
                {'content_type': 'file', 'url': 'https://example.com/g.bin'},
            ]
        },
    )

    rendered = str(data)

    assert '[video]' in rendered
    assert '[file:f.pdf]' in rendered
    assert '[file]' in rendered


def test_str_unchanged_for_text_only():
    # 纯文本消息的渲染结果不能因为新增占位符而变化
    data = make_data()
    data.set_text('你好')

    assert str(data).endswith(': 你好')
