"""
https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/interface-framework/event-emit.html#websocket-%E6%96%B9%E5%BC%8F
"""

import enum


class IntentsClass(enum.Enum):
    @classmethod
    def calc(cls):
        intent = 0
        for item in cls:
            intent |= item.value
        return intent


class CommonIntents(IntentsClass):
    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_MESSAGE_REACTIONS = 1 << 10
    DIRECT_MESSAGE = 1 << 12
    INTERACTION = 1 << 26
    MESSAGE_AUDIT = 1 << 27
    AUDIO_ACTION = 1 << 29


class PublicIntents(IntentsClass):
    PUBLIC_GUILD_MESSAGES = 1 << 30


class PrivateIntents(IntentsClass):
    GUILD_MESSAGES = 1 << 9
    FORUMS_EVENT = 1 << 28


class GroupIntents(IntentsClass):
    GROUP_AND_C2C_EVENT = 1 << 25


class GroupMemberIntents(IntentsClass):
    # 群成员事件（如入群申请 GROUP_JOIN_REQUEST），需在管理端申请权限后订阅，
    # 无权限却订阅会导致 WebSocket 被服务端关闭（close code 4014）
    GROUP_MEMBER_EVENT = 1 << 24


def get_intents(private: bool, name: str, subscribe_group_member_event: bool = False) -> int:
    if name == 'QQGroup':
        res = GroupIntents.calc() | CommonIntents.INTERACTION.value
    else:
        res = CommonIntents.calc()

        if private:
            res |= PrivateIntents.calc()
        else:
            res |= PublicIntents.calc()

        if name == 'QQGlobal':
            res |= GroupIntents.calc()

    if subscribe_group_member_event:
        res |= GroupMemberIntents.calc()

    return res
