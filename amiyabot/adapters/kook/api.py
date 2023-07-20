from typing import Optional
from amiyabot.log import LoggerManager
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters._adapterApi.define import GroupId
from amiyabot.network.download import download_async
from .._adapterApi import BotAdapterAPI, BotAdapterType, UserId

log = LoggerManager('KOOK')


class KOOKAPI(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.KOOK)

    async def get_user_info(
        self,
        user_id: UserId,
        group_id: Optional[GroupId] = None,
    ) -> Optional[dict]:
        """获取用户信息

        Args:
            user_id (UserId): 用户ID
            group_id (GroupId, optional): 群组ID. Defaults to None.

        Returns:
            Optional[dict]: 用户信息
        """
        params = {'user_id': user_id}
        if group_id:
            params['guild_id'] = group_id
        res = await self.get('/user/view', params=params)
        if res.data:
            return res.data.get('data')
        return None

    async def get_user_avatar(self, user_id: UserId, **kwargs) -> Optional[bytes]:
        """获取用户头像

        Args:
            user_id (UserId): 用户ID
            guild_id (str): 服务器ID

        Returns:
            Optional[bytes]: 头像数据
        """
        user_id = int(user_id)
        params = {'user_id': user_id}
        if kwargs.get('guild_id'):
            params['guild_id'] = kwargs['guild_id']
        res = await self.get('/user/view', params=params)
        if res.data:
            url = res.data['data']['avatar']
            data = await download_async(url)
            return data
        return None

    async def send_group_notice(self, group_id: GroupId, content: str, **kwargs) -> Optional[bool]:
        return None

    async def send_nudge(self, user_id: UserId, group_id: GroupId) -> Optional[bool]:
        return None
