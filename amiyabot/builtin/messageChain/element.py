import asyncio

from dataclasses import dataclass
from typing import Optional, Union, List
from amiyabot import log
from amiyabot.builtin.lib.htmlConverter import ChromiumBrowser, debug


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


@dataclass
class Voice:
    url: str
    title: str


@dataclass
class Html:
    data: Union[list, dict]
    template: str
    is_file: bool
    render_time: int
    width: int = 1280
    height: int = 720

    async def create_html_image(self):
        async with log.catch('html convert error:'):
            browser = ChromiumBrowser()
            page = await browser.open_page(self.template,
                                           is_file=self.is_file,
                                           width=self.width,
                                           height=self.height)

            if not page:
                return None

            if self.data:
                await page.init_data(self.data)

            await asyncio.sleep(self.render_time / 1000)

            result = await page.make_image()

            if not debug:
                await page.close()

            return result


CHAIN_LIST = List[
    Union[
        At, Face, Text, Image, Voice, Html
    ]
]
