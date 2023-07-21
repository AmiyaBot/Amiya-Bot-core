from typing import Optional
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters._adapterApi.define import GroupId
from amiyabot.network.download import download_async
from .._adapterApi import BotAdapterAPI, BotAdapterType, UserId


class KOOKAPI(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.KOOK)

    async def get_user_avatar(self, user_id: UserId, **kwargs) -> Optional[bytes]:
        """获取用户头像

        Args:
            user_id (UserId): 用户ID
            guild_id (str): 服务器ID

        Returns:
            Optional[bytes]: 头像数据
        """
        params = {'user_id': user_id}
        if kwargs.get('guild_id'):
            params['guild_id'] = kwargs['guild_id']
        res = await self.get('/user/view', params=params)
        if res.data:
            url = res.data['avatar']
            data = await download_async(url)
            return data
        return None

    async def send_group_notice(self, group_id: GroupId, content: str, **kwargs) -> Optional[bool]:
        return None

    async def send_nudge(self, user_id: UserId, group_id: GroupId) -> Optional[bool]:
        return None
