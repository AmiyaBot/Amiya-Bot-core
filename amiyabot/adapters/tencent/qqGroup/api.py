import json
import time
import requests

from typing import Optional
from amiyabot.network.httpRequests import http_requests
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol
from amiyabot.log import LoggerManager

log = LoggerManager('Tencent')


class QQGroupAPI(BotInstanceAPIProtocol):
    def __init__(self, appid: str, client_secret: str):
        self.appid = appid
        self.client_secret = client_secret
        self.access_token = ''
        self.expires_time = 0

    @property
    def headers(self):
        if not self.access_token or self.expires_time - time.time() <= 60:
            try:
                res = requests.post(
                    url='https://bots.qq.com/app/getAppAccessToken',
                    data=json.dumps(
                        {
                            'appId': self.appid,
                            'clientSecret': self.client_secret,
                        }
                    ),
                    headers={
                        'Content-Type': 'application/json',
                    },
                )
                data = json.loads(res.text)

                self.access_token = data['access_token']
                self.expires_time = int(time.time()) + int(data['expires_in'])

            except Exception as e:
                log.error(e, desc='accessToken requests error:')

        return {
            'Authorization': f'QQBot {self.access_token}',
            'X-Union-Appid': f'{self.appid}',
        }

    @property
    def domain(self):
        return 'https://api.sgroup.qq.com'

    async def get(self, url: str, params: Optional[dict] = None, *args, **kwargs):
        return await http_requests.get(
            self.domain + url,
            params,
            headers=self.headers,
        )

    async def post(self, url: str, payload: Optional[dict] = None, *args, **kwargs):
        return await http_requests.post(
            self.domain + url,
            payload,
            headers=self.headers,
        )

    async def request(self, url: str, method: str, payload: Optional[dict] = None, *args, **kwargs):
        return await http_requests.request(
            self.domain + url,
            method,
            data=payload,
            headers=self.headers,
        )

    async def gateway(self):
        return await self.get('/gateway')

    async def gateway_bot(self):
        return await self.get('/gateway/bot')

    async def upload_file(self, channel_openid: str, file_type: int, url: str, srv_send_msg: bool = False):
        return await self.post(
            f'/v2/groups/{channel_openid}/files',
            {
                'file_type': file_type,
                'url': url,
                'srv_send_msg': srv_send_msg,
            },
        )

    async def post_message(self, channel_openid: str, payload: dict):
        print(payload)
        res = await self.post(f'/v2/groups/{channel_openid}/messages', payload)
        print(res)
        return res

    async def delete_message(self, message_id: str, target_id: str, is_direct: bool, hidetip: bool = True):
        ...
