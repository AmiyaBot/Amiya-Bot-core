import json

from typing import Optional, Union
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol
from amiyabot.network.httpRequests import http_requests
from amiyabot.log import LoggerManager

log = LoggerManager('KOOK')


class KOOKAPI(BotInstanceAPIProtocol):
    def __init__(self, token):
        self.host = 'https://www.kookapp.cn/api/v3'
        self.token = token

    @property
    def headers(self):
        return {'Authorization': f'Bot {self.token}'}

    async def get(self, url: str, params: Optional[dict] = None, *args, **kwargs):
        return await http_requests.get(
            self.host + url,
            params,
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
            method,
            headers=self.headers,
            **kwargs,
        )

    async def get_me(self):
        return await self.get('/user/me')

    async def get_message(self, message_id: str):
        return await self.get('/message/view', params={'msg_id': message_id})

    async def get_user_info(self, user_id: str, group_id: Optional[str] = None):
        params = {'user_id': user_id}
        if group_id:
            params['guild_id'] = group_id

        return await self.get('/user/view', params=params)

    async def get_user_avatar(self, user_id: str, group_id: Optional[str] = None, *args, **kwargs) -> Optional[str]:
        res = await self.get_user_info(user_id, group_id)
        if res:
            data = json.loads(res)
            return data['data']['avatar']

    async def create_asset(self, file: Union[str, bytes]):
        return await http_requests.post_form(
            self.host + '/asset/create',
            {'file': file},
            headers=self.headers,
        )
