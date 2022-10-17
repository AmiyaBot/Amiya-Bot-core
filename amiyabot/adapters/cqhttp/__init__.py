import json
import asyncio
import websockets

from typing import Callable
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.log import LoggerManager

from .package import package_cqhttp_message
from .builder import build_message_send
from .api import CQHttpAPI

log = LoggerManager('CQHttp')


def cq_http(host: str, ws_port: int, http_port: int):
    def adapter(appid: str, token: str):
        return CQHttpBotInstance(appid, token, host, ws_port, http_port)

    return adapter


class CQHttpBotInstance(BotAdapterProtocol):
    def __init__(self, appid: str, token: str, host: str, ws_port: int, http_port: int):
        super().__init__(appid, token)

        self.url = f'ws://{host}:{ws_port}/'
        self.headers = {
            'Authorization': f'Bearer {token}'
        }

        self.connection: websockets.WebSocketClientProtocol = None

        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port

        self.api = CQHttpAPI(f'{host}:{http_port}', token)

    def __str__(self):
        return 'CQHttp'

    def close(self):
        log.info(f'closing {self}(appid {self.appid})...')
        self.keep_run = False

        asyncio.create_task(self.connection.close())

    async def connect(self, private: bool, handler: Callable):
        while self.keep_run:
            await self.keep_connect(handler)
            await asyncio.sleep(10)

    async def keep_connect(self, handler):
        mark = f'websocket({self.appid})'

        log.info(f'connecting {mark}...')
        try:
            async with websockets.connect(self.url, extra_headers=self.headers) as websocket:
                log.info(f'{mark} connect successful.')
                self.connection = websocket
                self.set_alive(True)

                while self.keep_run:
                    message = await websocket.recv()

                    if message == b'':
                        await websocket.close()
                        log.warning(f'{mark} cq-http close the connection.')
                        return False

                    async with log.catch(ignore=[json.JSONDecodeError]):
                        asyncio.create_task(handler('', json.loads(message)))

                await websocket.close()

                self.set_alive(False)
                log.info(f'{mark} closed.')

        except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError, websockets.InvalidStatusCode) as e:
            log.error(f'{mark} connection closed. {e}')
        except ConnectionRefusedError:
            log.error(f'cannot connect to cq-http {mark} server.')

    async def send_chain_message(self, chain: Chain):
        reply, voice_list = await build_message_send(chain)

        if reply:
            await self.connection.send(reply)

        if voice_list:
            for voice in voice_list:
                await self.connection.send(voice)

    async def send_message(self,
                           chain: Chain,
                           user_id: str = '',
                           channel_id: str = '',
                           direct_src_guild_id: str = ''):
        data = Message(self)

        data.user_id = user_id
        data.channel_id = channel_id
        data.message_type = 'group'

        if not channel_id and not user_id:
            raise TypeError(
                'CQHttpBotInstance.send_message() missing argument: "channel_id" or "user_id"')

        if not channel_id and user_id:
            data.message_type = 'private'
            data.is_direct = True

        message = Chain(data)
        message.chain = chain.chain
        message.builder = chain.builder

        await self.send_chain_message(message)

    async def package_message(self, event: str, message: dict):
        return package_cqhttp_message(self, self.appid, message)
