import random
from typing import Optional
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters._adapterApi.define import GroupId, UserId
from .._adapterApi import BotAdapterAPI, BotAdapterType, RelationType, UserId
from .._adapterApi.define import GroupId


class TencentAPIExtra(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.TENCENT)

    async def get_user_avatar(self, user_id: UserId, **kwargs) -> Optional[bytes]:
        return await super().get_user_avatar(user_id, **kwargs)

    async def send_group_notice(self, group_id: GroupId, content: str, **kwargs) -> Optional[bool]:
        return await super().send_group_notice(group_id, content, **kwargs)

    async def send_nudge(self, user_id: UserId, group_id: GroupId):
        return await super().send_nudge(user_id, group_id)

    async def get_role_list(self, guild_id: GroupId):
        res = await self.get(f'/guilds/{guild_id}/roles')
        if res.status != 200:
            return None
        if res.data:
            return res.data

    async def set_user_role(self, guild_id: GroupId, user_id: UserId, role_id: str, channel_id: Optional[str] = None):
        if role_id == '5':
            res = await self.request(
                f'/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
                method='put',
                json={'channel_id': channel_id}
            )
        else:
            res = await self.request(f'/guilds/{guild_id}/members/{user_id}/roles/{role_id}', method='put')
        if res.status != 200:
            return None
        if res.data:
            return res.data

    async def delete_user_role(self, guild_id: GroupId, user_id: UserId, role_id: str):
        res = await self.request(f'/guilds/{guild_id}/members/{user_id}/roles/{role_id}', method='delete')
        if res.status != 200:
            return None
        if res.data:
            return res.data

    async def create_role(self, guild_id: GroupId, name: str, color: Optional[int] = None, hoist: int = 0):
        if not color:
            color = 4285110493
        res = await self.request(
            f'/guilds/{guild_id}/roles',
            method='post',
            json={'name': name, 'color': color, 'hoist': hoist}
        )
        if res.status != 200:
            return None
        if res.data:
            return res.data

    async def update_role(
        self,
        guild_id: GroupId,
        role_id: str,
        name: str,
        color: Optional[int] = None,
        hoist: int = 0
    ):
        res = await self.request(
            f'/guilds/{guild_id}/roles/{role_id}',
            method='patch',
            json={'name': name, 'color': color, 'hoist': hoist}
        )
        if res.status != 200:
            return None
        if res.data:
            return res.data

    async def delete_role(self, guild_id: GroupId, role_id: str):
        res = await self.request(f'/guilds/{guild_id}/roles/{role_id}', method='delete')
        if res.status != 200:
            return None
        if res.data:
            return res.data
