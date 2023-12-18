import json
import time
import requests

from amiyabot.network.httpRequests import http_requests
from amiyabot.adapters.tencent.qqGuild.api import QQGuildAPI, log


class QQGroupAPI(QQGuildAPI):
    def __init__(self, appid: str, client_secret: str):
        super().__init__(appid, '')

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
