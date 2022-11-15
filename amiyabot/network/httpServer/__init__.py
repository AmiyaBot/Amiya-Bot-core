import os
import asyncio
import uvicorn

from typing import Any, List, Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter

from pydantic import BaseModel

from amiyabot.log import LoggerManager
from amiyabot.util import snake_case_to_pascal_case

cur_file_path = os.path.abspath(__file__)
cur_file_folder = os.path.dirname(cur_file_path)


class ServerLog:
    logger = LoggerManager('Server')

    @classmethod
    def write(cls, text: str):
        cls.logger.info(text, 'server')


class ServerEventHandler:
    on_shutdown: List[Callable] = []


class ServerMeta(type):
    servers: List[uvicorn.Server] = []
    shutdown_lock = False

    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)

        cls.servers.append(instance.server)

        return instance

    def shutdown_all(cls, server: uvicorn.Server):
        if not cls.shutdown_lock:
            cls.shutdown_lock = True

            for item in cls.servers:
                if item != server:
                    item.should_exit = True

            for action in ServerEventHandler.on_shutdown:
                asyncio.create_task(action())


class HttpServer(metaclass=ServerMeta):
    def __init__(self,
                 host: str,
                 port: int,
                 title: str = 'AmiyaBot',
                 description: str = '<a href="https://www.amiyabot.com" target="__blank">https://www.amiyabot.com</a>',
                 auth_key: str = None,
                 fastapi_options: dict = None,
                 uvicorn_options: dict = None):
        self.app = FastAPI(title=title, description=description, **(fastapi_options or {}))
        self.server = self.__load_server(options={
            'host': host,
            'port': port,
            **(uvicorn_options or {})
        })
        self.router = InferringRouter()
        self.controller = cbv(self.router)

        self.__routes = []
        self.__allow_path = []

        @self.app.middleware('http')
        async def interceptor(request: Request, call_next):
            if not request.scope['path'] in self.__allow_path + ['/docs', '/favicon.ico', '/openapi.json']:
                if auth_key and request.headers.get('authKey') != auth_key:
                    return Response('Invalid authKey', status_code=401)
            return await call_next(request)

        @self.app.on_event('shutdown')
        def on_shutdown():
            HttpServer.shutdown_all(self.server)

    def set_allow_path(self, paths: list):
        self.__allow_path = paths

    @staticmethod
    def response(data: Any = None, code: int = 200, message: str = ''):
        return {
            'data': data,
            'code': code,
            'message': message
        }

    def route(self, router_path: str = None, method: str = 'post', **kwargs):
        def decorator(fn):
            nonlocal router_path

            path = fn.__qualname__.split('.')
            c_name = snake_case_to_pascal_case(path[0][0].lower() + path[0][1:])

            if not router_path:
                router_path = f'/{c_name}'
                if len(path) > 1:
                    router_path += f'/{snake_case_to_pascal_case(path[1])}'

            arguments = {
                'path': router_path,
                'tags': [c_name.title()] if len(path) > 1 else ['Alone'],
                **kwargs
            }

            router_builder = getattr(self.router, method)
            router = router_builder(**arguments)

            self.__routes.append(router_path)

            return router(fn)

        return decorator

    def __load_server(self, options):
        return uvicorn.Server(config=uvicorn.Config(self.app,
                                                    loop='asyncio',
                                                    log_config=os.path.join(cur_file_folder,
                                                                            '../../_assets/serverLogger.yaml'),
                                                    **options))

    async def serve(self):
        async with ServerLog.logger.catch('Http server Error:'):
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=['*'],
                allow_methods=['*'],
                allow_headers=['*'],
                allow_credentials=True
            )
            self.app.include_router(self.router)

            await self.server.serve()
