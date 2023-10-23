from typing import Optional
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol
from amiyabot.network.httpRequests import http_requests


class OneBot12API(BotInstanceAPIProtocol):
    def __init__(self, host: str, port: int, token: str):
        self.token = token
        self.host = f'http://{host}:{port}'

    @property
    def headers(self):
        return {'Authorization': f'Bearer {self.token}'}

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
            method,
            headers=self.headers,
            **kwargs,
        )
