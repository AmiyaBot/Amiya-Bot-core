import json
import asyncio
import websockets

from typing import Optional
from amiyabot.adapters import BotAdapterProtocol, HANDLER_TYPE
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.log import LoggerManager

from .forwardMessage import MiraiForwardMessage
from .package import package_mirai_message
from .builder import build_message_send, MiraiMessageCallback
from .api import MiraiAPI

log = LoggerManager('Mirai')


def mirai_api_http(host: str, ws_port: int, http_port: int):
    def adapter(appid: str, token: str):
        return MiraiBotInstance(appid, token, host, ws_port, http_port)

    return adapter


class MiraiBotInstance(BotAdapterProtocol):
    def __init__(self, appid: str, token: str, host: str, ws_port: int, http_port: int):
        super().__init__(appid, token)

        self.url = f'ws://{host}:{ws_port}/all?verifyKey={token}&&qq={appid}'

        self.connection: Optional[websockets.WebSocketClientProtocol] = None

        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port

        self.session = None

    def __str__(self):
        return 'Mirai'

    @property
    def api(self):
        return MiraiAPI(self.host, self.http_port, self.session)

    async def close(self):
        log.info(f'closing {self}(appid {self.appid})...')
        self.keep_run = False

        if self.connection:
            await self.connection.close()

    async def start(self, handler: HANDLER_TYPE):
        while self.keep_run:
            await self.keep_connect(handler)
            await asyncio.sleep(10)

    async def keep_connect(self, handler: HANDLER_TYPE):
        mark = f'websocket({self.appid})'

        async with self.get_websocket_connection(mark, self.url) as websocket:
            if websocket:
                log.info(f'{mark} connect successful. waiting handshake...')
                self.connection = websocket

                while self.keep_run:
                    message = await websocket.recv()

                    if message == b'':
                        await websocket.close()
                        log.warning(f'{mark} mirai-api-http close the connection.')
                        return None

                    await self.handle_message(str(message), handler)

                await websocket.close()

    async def handle_message(self, message: str, handler: HANDLER_TYPE):
        async with log.catch(ignore=[json.JSONDecodeError]):
            data = json.loads(message)
            data = data['data']

            if 'session' in data:
                self.session = data['session']
                log.info(f'websocket({self.appid}) handshake successful. session: ' + self.session)
                return None

            asyncio.create_task(
                handler(
                    package_mirai_message(self, self.appid, data),
                ),
            )

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        reply, voice_list = await build_message_send(self.api, chain, use_http=is_sync)

        res = []

        for reply_list in [[reply], voice_list]:
            for item in reply_list:
                if is_sync:
                    request = await self.api.post('/' + item[0], item[1])
                    res.append(request)
                else:
                    await self.connection.send(item[1])

        return [MiraiMessageCallback(chain.data, self, item) for item in res]

    async def build_active_message_chain(self, chain: Chain, user_id: str, channel_id: str, direct_src_guild_id: str):
        data = Message(self)

        data.user_id = user_id
        data.channel_id = channel_id
        data.message_type = 'group'

        if not channel_id and not user_id:
            raise TypeError('send_message() missing argument: "channel_id" or "user_id"')

        if not channel_id and user_id:
            data.message_type = 'friend'
            data.is_direct = True

        message = Chain(data)
        message.chain = chain.chain
        message.builder = chain.builder

        return message

    async def recall_message(self, message_id: str, data: Optional[Message] = None):
        await self.api.post(
            '/recall',
            {
                'messageId': message_id,
                'target': data.channel_id or data.user_id,
            },
        )
