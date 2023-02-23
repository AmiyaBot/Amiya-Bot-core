import json
import asyncio
import websockets

from typing import Callable
from amiyabot.adapters import BotAdapterProtocol, MessageCallback
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain

from .forwardMessage import MiraiForwardMessage
from .package import package_mirai_message
from .builder import build_message_send
from .api import MiraiAPI, log


def mirai_api_http(host: str, ws_port: int, http_port: int):
    def adapter(appid: str, token: str):
        return MiraiBotInstance(appid, token, host, ws_port, http_port)

    return adapter


class MiraiMessageCallback(MessageCallback):
    async def recall(self):
        if not self.response:
            log.warning('can not recall message because the response is None.')
            return False
        chain: Chain = self.chain
        await self.instance.recall_message(self.response['messageId'], chain.data.channel_id or chain.data.user_id)


class MiraiBotInstance(BotAdapterProtocol):
    def __init__(self, appid: str, token: str, host: str, ws_port: int, http_port: int):
        super().__init__(appid, token)

        self.url = f'ws://{host}:{ws_port}/all?verifyKey={token}&&qq={appid}'

        self.connection: websockets.WebSocketClientProtocol = None

        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port

        self.session = None

        self.api = MiraiAPI(f'{host}:{http_port}')

    def __str__(self):
        return 'Mirai'

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
                log.info(f'{mark} connect successful. waiting handshake...')
                self.connection = websocket
                self.set_alive(True)

                while self.keep_run:
                    message = await websocket.recv()

                    if message == b'':
                        await websocket.close()
                        log.warning(f'{mark} mirai-api-http close the connection.')
                        return False

                    await self.handle_message(str(message), handler)

                await websocket.close()

                self.set_alive(False)
                log.info(f'{mark} closed.')

        except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError) as e:
            log.error(f'{mark} connection closed. {e}')
        except ConnectionRefusedError:
            log.error(f'cannot connect to mirai-api-http {mark} server.')

    async def handle_message(self, message: str, handler: Callable):
        async with log.catch(ignore=[json.JSONDecodeError]):
            data = json.loads(message)
            data = data['data']

            if 'session' in data:
                self.api.session = self.session = data['session']
                log.info(f'websocket({self.appid}) handshake successful. session: ' + self.session)
                return False

            asyncio.create_task(handler('', data))

    async def send_chain_message(self, chain: Chain, use_http: bool = False):
        reply, voice_list = await build_message_send(self.api, chain, use_http=use_http)

        res = []

        for reply_list in [[reply], voice_list]:
            for item in reply_list:
                if use_http:
                    res.append({
                        **await self.api.post(item[0], item[1])
                    })
                else:
                    await self.connection.send(item[1])

        return [MiraiMessageCallback(chain, self, item) for item in res]

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
                'MiraiBotInstance.send_message() missing argument: "channel_id" or "user_id"')

        if not channel_id and user_id:
            data.message_type = 'friend'
            data.is_direct = True

        message = Chain(data)
        message.chain = chain.chain
        message.builder = chain.builder

        return await self.send_chain_message(message)

    async def package_message(self, event: str, message: dict):
        return package_mirai_message(self, self.appid, message)

    async def recall_message(self, message_id, target_id=None):
        await self.api.post('recall', {
            'sessionKey': self.api.session,
            'messageId': message_id,
            'target': target_id
        })
