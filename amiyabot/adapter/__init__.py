import json
import asyncio
import websockets

from typing import Dict
from amiyabot import log
from amiyabot.builtin.messageChain import Chain

from .api import TencentConnect
from .model import GateWay, Payload, ShardsRecord, ConnectionHandler
from .intents import Intents


class BotInstance(TencentConnect):
    def __init__(self, appid: str, token: str):
        super().__init__(appid, token)

        self.appid = appid
        self.token = token

        self.shards_record: Dict[int, ShardsRecord] = {}
        self.alive = True

    async def create_connection(self, handler: ConnectionHandler, shards_index: int = 0):
        gateway = handler.gateway

        async with log.catch('connection error:', ignore=[asyncio.CancelledError, websockets.ConnectionClosedError]):
            async with websockets.connect(gateway.url) as websocket:
                self.shards_record[shards_index] = ShardsRecord(shards_index)

                while self.alive:
                    await asyncio.sleep(0)

                    recv = await websocket.recv()
                    payload = Payload(**json.loads(recv))

                    if payload.op == 0:
                        if payload.t == 'READY':
                            log.info(
                                f'bot connected. {self.appid} '
                                f'{shards_index + 1}/{gateway.shards} %s' % payload.d['user']['username']
                            )
                        else:
                            asyncio.create_task(handler.message_handler(payload.t, payload.d))

                    intent = 0
                    intent |= handler.intents_type
                    intent |= Intents.GUILDS
                    intent |= Intents.GUILD_MEMBERS
                    intent |= Intents.MESSAGE_REACTION
                    intent |= Intents.DIRECT_MESSAGE
                    intent |= Intents.INTERACTION
                    intent |= Intents.AUDIO

                    if payload.op == 10:
                        auth_token = {
                            'token': f'Bot {self.appid}.{self.token}',
                            'intents': intent,
                            'shard': [shards_index, gateway.shards],
                            'properties': {
                                '$os': '',
                                '$browser': '',
                                '$device': ''
                            }
                        }
                        await websocket.send(Payload(op=2, d=auth_token).to_dict())
                        asyncio.create_task(
                            self.heartbeat_interval(websocket, payload.d['heartbeat_interval'], shards_index)
                        )

                    if payload.s:
                        self.shards_record[shards_index].last_s = payload.s

        log.error('connection closed.')

        self.alive = False

    async def heartbeat_interval(self, websocket: websockets.WebSocketClientProtocol, interval: int, shards_index: int):
        sec = 0
        while self.alive:
            await asyncio.sleep(1)
            sec += 1
            if sec >= interval / 1000:
                sec = 0
                await websocket.send(Payload(op=1, d=self.shards_record[shards_index].last_s).to_dict())

    async def send_chain_message(self, chain: Chain):
        reqs = await chain.build()
        for req in reqs.req_list:
            async with log.catch('post error:', ignore=[asyncio.TimeoutError]):
                await self.post_message(chain.data.channel_id, req)
