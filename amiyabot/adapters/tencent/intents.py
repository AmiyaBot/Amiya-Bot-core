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


def get_intents(private: bool, name: str) -> int:
    if name == 'QQGroup':
        return GroupIntents.calc()

    res = CommonIntents.calc()

    if private:
        res |= PrivateIntents.calc()
    else:
        res |= PublicIntents.calc()

    if name == 'QQGlobal':
        res |= GroupIntents.calc()

    return res
