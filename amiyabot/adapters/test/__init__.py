from typing import Callable
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.builtin.message import Message, Event
from amiyabot.builtin.messageChain import Chain
from amiyabot.log import LoggerManager

from ..common import text_convert
from .builder import build_message_send
from .ws import TestServer

log = LoggerManager('Test')


def test_instance(host: str, port: int):
    def adapter(appid: str, _):
        return TestInstance(appid, host, port)

    return adapter


class TestInstance(BotAdapterProtocol):
    def __init__(self, appid: str, host: str, port: int):
        super().__init__(appid, '')

        self.host = host
        self.port = port

        self.server = TestServer(appid, host, port)

        @self.server.app.on_event('startup')
        async def startup():
            log.info('The test service has been started. '
                     'Please go to https://console.amiyabot.com/#/test Connect and start testing.')

    def __str__(self):
        return 'Testing'

    async def close(self):
        ...

    async def connect(self, private: bool, handler: Callable):
        await self.server.run(handler)

    async def send_message(self, chain: Chain, **kwargs):
        await self.send_chain_message(chain)

    async def send_chain_message(self, chain: Chain, use_http: bool = False):
        reply, voice_list = await build_message_send(chain)

        if reply:
            await self.server.send(reply)

        if voice_list:
            for voice in voice_list:
                await self.server.send(voice)

    async def package_message(self, event: str, data: dict):
        if event != 'message':
            return Event(self, event, data)

        text = data['message']
        msg = Message(self, data)

        msg.user_id = data['user_id']
        msg.channel_id = data['channel_id']
        msg.message_type = data['message_type']
        msg.nickname = data['nickname']
        msg.is_admin = data['is_admin']

        return text_convert(msg, text, text)

    async def recall_message(self, message_id, target_id=None):
        pass
