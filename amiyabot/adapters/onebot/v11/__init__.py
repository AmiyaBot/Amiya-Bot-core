import json
import asyncio
import websockets

from typing import Callable, Optional
from amiyabot.adapters import BotAdapterProtocol, HANDLER_TYPE
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.log import LoggerManager

from .package import package_onebot11_message
from .builder import build_message_send, OneBot11MessageCallback
from .api import OneBot11API

log = LoggerManager('OneBot11')


def onebot11(host: str, ws_port: int, http_port: int):
    def adapter(appid: str, token: str):
        return OneBot11Instance(appid, token, host, ws_port, http_port)

    return adapter


class OneBot11Instance(BotAdapterProtocol):
    def __init__(
        self,
        appid: str,
        token: str,
        host: str,
        ws_port: int,
        http_port: int,
    ):
        super().__init__(appid, token)

        self.url = f'ws://{host}:{ws_port}/'
        self.headers = {'Authorization': f'Bearer {token}'}

        self.connection: Optional[websockets.WebSocketClientProtocol] = None

        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port

    def __str__(self):
        return 'OneBot11'

    @property
    def api(self):
        return OneBot11API(self.host, self.http_port, self.token)

    async def close(self):
        log.info(f'closing {self}(appid {self.appid})...')
        self.keep_run = False

        if self.connection:
            await self.connection.close()

    async def start(self, handler: HANDLER_TYPE):
        while self.keep_run:
            await self.keep_connect(handler)
            await asyncio.sleep(10)

    async def keep_connect(self, handler: HANDLER_TYPE, package_method: Callable = package_onebot11_message):
        mark = f'websocket({self.appid})'

        async with self.get_websocket_connection(mark, self.url, self.headers) as websocket:
            if websocket:
                log.info(f'{mark} connect successful.')
                self.connection = websocket

                while self.keep_run:
                    message = await websocket.recv()

                    if message == b'':
                        await websocket.close()
                        log.warning(f'{mark} server already closed this connection.')
                        return None

                    async with log.catch(ignore=[json.JSONDecodeError]):
                        asyncio.create_task(
                            handler(
                                await package_method(self, self.appid, json.loads(message)),
                            ),
                        )

                await websocket.close()

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        reply, voice_list, cq_codes = await build_message_send(chain)

        res = []

        for reply_list in [[reply], cq_codes, voice_list]:
            for item in reply_list:
                if is_sync:
                    request = await self.api.post('/send_msg', item)
                    res.append(request)
                else:
                    await self.connection.send(json.dumps({'action': 'send_msg', 'params': item}))

        return [OneBot11MessageCallback(chain.data, self, item) for item in res]

    async def build_active_message_chain(self, chain: Chain, user_id: str, channel_id: str, direct_src_guild_id: str):
        data = Message(self)

        data.user_id = user_id
        data.channel_id = channel_id
        data.message_type = 'group'

        if not channel_id and not user_id:
            raise TypeError('send_message() missing argument: "channel_id" or "user_id"')

        if not channel_id and user_id:
            data.message_type = 'private'
            data.is_direct = True

        message = Chain(data)
        message.chain = chain.chain
        message.builder = chain.builder

        return message

    async def recall_message(self, message_id: str, data: Optional[Message] = None):
        await self.api.post('/delete_msg', {'message_id': message_id})
