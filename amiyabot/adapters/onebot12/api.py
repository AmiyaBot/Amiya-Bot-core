from typing import Optional
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol, UnsupportedMethod
from amiyabot.network.httpRequests import http_requests


class OneBot12API(BotInstanceAPIProtocol):
    def __init__(self, host: str, port: int, token: str):
        self.token = token
        self.host = f'http://{host}:{port}'

    @property
    def headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    @staticmethod
    def ob12_action(action: str, params: dict):
        return {'action': action.strip('/'), 'params': params}

    async def get(self, url: str, params: Optional[dict] = None, *args, **kwargs):
        raise UnsupportedMethod('Unsupported "get" method')

    async def post(self, url: str, data: Optional[dict] = None, *args, **kwargs):
        return await http_requests.post(
            self.host + url,
            data,
            headers=self.headers,
            **kwargs,
        )

    async def request(self, url: str, method: str, *args, **kwargs):
        raise UnsupportedMethod(f'Unsupported "{method}" method')

    async def get_file(self, file_id: str, file_type: str = 'url'):
        res = await self.post('/', self.ob12_action('get_file', {'file_id': file_id, 'type': file_type}))
        if res:
            data = res.json
            if data['status'] == 'ok':
                return data['data'].get(file_type)
