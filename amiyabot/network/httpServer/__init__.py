import os
import uvicorn

from typing import Dict, Callable
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
                 ssl_keyfile: str = None,
                 ssl_certfile: str = None):

        self.app = FastAPI(title=title, description=description)
        self.server = self.__load_server(options={
            'host': host,
            'port': port,
            'ssl_keyfile': ssl_keyfile,
            'ssl_certfile': ssl_certfile
        })

        self.__routes = []
        self.__controllers = []

    @staticmethod
    def router(router_path: str = None, method: str = 'post', **kwargs):
        def decorator(fn):
            def options():
                return fn, router_path, method, kwargs

            return options

        return decorator

    def controller(self, cls):
        self.__controllers.append(cls)

    def __load_server(self, options):
        return uvicorn.Server(config=uvicorn.Config(self.app,
                                                    loop='asyncio',
                                                    log_config=os.path.join(cur_file_folder, './server.yaml'),
                                                    **options))

    @staticmethod
    def __load_controller(controller):
        attrs = [item for item in dir(controller) if not item.startswith('__')]
        methods: Dict[str, Callable] = {}

        for n in attrs:
            obj = getattr(controller, n)
            if hasattr(obj, '__call__'):
                methods[n] = obj

        cname = controller.__name__[0].lower() + controller.__name__[1:]

        for name, options in methods.items():
            fn, router_path, method, kwargs = options()

            router_path = router_path or f'/{cname}/' + snake_case_to_pascal_case(name.strip('_'))

            yield fn, router_path, method, cname, kwargs

    async def serve(self):
        for cls in self.__controllers:
            for fn, router_path, method, cname, options in self.__load_controller(cls):
                arguments = {
                    'path': router_path,
                    'tags': [cname.title()],
                    **options
                }

                router_builder = getattr(self.app, method)
                router = router_builder(**arguments)
                router(fn)

                if cname != 'index':
                    self.__routes.append(router_path)

        async with ServerLog.logger.catch('Http server Error:'):
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=['*'],
                allow_methods=['*'],
                allow_headers=['*'],
                allow_credentials=True
            )

            await self.server.serve()
