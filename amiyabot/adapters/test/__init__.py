from typing import Optional

from amiyabot.adapters import BotAdapterProtocol, HANDLER_TYPE
from amiyabot.builtin.message import Message, MessageCallback
from amiyabot.builtin.messageChain import Chain
from amiyabot.log import LoggerManager

from .builder import build_message_send
from .server import TestServer

log = LoggerManager('Test')


def test_instance(host: str = '127.0.0.1', port: int = 32001):
    def adapter(appid: str, _):
        return TestInstance(appid, host, port)

    return adapter


class TestMessageCallback(MessageCallback):
    async def recall(self):
        ...

    async def get_message(self) -> Optional[Message]:
        ...


class TestInstance(BotAdapterProtocol):
    def __init__(self, appid: str, host: str, port: int):
        super().__init__(appid, '')

        self.host = host
        self.port = port

        self.server = TestServer(self, appid, host, port)

        @self.server.app.on_event('startup')
        async def startup():
            log.info(
                'The test service has been started. '
                'Please go to https://console.amiyabot.com/#/test Connect and start testing.'
            )

    def __str__(self):
        return 'Testing'

    async def close(self):
        ...

    async def start(self, handler: HANDLER_TYPE):
        await self.server.run(handler)

    async def build_active_message_chain(self, chain: Chain, user_id: str, channel_id: str, direct_src_guild_id: str):
        return chain

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        reply, voice_list = await build_message_send(chain)

        if reply:
            await self.server.send(reply)

        if voice_list:
            for voice in voice_list:
                await self.server.send(voice)

        return [TestMessageCallback(chain.data, self, None)]

    async def recall_message(self, message_id, data: Optional[Message] = None):
        ...
