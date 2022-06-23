import json
import aiohttp

from typing import Union
from amiyabot import log


class HttpRequests:
    success_code = [200, 201, 202, 204]

    @classmethod
    async def get(cls, interface: str, *args, **kwargs):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(interface, *args, **kwargs) as res:
                    if res.status in cls.success_code:
                        return await res.text()
                    else:
                        log.error(f'bad to request <{interface}>[GET]. Got code {res.status}')
        except aiohttp.ClientConnectorError:
            log.error(f'fail to request <{interface}>[GET]')

    @classmethod
    async def post(cls, interface: str, payload: Union[dict, list] = None, headers: dict = None):
        _headers = {
            'Content-Type': 'application/json',
            **(headers or {})
        }
        _payload = {
            **(payload or {})
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(interface, data=json.dumps(_payload), headers=_headers) as res:
                    if res.status in cls.success_code:
                        return await res.text()
                    else:
                        log.error(f'bad to request <{interface}>[POST]. Got code {res.status}')
        except aiohttp.ClientConnectorError:
            log.error(f'fail to request <{interface}>[POST]')

    @classmethod
    async def post_form_data(cls, interface: str, payload: dict = None, headers: dict = None):
        _headers = {
            **(headers or {})
        }

        data = aiohttp.FormData()
        for field, value in (payload or {}).items():
            if type(value) in [dict, list]:
                value = json.dumps(value, ensure_ascii=False)
            data.add_field(field, value)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(interface, data=data, headers=_headers) as res:
                    if res.status in cls.success_code:
                        return await res.text()
                    else:
                        log.error(f'bad to request <{interface}>[POST-FormData]. Got code {res.status}')
        except aiohttp.ClientConnectorError:
            log.error(f'fail to request <{interface}>[POST-FormData]')


http_requests = HttpRequests
