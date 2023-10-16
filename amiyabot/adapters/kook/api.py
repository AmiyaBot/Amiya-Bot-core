from typing import Optional
from amiyabot.adapters.api import BotInstanceAPIProtocol
from amiyabot.network.httpRequests import http_requests
from amiyabot.network.download import download_async


class KOOKAPI(BotInstanceAPIProtocol):
    def __init__(self, token):
        self.host = 'https://www.kookapp.cn/api/v3'
        self.token = token

    @property
    def headers(self):
        return {'Authorization': f'Bot {self.token}'}

    async def get(self, url: str, *args, **kwargs):
        return await http_requests.get(
            self.host + url,
            headers=self.headers,
            **kwargs,
        )

    async def post(self, url: str, data: Optional[dict] = None, *args, **kwargs):
        return await http_requests.post(
            self.host + url,
            data,
            headers=self.headers,
            **kwargs,
        )

    async def request(self, url: str, method: str, *args, **kwargs):
        return await http_requests.request(
            self.host + url,
            headers=self.headers,
            **kwargs,
        )

    async def get_user_info(
        self,
        user_id: str,
        group_id: Optional[str] = None,
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

    async def get_user_avatar(self, user_id: str, **kwargs) -> Optional[bytes]:
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
