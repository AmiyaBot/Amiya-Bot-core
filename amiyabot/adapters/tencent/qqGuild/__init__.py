import sys
import json
import asyncio

from websockets.legacy.client import WebSocketClientProtocol
from typing import Dict, Optional
from amiyabot.util import random_code
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.adapters import BotAdapterProtocol, HANDLER_TYPE
from amiyabot.adapters.tencent.intents import get_intents

from .api import QQGuildAPI, log
from .model import GateWay, Payload, ConnectionModel, ConnectionHandler
from .package import package_qq_guild_message
from .builder import build_message_send, QQGuildMessageCallback


def qq_guild_shards(shard_index: int, shards: int):
    def adapter(appid: str, token: str):
        return QQGuildBotInstance(appid, token, shard_index, shards)

    return adapter


class QQGuildBotInstance(BotAdapterProtocol):
    def __init__(self, appid: str, token: str, shard_index: int = 0, shards: int = 1):
        super().__init__(appid, token)

        self.appid = appid
        self.token = token
        self.shard_index = shard_index
        self.shards = shards

        self.model: Optional[ConnectionModel] = None

    def __str__(self):
        return 'QQGuild'

    @property
    def api(self):
        return QQGuildAPI(self.appid, self.token)

    @property
    def package_method(self):
        return package_qq_guild_message

    def __create_heartbeat(self, websocket, interval: int):
        heartbeat_key = random_code(10)
        self.model.heartbeat_key = heartbeat_key
        asyncio.create_task(
            self.heartbeat_interval(
                websocket,
                interval,
                heartbeat_key,
            )
        )

    async def close(self):
        log.info(f'closing {self}(appid {self.appid})...')
        self.keep_run = False

        if self.model:
            await self.model.connection.close()

    async def start(self, handler: HANDLER_TYPE):
        log.info(f'requesting appid {self.appid} gateway')

        resp = await self.api.gateway_bot()

        if not resp or 'url' not in resp.json:
            if self.keep_run:
                await asyncio.sleep(10)
                asyncio.create_task(self.start(handler))
            return False

        gateway = GateWay(**resp.json)

        log.info(
            f'appid {self.appid} gateway resp: shards {gateway.shards}, max_concurrency %d, remaining %d/%d'
            % (
                gateway.session_start_limit['max_concurrency'],
                gateway.session_start_limit['remaining'],
                gateway.session_start_limit['total'],
            )
        )

        await self.create_connection(
            ConnectionHandler(
                private=self.private,
                gateway=gateway,
                message_handler=handler,
            )
        )

    async def create_connection(self, handler: ConnectionHandler):
        gateway = handler.gateway
        sign = f'{self.appid} {self.shard_index + 1}/{self.shards}'

        async with self.get_websocket_connection(sign, gateway.url) as websocket:
            if websocket:
                self.model = ConnectionModel(connection=websocket)

                while self.keep_run:
                    await asyncio.sleep(0)

                    recv = await websocket.recv()
                    payload = Payload(**json.loads(recv))

                    if payload.op == 0:
                        if payload.t == 'READY':
                            self.bot_name = payload.d['user']['username']
                            log.info(
                                f'connected({sign}): {self.bot_name}({self}-%s)'
                                % ('private' if handler.private else 'public')
                            )
                            self.model.session_id = payload.d['session_id']
                        else:
                            await self.create_package_task(handler, payload)

                    if payload.op == 10:
                        create_token = {
                            'token': f'Bot {self.appid}.{self.token}',
                            'intents': get_intents(handler.private, self.__str__()),
                            'shard': [self.shard_index, self.shards],
                            'properties': {
                                '$os': sys.platform,
                                '$browser': '',
                                '$device': '',
                            },
                        }
                        await websocket.send(Payload(op=2, d=create_token).to_json())

                        self.__create_heartbeat(websocket, payload.d['heartbeat_interval'])

                    if payload.s:
                        self.model.last_s = payload.s

        while self.keep_run and self.model.reconnect_limit > 0:
            await self.reconnect(handler, sign)
            await asyncio.sleep(1)

    async def reconnect(self, handler: ConnectionHandler, sign: str):
        log.info(f'reconnecting({sign})...')

        async with self.get_websocket_connection(sign, handler.gateway.url) as websocket:
            if websocket:
                self.model.connection = websocket

                while self.keep_run:
                    await asyncio.sleep(0)

                    recv = await websocket.recv()
                    payload = Payload(**json.loads(recv))

                    if payload.op == 0:
                        if payload.t == 'RESUMED':
                            log.info(f'Bot reconnected({sign}).')
                        else:
                            await self.create_package_task(handler, payload)

                    if payload.op == 10:
                        reconnect_token = {
                            'token': f'Bot {self.appid}.{self.token}',
                            'session_id': self.model.session_id,
                            'seq': self.model.last_s,
                        }
                        await websocket.send(Payload(op=6, d=reconnect_token).to_json())

                        self.__create_heartbeat(websocket, payload.d['heartbeat_interval'])

                        self.model.reconnect_limit = 3

                    if payload.s:
                        self.model.last_s = payload.s

        self.model.reconnect_limit -= 1

    async def heartbeat_interval(
        self,
        websocket: WebSocketClientProtocol,
        interval: int,
        heartbeat_key: str,
    ):
        sec = 0
        while self.keep_run and self.model.heartbeat_key == heartbeat_key:
            await asyncio.sleep(1)
            sec += 1
            if sec >= interval / 1000:
                sec = 0
                await websocket.send(Payload(op=1, d=self.model.last_s).to_json())

    async def create_package_task(self, handler: ConnectionHandler, payload: Payload):
        asyncio.create_task(
            handler.message_handler(
                await self.package_method(self, payload.t, payload.d),
            ),
        )

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        reqs = await build_message_send(chain)
        res = []

        for req in reqs.req_list:
            async with log.catch('post error:', ignore=[asyncio.TimeoutError]):
                res.append(
                    await self.api.post_message(
                        chain.data.guild_id,
                        chain.data.src_guild_id,
                        chain.data.channel_id,
                        req,
                    )
                )

        return [QQGuildMessageCallback(chain.data, self, item) for item in res]

    async def build_active_message_chain(self, chain: Chain, user_id: str, channel_id: str, direct_src_guild_id: str):
        data = Message(self)

        data.user_id = user_id
        data.channel_id = channel_id

        if not channel_id and not direct_src_guild_id:
            raise TypeError('send_message() missing argument: "channel_id" or "direct_src_guild_id"')

        if direct_src_guild_id:
            if not user_id:
                raise TypeError('send_message(direct_src_guild_id=...) missing argument: "user_id"')

            data.is_direct = True
            data.src_guild_id = direct_src_guild_id

        message = Chain(data)
        message.chain = chain.chain
        message.builder = chain.builder

        return message

    async def recall_message(self, message_id: str, data: Optional[Message] = None):
        await self.api.delete_message(message_id, data.guild_id if data.is_direct else data.channel_id, data.is_direct)


class QQGuildSandboxBotInstance(QQGuildBotInstance):
    @property
    def api(self):
        return QQGuildAPI(self.appid, self.token, True)

    def __str__(self):
        return 'QQGuildSandbox'
