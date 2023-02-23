import json

from amiyabot.log import LoggerManager
from amiyabot.network.httpRequests import http_requests

from .payload import HttpAdapter

log = LoggerManager('Mirai')


class MiraiAPI:
    def __init__(self, address: str, session: str = None):
        self.address = address
        self.session = session

    @classmethod
    def __json(cls, interface, res):
        try:
            response = json.loads(res)
            if response['code'] != 0:
                log.error(f'interface </{interface}> response: {response}')
                return None
            return response
        except json.decoder.JSONDecodeError:
            return res

    def __url(self, interface):
        return f'http://{self.address}/{interface}'

    async def get(self, interface):
        res = await http_requests.get(self.__url(interface))
        if res:
            return self.__json(interface, res)

    async def post(self, interface, data=None):
        res = await http_requests.post(self.__url(interface), data)
        if res:
            return self.__json(interface, res)

    async def upload(self, interface, field_type, file, msg_type):
        res = await http_requests.post_upload(self.__url(interface), file, file_field=field_type, payload={
            'sessionKey': self.session,
            'type': msg_type
        })
        if res:
            return json.loads(res)

    async def upload_image(self, file, msg_type):
        res = await self.upload('uploadImage', 'img', file, msg_type)
        if 'imageId' in res:
            return res['imageId']

    async def upload_voice(self, file, msg_type):
        res = await self.upload('uploadVoice', 'voice', file, msg_type)
        if 'voiceId' in res:
            return res['voiceId']

    async def get_group_list(self):
        response = await self.get(f'groupList?sessionKey={self.session}')
        if response:
            group_list = {}
            for item in response['data']:
                if item['id'] not in group_list:
                    group_list[item['id']] = {
                        'group_id': item['id'],
                        'group_name': item['name'],
                        'permission': item['permission']
                    }
            group_list = [n for i, n in group_list.items()]
            return group_list
        return []

    async def leave_group(self, group_id):
        await self.post('quit', {
            'sessionKey': self.session,
            'target': group_id
        })

    async def send_group_message(self, group_id, chain_list):
        await self.post('sendGroupMessage', {
            'sessionKey': self.session,
            'target': group_id,
            'messageChain': chain_list
        })

    async def send_nudge(self, user_id, group_id):
        await self.post(*HttpAdapter.nudge(self.session, user_id, group_id))

    async def mute(self, user_id, group_id, time: int):
        await self.post(*HttpAdapter.mute(self.session, group_id, user_id, time))
