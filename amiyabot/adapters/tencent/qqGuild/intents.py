import abc

from typing import Type


class IntentsClass:
    @classmethod
    @abc.abstractmethod
    def get_all_intents(cls):
        raise NotImplementedError


class PublicIntents(IntentsClass):
    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_MESSAGE_REACTIONS = 1 << 10
    DIRECT_MESSAGE = 1 << 12
    INTERACTION = 1 << 26
    MESSAGE_AUDIT = 1 << 27
    AUDIO_ACTION = 1 << 29
    PUBLIC_GUILD_MESSAGES = 1 << 30

    @classmethod
    def public_intents(cls, private: bool = False):
        intent = 0
        intent |= cls.GUILDS
        intent |= cls.GUILD_MEMBERS
        intent |= cls.GUILD_MESSAGE_REACTIONS
        intent |= cls.DIRECT_MESSAGE
        intent |= cls.INTERACTION
        intent |= cls.MESSAGE_AUDIT
        intent |= cls.AUDIO_ACTION

        if not private:
            intent |= cls.PUBLIC_GUILD_MESSAGES

        return intent

    @classmethod
    def get_all_intents(cls):
        return cls.public_intents()


class PrivateIntents(PublicIntents):
    GUILD_MESSAGES = 1 << 9
    FORUMS_EVENT = 1 << 28

    @classmethod
    def get_all_intents(cls):
        intent = cls.public_intents(private=True)
        intent |= cls.GUILD_MESSAGES
        intent |= cls.FORUMS_EVENT

        return intent


class GroupIntents(IntentsClass):
    C2C_MESSAGE_CREATE = 1 << 25
    GROUP_AT_MESSAGE_CREATE = 1 << 25

    @classmethod
    def get_all_intents(cls):
        intent = 0
        intent |= cls.GROUP_AT_MESSAGE_CREATE

        return intent


def get_intents(private: bool, name: str) -> Type[IntentsClass]:
    if name == 'QQGroup':
        return GroupIntents
    return PrivateIntents if private else PublicIntents


"""
https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/interface-framework/event-emit.html#websocket-%E6%96%B9%E5%BC%8F
"""
