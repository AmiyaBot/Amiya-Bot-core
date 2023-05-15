import json

from typing import Hashable, Union, Optional
from amiyabot.log import LoggerManager
from amiyabot.network.httpRequests import http_requests

from .payload import HttpAdapter

log = LoggerManager('Mirai')


class MiraiAPI:
    def __init__(self, address: str, session: str = None):
        self.address = address
        self.session = session

    @classmethod
    def __json(cls, interface: str, res: str) -> Optional[Union[dict, str]]:
        try:
            response = json.loads(res)
            if response['code'] != 0:
                log.error(f'interface </{interface}> response: {response}')
                return None
            return response
        except json.decoder.JSONDecodeError:
            return res

    def __url(self, interface: str):
        return f'http://{self.address}/{interface}'

    async def get(self, interface: str):
        res = await http_requests.get(self.__url(interface))
        if res:
            return self.__json(interface, res)

    async def post(self, interface: str, data: Hashable = None):
        res = await http_requests.post(self.__url(interface), data)
        if res:
            return self.__json(interface, res)

    async def upload(self, interface: str, field_type: str, file: bytes, msg_type: str):
        res = await http_requests.post_upload(self.__url(interface), file, file_field=field_type, payload={
            'sessionKey': self.session,
            'type': msg_type
        })
        if res:
            return json.loads(res)

    async def upload_image(self, file: bytes, msg_type: str):
        res = await self.upload('uploadImage', 'img', file, msg_type)
        if res and 'imageId' in res:
            return res['imageId']

    async def upload_voice(self, file: bytes, msg_type: str):
        res = await self.upload('uploadVoice', 'voice', file, msg_type)
        if res and 'voiceId' in res:
            return res['voiceId']

    async def get_group_list(self):
        response: dict = await self.get(f'groupList?sessionKey={self.session}')
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

    async def send_group_message(self, group_id: str, chain_list: list):
        return await self.post(*HttpAdapter.group_message(self.session, group_id, chain_list))

    async def leave_group(self, group_id: str):
        await self.post('quit', {
            'sessionKey': self.session,
            'target': group_id
        })

    async def recall_message(self, message_id: str, target_id: str = None):
        await self.post('recall', {
            'sessionKey': self.session,
            'messageId': message_id,
            'target': target_id
        })

    async def send_nudge(self, user_id: str, group_id: str):
        await self.post(*HttpAdapter.nudge(self.session, user_id, group_id))

    async def mute(self, user_id: str, group_id: str, time: int):
        await self.post(*HttpAdapter.mute(self.session, group_id, user_id, time))
