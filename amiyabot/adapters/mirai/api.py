import json

from amiyabot.log import LoggerManager
from amiyabot.network.httpRequests import http_requests
from amiyabot.adapters import BotAdapterProtocol

from .._adapterApi import BotAdapterAPI, BotAdapterType
from .payload import HttpAdapter

log = LoggerManager('Mirai')


class MiraiAPI(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.MIRAI)

    async def upload(self, interface: str, field_type: str, file: bytes, msg_type: str):
        res = await http_requests.post_upload(self.url + interface, file, file_field=field_type, payload={
            'sessionKey': self.session,
            'type': msg_type
        })
        if res:
            return json.loads(res)

    async def upload_image(self, file: bytes, msg_type: str):
        res = await self.upload('/uploadImage', 'img', file, msg_type)
        if res and 'imageId' in res:
            return res['imageId']

    async def upload_voice(self, file: bytes, msg_type: str):
        res = await self.upload('/uploadVoice', 'voice', file, msg_type)
        if res and 'voiceId' in res:
            return res['voiceId']

    async def send_group_message(self, group_id: str, chain_list: list):
        return await self.post(*HttpAdapter.group_message(self.session, group_id, chain_list))

    async def send_nudge(self, user_id: str, group_id: str):
        await self.post(*HttpAdapter.nudge(self.session, user_id, group_id))
