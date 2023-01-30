import json

from amiyabot.network.httpRequests import http_requests


class CQHttpAPI:
    def __init__(self, address: str, token: str):
        self.address = address
        self.headers = {
            'Authorization': f'Bearer {token}'
        }

    @classmethod
    def __json(cls, res):
        try:
            return json.loads(res)
        except json.decoder.JSONDecodeError:
            return res

    def __url(self, interface):
        return f'http://{self.address}/{interface}'

    async def get(self, interface):
        res = await http_requests.get(self.__url(interface), headers=self.headers)
        if res:
            return self.__json(res)

    async def post(self, interface, data=None):
        res = await http_requests.post(self.__url(interface), data, headers=self.headers)
        if res:
            return self.__json(res)

    async def send_group_forward_msg(self, group_id: int, forward_node: list):
        await self.post('send_group_forward_msg', {
            'group_id': group_id,
            'messages': forward_node
        })
