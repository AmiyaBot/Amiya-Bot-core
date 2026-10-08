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
    # 同时承载 C2C_MESSAGE_CREATE / GROUP_AT_MESSAGE_CREATE / GROUP_MESSAGE_CREATE(全量模式)
    GROUP_AND_C2C_EVENT = 1 << 25


class GroupMemberIntents(IntentsClass):
    """
    群成员事件（仅群/全域适配器可用）。
    GROUP_MEMBER_EVENT (1<<24) 承载 GROUP_JOIN_REQUEST 等入群申请类事件。

    ⚠️ 该 intent 需平台审批：若机器人无权限却订阅，WebSocket 会返回 4014 并直接断开连接。
    因此默认不订阅，仅在显式开启时并入。
    """

    GROUP_MEMBER_EVENT = 1 << 24


def get_intents(private: bool, name: str, subscribe_group_member_event: bool = False) -> int:
    if name == 'QQGroup':
        res = GroupIntents.calc()
        if subscribe_group_member_event:
            res |= GroupMemberIntents.calc()
        return res

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
