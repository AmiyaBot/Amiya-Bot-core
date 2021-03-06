import json
import asyncio
import websockets

from typing import Dict
from amiyabot import log
from amiyabot.util import random_code
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from contextlib import asynccontextmanager

from .api import TencentAPI
from .model import GateWay, Payload, ShardsRecord, ConnectionHandler
from .intents import Intents
from .package import package_tencent_message
from .builder import build_message_send

from .. import BotAdapterProtocol


@asynccontextmanager
async def ws(sign, url):
    async with log.catch(f'connection({sign}) error:',
                         ignore=[asyncio.CancelledError, websockets.ConnectionClosedError]):
        async with websockets.connect(url) as websocket:
            yield websocket

    log.info(f'connection({sign}) closed.')


class TencentBotInstance(TencentAPI, BotAdapterProtocol):
    def __init__(self, appid: str, token: str):
        super().__init__(appid, token)

        self.appid = appid
        self.token = token

        self.shards_record: Dict[int, ShardsRecord] = {}
        self.alive = True

    def __create_heartbeat(self, websocket, interval, record: ShardsRecord):
        heartbeat_key = random_code(10)
        record.heartbeat_key = heartbeat_key
        asyncio.create_task(
            self.heartbeat_interval(websocket,
                                    interval,
                                    record.shards_index,
                                    heartbeat_key)
        )

    async def create_connection(self, handler: ConnectionHandler, shards_index: int = 0):
        gateway = handler.gateway
        sign = f'{self.appid} {shards_index + 1}/{gateway.shards}'

        log.info(f'connecting({sign})...')

        async with ws(sign, gateway.url) as websocket:
            self.shards_record[shards_index] = ShardsRecord(shards_index)

            while self.alive:
                await asyncio.sleep(0)

                recv = await websocket.recv()
                payload = Payload(**json.loads(recv))

                if payload.op == 0:
                    if payload.t == 'READY':
                        log.info(
                            f'Bot connected({sign}): %s(%s)' % (
                                payload.d['user']['username'], 'private' if handler.private else 'public'
                            )
                        )
                        self.shards_record[shards_index].session_id = payload.d['session_id']
                    else:
                        asyncio.create_task(handler.message_handler(payload.t, payload.d))

                if payload.op == 10:
                    create_token = {
                        'token': f'Bot {self.appid}.{self.token}',
                        'intents': Intents(handler.private).intents.get_all_intents(),
                        'shard': [shards_index, gateway.shards],
                        'properties': {
                            '$os': '',
                            '$browser': '',
                            '$device': ''
                        }
                    }
                    await websocket.send(Payload(op=2, d=create_token).to_dict())

                    self.__create_heartbeat(websocket,
                                            payload.d['heartbeat_interval'],
                                            self.shards_record[shards_index])

                if payload.s:
                    self.shards_record[shards_index].last_s = payload.s

        while self.shards_record[shards_index].reconnect_limit > 0:
            await self.reconnect(handler, self.shards_record[shards_index], sign)

        self.alive = False

    async def reconnect(self, handler: ConnectionHandler, record: ShardsRecord, sign: str):
        log.info(f'reconnecting({sign})...')

        async with ws(sign, handler.gateway.url) as websocket:
            while self.alive:
                await asyncio.sleep(0)

                recv = await websocket.recv()
                payload = Payload(**json.loads(recv))

                if payload.op == 0:
                    if payload.t == 'RESUMED':
                        log.info(f'Bot reconnected({sign}).')
                    else:
                        asyncio.create_task(handler.message_handler(payload.t, payload.d))

                if payload.op == 10:
                    reconnect_token = {
                        'token': f'Bot {self.appid}.{self.token}',
                        'session_id': record.session_id,
                        'seq': record.last_s
                    }
                    await websocket.send(Payload(op=6, d=reconnect_token).to_dict())

                    self.__create_heartbeat(websocket,
                                            payload.d['heartbeat_interval'],
                                            record)

                    record.reconnect_limit = 3

                if payload.s:
                    record.last_s = payload.s

        record.reconnect_limit -= 1

    async def heartbeat_interval(self,
                                 websocket: websockets.WebSocketClientProtocol,
                                 interval: int,
                                 shards_index: int,
                                 heartbeat_key: str):
        sec = 0
        while self.alive and self.shards_record[shards_index].heartbeat_key == heartbeat_key:
            await asyncio.sleep(1)
            sec += 1
            if sec >= interval / 1000:
                sec = 0
                await websocket.send(Payload(op=1, d=self.shards_record[shards_index].last_s).to_dict())

    async def send_chain_message(self, chain: Chain):
        reqs = await build_message_send(chain)
        for req in reqs.req_list:
            async with log.catch('post error:', ignore=[asyncio.TimeoutError]):
                await self.post_message(chain.data.guild_id,
                                        chain.data.src_guild_id,
                                        chain.data.channel_id,
                                        req)

    @asynccontextmanager
    async def send_message(self, channel_id: str = '', user_id: str = '', direct_src_guild_id: str = ''):
        data = Message(self)

        data.user_id = user_id
        data.channel_id = channel_id

        if not channel_id and not direct_src_guild_id:
            raise TypeError(
                'BotInstance.send_message() missing argument: "channel_id" or "direct_src_guild_id"')

        if direct_src_guild_id:
            if not user_id:
                raise TypeError('BotInstance.send_message(direct_src_guild_id=...) missing argument: "user_id"')

            data.is_direct = True
            data.src_guild_id = direct_src_guild_id

        chain = Chain(data)

        yield chain

        await self.send_chain_message(chain)

    async def package_message(self, event: str, message: dict):
        return await package_tencent_message(self, event, message)
