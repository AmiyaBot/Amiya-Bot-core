from typing import Optional
from amiyabot.adapters import BotAdapterProtocol
from .._adapterApi import BotAdapterAPI, BotAdapterType, GroupId, UserId


class OneBot12API(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.ONEBOT12)

    async def get_user_avatar(self, user_id: UserId, **kwargs) -> Optional[bytes]:
        return None

    async def send_group_notice(self, group_id: GroupId, content: str, **kwargs) -> Optional[bool]:
        return None

    async def send_nudge(self, user_id: UserId, group_id: GroupId):
        return None
