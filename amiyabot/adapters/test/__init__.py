import json
import asyncio
import websockets

from typing import Callable
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.builtin.message import Message, Event
from amiyabot.builtin.messageChain import Chain
from amiyabot.log import LoggerManager

from ..convert import text_convert
from .builder import build_message_send

log = LoggerManager('Test')


def test_instance(host: str, port: int):
    def adapter(appid: str, _):
        return TestInstance(appid, host, port)

    return adapter


class TestInstance(BotAdapterProtocol):
    def __init__(self, appid: str, host: str, port: int):
        super().__init__(appid, '')

        self.url = f'ws://{host}:{port}/channel/bot/{appid}'

        self.connection: websockets.WebSocketClientProtocol = None

    def __str__(self):
        return 'Testing'

    async def close(self):
        log.info(f'closing {self}(appid {self.appid})...')
        self.keep_run = False
        if self.connection:
            await self.connection.close()

    async def connect(self, private: bool, handler: Callable):
        while self.keep_run:
            await self.keep_connect(handler)
            await asyncio.sleep(10)

    async def keep_connect(self, handler):
        mark = f'websocket({self.appid})'

        log.info(f'connecting {mark}...')
        try:
            async with websockets.connect(self.url) as websocket:
                log.info(f'{mark} connect successful.')
                self.connection = websocket
                self.set_alive(True)

                while self.keep_run:
                    message = await websocket.recv()

                    if message == b'':
                        await websocket.close()
                        log.warning(f'{mark} test server close the connection.')
                        return False

                    async with log.catch(ignore=[json.JSONDecodeError]):
                        data = json.loads(message)
                        asyncio.create_task(handler(data['event'], data['event_data']))

                await websocket.close()

                self.set_alive(False)
                log.info(f'{mark} closed.')

        except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError, websockets.InvalidStatusCode) as e:
            log.error(f'{mark} connection closed. {e}')
        except ConnectionRefusedError:
            log.error(f'cannot connect to test server {mark}.')

    async def send_message(self, chain: Chain, **kwargs):
        await self.send_chain_message(chain)

    async def send_chain_message(self, chain: Chain):
        reply, voice_list = await build_message_send(chain)

        if reply:
            await self.connection.send(reply)

        if voice_list:
            for voice in voice_list:
                await self.connection.send(voice)

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
