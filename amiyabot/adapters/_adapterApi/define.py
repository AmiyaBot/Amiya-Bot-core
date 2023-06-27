from enum import Enum

from typing import Union

UserId = Union[str, int]
GroupId = Union[str, int]
MessageId = Union[str, int]


class BotAdapterType(Enum):
    CQHTTP = 1
    MIRAI = 2


class UserPermission(Enum):
    OWNER = 1
    ADMIN = 2
    MEMBER = 3
    UNKNOWN = 4

    @classmethod
    def from_str(cls, string: str):
        string = string.lower()
        if string == 'owner':
            return cls.OWNER
        if string == 'admin':
            return cls.ADMIN
        if string == 'member':
            return cls.MEMBER
        return cls.UNKNOWN


class UserGender(Enum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2

    @classmethod
    def from_str(cls, string: str):
        string = string.lower()
        if string == 'male':
            return cls.MALE
        if string == 'female':
            return cls.FEMALE
        return cls.UNKNOWN


class RelationType(Enum):
    FRIEND = 1
    GROUP = 2
    STRANGER = 3
