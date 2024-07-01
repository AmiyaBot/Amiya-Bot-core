import json
import aiohttp

from typing import Optional, Union, Any
from amiyabot import log


class HttpRequests:
    success = [200, 204]
    async_success = [201, 202, 304023, 304024]

    @classmethod
    async def request(
        cls,
        url: str,
        method: str = 'post',
        request_name: Optional[str] = None,
        ignore_error: bool = False,
        **kwargs,
    ):
        response = Response('')
        try:
            request_name = (request_name or method).upper()

            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.request(method, url, **kwargs) as res:
                    response = Response(await res.text())
                    response.response = res

                    log_text = (
                        f'Request <{url}>[{request_name}]. '
                        f'Got code {res.status} {res.reason}. '
                        f'Response: {response.text}'
                    )
                    log.debug(log_text)

                    if res.status not in cls.success + cls.async_success:
                        if not ignore_error:
                            log.warning(log_text)

                    return response

        except aiohttp.ClientConnectorError as e:
            response.error = e
            if not ignore_error:
                log.error(f'Unable to request <{url}>[{request_name}]')

        except Exception as e:
            response.error = e
            if not ignore_error:
                log.error(e)

        return response

    @classmethod
    async def get(
        cls,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs,
    ):
        return await cls.request(
            url,
            'get',
            params=params,
            headers=headers,
            **kwargs,
        )

    @classmethod
    async def post(
        cls,
        url: str,
        payload: Optional[Union[dict, list]] = None,
        headers: Optional[dict] = None,
        **kwargs,
    ):
        _headers = {'Content-Type': 'application/json', **(headers or {})}
        _payload = {**(payload or {})}
        return await cls.request(
            url,
            'post',
            request_name='post',
            data=json.dumps(_payload),
            headers=_headers,
            **kwargs,
        )

    @classmethod
    async def post_form(
        cls,
        url: str,
        payload: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs,
    ):
        _headers = {**(headers or {})}

        data = cls.__build_form_data(payload)

        return await cls.request(
            url,
            'post',
            'post-form',
            data=data,
            headers=_headers,
            **kwargs,
        )

    @classmethod
    async def post_upload(
        cls,
        url: str,
        file: bytes,
        filename: str = 'file',
        file_field: str = 'file',
        payload: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs,
    ):
        _headers = {**(headers or {})}

        data = cls.__build_form_data(payload)
        data.add_field(file_field, file, filename=filename, content_type='application/octet-stream')

        return await cls.request(
            url,
            'post',
            'post-upload',
            data=data,
            headers=_headers,
            **kwargs,
        )

    @classmethod
    def __build_form_data(cls, payload: Optional[dict]):
        data = aiohttp.FormData()

        for field, value in (payload or {}).items():
            if value is None:
                continue
            if type(value) in [dict, list]:
                value = json.dumps(value, ensure_ascii=False)
            data.add_field(field, value)

        return data


class Response(str):
    def __init__(self, res_text: str):
        self.text = res_text
        self.response: Optional[aiohttp.ClientResponse] = None
        self.error: Optional[Exception] = None

    @property
    def json(self):
        try:
            return json.loads(self.text)
        except json.JSONDecodeError:
            return None


class ResponseException(Exception):
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.data = data
        self.message = message

    def __str__(self):
        return f'[{self.code}] {self.message} -- data: {self.data}'


http_requests = HttpRequests
