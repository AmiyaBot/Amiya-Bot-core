import asyncio

from typing import Dict, List
from dataclasses import dataclass
from fastapi import WebSocket, WebSocketDisconnect
from amiyabot.network.httpServer import HttpServer
from amiyabot import log


@dataclass
class ReceivedMessage:
    data: str
    port: str
    appid: str
    websocket: WebSocket


class TestServer(HttpServer):
    def __init__(self, host: str = '127.0.0.1', port: int = 32001, **kwargs):
        super().__init__(host, port, **kwargs)

        self.__create_websocket_api()

        self.clients: Dict[str, Dict[str, List[WebSocket]]] = {
            'bot': {},
            'client': {}
        }

    def __create_websocket_api(self):
        @self.app.websocket('/channel/{port}/{appid}')
        async def websocket_endpoint(websocket: WebSocket, port: str, appid: str):
            if port not in ('bot', 'client'):
                await websocket.close()

            await websocket.accept()

            if appid not in self.clients[port]:
                self.clients[port][appid] = []

            self.clients[port][appid].append(websocket)

            while True:
                try:
                    asyncio.create_task(
                        self.__handle_message(
                            ReceivedMessage(await websocket.receive_text(), port, appid, websocket)
                        )
                    )
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    log.error(e, desc='websocket recv error:')
                    break

            self.clients[port][appid].remove(websocket)

    async def __handle_message(self, data: ReceivedMessage):
        if data.port == 'bot':
            for item in self.clients['client'][data.appid]:
                await item.send_text(data.data)
        if data.port == 'client':
            for item in self.clients['bot'][data.appid]:
                await item.send_text(data.data)
