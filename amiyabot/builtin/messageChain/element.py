import asyncio

from dataclasses import dataclass
from typing import Optional, Callable, Coroutine, Union, List, Any
from amiyabot.builtin.lib.browserService import basic_browser_service
from amiyabot.util import argv
from amiyabot import log

IMAGE_GETTER_HOOK = Callable[[Union[str, bytes]], Coroutine[Any, Any, Union[str, bytes]]]

DEFAULT_WIDTH = argv('browser-width', int) or 1280
DEFAULT_HEIGHT = argv('browser-height', int) or 720
DEFAULT_RENDER_TIME = argv('browser-render-time', int) or 200


@dataclass
class At:
    target: int


@dataclass
class Face:
    face_id: int


@dataclass
class Text:
    content: str


@dataclass
class Image:
    url: Optional[str] = None
    content: Optional[bytes] = None
    getter_hook: IMAGE_GETTER_HOOK = None

    async def get(self):
        if self.getter_hook:
            res = await self.getter_hook(self.url or self.content)
            if res:
                return res
        return self.url or self.content


@dataclass
class Voice:
    file: str
    title: str


@dataclass
class Html:
    url: str
    data: Union[list, dict]
    is_file: bool = True
    render_time: int = DEFAULT_RENDER_TIME
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    getter_hook: IMAGE_GETTER_HOOK = None

    async def create_html_image(self):
        async with log.catch('html convert error:'):
            page = await basic_browser_service.open_page(self.url,
                                                         is_file=self.is_file,
                                                         width=self.width,
                                                         height=self.height)

            if not page:
                return None

            if self.data:
                await page.init_data(self.data)

            # 等待渲染
            await asyncio.sleep(self.render_time / 1000)

            result = await page.make_image()

            if self.getter_hook:
                res = await self.getter_hook(result)
                if res:
                    result = res

            await page.close()

            return result


CHAIN_LIST = List[
    Union[
        At, Face, Text, Image, Voice, Html
    ]
]
