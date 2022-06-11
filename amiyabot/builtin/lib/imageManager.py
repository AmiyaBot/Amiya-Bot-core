from typing import Any, Optional, Callable, Coroutine
from amiyabot.network.httpRequests import http_requests


class ImagesManager:
    remote: str = 'http://server.amiyabot.com'
    custom_generate: Callable[[bytes], Coroutine[Any, Any, Optional[str]]] = None

    @classmethod
    async def generate_url(cls, content: bytes) -> Optional[str]:
        if cls.custom_generate:
            return await cls.custom_generate(content)

        path = await http_requests.upload(f'{cls.remote}/upload', content)
        if path:
            return f'{cls.remote}/images?path=' + path.strip('"')
