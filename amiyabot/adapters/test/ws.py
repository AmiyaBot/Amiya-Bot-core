import json
import asyncio

from typing import Callable, List
from dataclasses import dataclass
from fastapi import WebSocket, WebSocketDisconnect
from amiyabot.network.httpServer import HttpServer
from amiyabot import log


@dataclass
class ReceivedMessage:
    data: str
    websocket: WebSocket


class TestServer(HttpServer):
    def __init__(self, appid: str, host: str, port: int):
        super().__init__(host, port)

        self.appid = appid
        self.handler = None
        self.clients: List[WebSocket] = []

        self.__create_websocket_api()

    def __create_websocket_api(self):
        @self.app.websocket(f'/{self.appid}')
        async def websocket_endpoint(websocket: WebSocket):

            await websocket.accept()

            self.clients.append(websocket)

            while True:
                try:
                    asyncio.create_task(
                        self.__handle_message(
                            ReceivedMessage(await websocket.receive_text(), websocket)
                        )
                    )
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    log.error(e, desc='websocket recv error:')
                    break

            self.clients.remove(websocket)

    async def run(self, handler: Callable):
        self.handler = handler

        await self.serve()

    async def send(self, data: str):
        for item in self.clients:
            await item.send_text(data)

    async def __handle_message(self, data: ReceivedMessage):
        async with log.catch(ignore=[json.JSONDecodeError]):
            content = json.loads(data.data)
            asyncio.create_task(self.handler(content['event'], content['event_data']))
