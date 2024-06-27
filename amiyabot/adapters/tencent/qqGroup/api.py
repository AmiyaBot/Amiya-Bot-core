import json
import time
import requests

from ..qqGuild.api import QQGuildAPI, log


class QQGroupAPI(QQGuildAPI):
    def __init__(self, appid: str, token: str, client_secret: str):
        super().__init__(appid, token)

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
                    timeout=3,
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

    async def upload_file(
        self,
        openid: str,
        file_type: int,
        url: str,
        srv_send_msg: bool = False,
        is_direct: bool = False,
    ):
        return await self.post(
            f'/v2/users/{openid}/files' if is_direct else f'/v2/groups/{openid}/files',
            {
                'file_type': file_type,
                'url': url,
                'srv_send_msg': srv_send_msg,
            },
        )

    async def post_group_message(self, channel_openid: str, payload: dict):
        return await self.post(f'/v2/groups/{channel_openid}/messages', payload)

    async def post_private_message(self, user_openid: str, payload: dict):
        return await self.post(f'/v2/users/{user_openid}/messages', payload)
