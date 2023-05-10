import json

from typing import Union, Hashable
from amiyabot.network.httpRequests import http_requests


class CQHttpAPI:
    def __init__(self, address: str, token: str):
        self.address = address
        self.headers = {
            'Authorization': f'Bearer {token}'
        }

    @classmethod
    def __json(cls, res: str) -> Union[dict, str]:
        try:
            return json.loads(res)
        except json.decoder.JSONDecodeError:
            return res

    def __url(self, interface: str):
        return f'http://{self.address}/{interface}'

    async def get(self, interface: str):
        res = await http_requests.get(self.__url(interface), headers=self.headers)
        if res:
            return self.__json(res)

    async def post(self, interface: str, data: Hashable = None):
        res = await http_requests.post(self.__url(interface), data, headers=self.headers)
        if res:
            return self.__json(res)

    async def send_cq_code(self, user_id: str, group_id: str = '', code: str = ''):
        await self.post('send_msg', {
            'message_type': 'group' if group_id else 'private',
            'user_id': user_id,
            'group_id': group_id,
            'message': code
        })

    async def send_group_forward_msg(self, group_id: str, forward_node: list):
        return await self.post('send_group_forward_msg', {
            'group_id': group_id,
            'messages': forward_node
        })

    async def send_nudge(self, user_id: str, group_id: str):
        await self.send_cq_code(user_id, group_id, f'[CQ:poke,qq={user_id}]')
