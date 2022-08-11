import json
import aiohttp

from typing import Union
from amiyabot import log
from contextlib import asynccontextmanager


class HttpRequests:
    success = [200, 204]
    async_success = [201, 202, 304023, 304024]

    @classmethod
    @asynccontextmanager
    async def __handle_requests(cls, method: str, interface: str):
        async def handler(res: aiohttp.ClientResponse):
            if res.status in cls.success:
                return await res.text()
            elif res.status in cls.async_success:
                pass
            else:
                log.error(f'bad to request <{interface}>[{method}]. Got code {res.status}')

        try:
            async with aiohttp.ClientSession() as session:
                yield session, handler
        except aiohttp.ClientConnectorError:
            log.error(f'fail to request <{interface}>[{method}]')
        except Exception as e:
            log.error(e)

    @classmethod
    async def get(cls, interface: str, *args, **kwargs):
        async with cls.__handle_requests('GET', interface) as (session, handler):
            async with session.get(interface, *args, **kwargs) as res:
                return await handler(res)

    @classmethod
    async def post(cls, interface: str, payload: Union[dict, list] = None, headers: dict = None):
        _headers = {
            'Content-Type': 'application/json',
            **(headers or {})
        }
        _payload = {
            **(payload or {})
        }
        async with cls.__handle_requests('POST', interface) as (session, handler):
            async with session.post(interface, data=json.dumps(_payload), headers=_headers) as res:
                return await handler(res)

    @classmethod
    async def upload(cls, interface: str, file: bytes, file_field: str = 'file', payload: dict = None):
        data = aiohttp.FormData()
        data.add_field(file_field,
                       file,
                       content_type='application/octet-stream')

        for field, value in (payload or {}).items():
            data.add_field(field, value)

        async with cls.__handle_requests('UPLOAD', interface) as (session, handler):
            async with session.post(interface, data=data) as res:
                return await handler(res)

    @classmethod
    async def post_form_data(cls, interface: str, payload: dict = None, headers: dict = None):
        _headers = {
            **(headers or {})
        }

        data = aiohttp.FormData()
        for field, value in (payload or {}).items():
            if value is None:
                continue
            if type(value) in [dict, list]:
                value = json.dumps(value, ensure_ascii=False)
            data.add_field(field, value)

        async with cls.__handle_requests('FORM POST', interface) as (session, handler):
            async with session.post(interface, data=data, headers=_headers) as res:
                return await handler(res)


http_requests = HttpRequests
