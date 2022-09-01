import os
import uvicorn

from typing import Any
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter

from amiyabot.log import LoggerManager
from amiyabot.util import snake_case_to_pascal_case

cur_file_path = os.path.abspath(__file__)
cur_file_folder = os.path.dirname(cur_file_path)


class ServerLog:
    logger = LoggerManager('Server')

    @classmethod
    def write(cls, text: str):
        cls.logger.info(text, 'server')


class HttpServer:
    def __init__(self,
                 host: str,
                 port: int,
                 title: str = 'AmiyaBot',
                 description: str = '<a href="https://www.amiyabot.com" target="__blank">https://www.amiyabot.com</a>',
                 auth_key: str = None,
                 ssl_keyfile: str = None,
                 ssl_certfile: str = None):
        self.app = FastAPI(title=title, description=description)
        self.server = self.__load_server(options={
            'host': host,
            'port': port,
            'ssl_keyfile': ssl_keyfile,
            'ssl_certfile': ssl_certfile
        })
        self.router = InferringRouter()
        self.controller = cbv(self.router)

        self.__routes = []

        @self.app.middleware('http')
        async def interceptor(request: Request, call_next):
            if auth_key and request.headers.get('authKey') != auth_key:
                return Response('Invalid authKey', status_code=401)
            return await call_next(request)

    @staticmethod
    def response(data: Any = None, code: int = 200, message: str = 'success'):
        return {
            'data': data,
            'code': code,
            'message': message
        }

    def route(self, router_path: str = None, method: str = 'post', **kwargs):
        def decorator(fn):
            nonlocal router_path

            path = fn.__qualname__.split('.')
            c_name = path[0][0].lower() + path[0][1:]
            f_name = snake_case_to_pascal_case(path[1])

            if not router_path:
                router_path = f'/{c_name}/{f_name}'

            arguments = {
                'path': router_path,
                'tags': [c_name.title()],
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
                                                    log_config=os.path.join(cur_file_folder, './server.yaml'),
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
