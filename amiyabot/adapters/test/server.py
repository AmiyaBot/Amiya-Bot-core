import json
import base64
import shutil
import asyncio

from typing import Optional, List
from dataclasses import dataclass
from fastapi import WebSocket, WebSocketDisconnect
from amiyabot.adapters import BotAdapterProtocol, HANDLER_TYPE
from amiyabot.network.httpServer import HttpServer
from amiyabot.builtin.message import Message, Event
from amiyabot.util import random_code, create_dir
from amiyabot import log


@dataclass
class ReceivedMessage:
    data: str
    websocket: WebSocket


class TestServer(HttpServer):
    def __init__(self, instance: BotAdapterProtocol, appid: str, host: str, port: int):
        super().__init__(host, port)

        create_dir('testTemp')
        self.add_static_folder('/testTemp', 'testTemp')

        self.host = host
        self.port = port
        self.appid = appid
        self.instance = instance
        self.handler: Optional[HANDLER_TYPE] = None
        self.clients: List[WebSocket] = []

        @self.app.on_event('shutdown')
        def clean_temp():
            shutil.rmtree('testTemp')

        @self.app.websocket(f'/{self.appid}')
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()

            self.clients.append(websocket)

            while True:
                try:
                    asyncio.create_task(
                        self.handle_message(
                            ReceivedMessage(
                                await websocket.receive_text(),
                                websocket,
                            )
                        )
                    )
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    log.error(e, desc='websocket recv error:')
                    break

            self.clients.remove(websocket)

    async def run(self, handler: HANDLER_TYPE):
        self.handler = handler

        await self.serve()

    async def send(self, data: str):
        for item in self.clients:
            await item.send_text(data)

    async def handle_message(self, data: ReceivedMessage):
        async with log.catch(ignore=[json.JSONDecodeError]):
            content = json.loads(data.data)
            message = await self.package_message(content['event'], content['event_id'], content['event_data'])

            asyncio.create_task(self.handler(message))

    async def package_message(self, event: str, event_id: str, message: dict):
        if event != 'message':
            return Event(self.instance, event, message)

        msg = Message(self.instance, message)

        msg.message_id = event_id
        msg.user_id = message['user_id']
        msg.channel_id = message['channel_id']
        msg.message_type = message['message_type']
        msg.nickname = message['nickname']
        msg.is_admin = message['is_admin']
        msg.image = [self.base64_to_temp_url(item) for item in message['images']]

        text = message.get('message', '')

        msg.set_text(text)
        return msg

    def base64_to_temp_url(self, base64_string: str):
        data = base64_string.split('base64,')[-1]
        decoded_data = base64.b64decode(data)

        temp_file_path = f'testTemp/images/{random_code(20)}.png'
        create_dir(temp_file_path, is_file=True)

        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(decoded_data)

        return f'http://%s:{self.port}/{temp_file_path}' % ('localhost' if self.host == '0.0.0.0' else self.host)
