import json
import asyncio

from dataclasses import dataclass
from typing import List, Any
from amiyabot.builtin.lib.browserService import *
from amiyabot.adapters.common import CQCode
from amiyabot import log

from .keyboard import InlineKeyboard


class ChainBuilder:
    @classmethod
    async def get_image(cls, image: Union[str, bytes]) -> Union[str, bytes]:
        return image

    @classmethod
    async def get_voice(cls, voice_file: str) -> str:
        return voice_file

    @classmethod
    async def get_video(cls, video_file: str) -> str:
        return video_file

    @classmethod
    async def on_page_rendered(cls, page: Page):
        ...


@dataclass
class At:
    target: Union[str, int]


@dataclass
class AtAll:
    ...


@dataclass
class Tag:
    target: Union[str, int]


@dataclass
class Face:
    face_id: Union[str, int]


@dataclass
class Text:
    content: str


@dataclass
class Image:
    url: Optional[str] = None
    content: Optional[bytes] = None
    builder: Optional[ChainBuilder] = None

    async def get(self):
        if self.builder:
            res = await self.builder.get_image(self.url or self.content)
            if res:
                return res
        return self.url or self.content


@dataclass
class Voice:
    file: str
    title: str
    builder: Optional[ChainBuilder] = None

    async def get(self):
        if self.builder:
            res = await self.builder.get_voice(self.file)
            if res:
                return res
        return self.file


@dataclass
class Video:
    file: str
    builder: Optional[ChainBuilder] = None

    async def get(self):
        if self.builder:
            res = await self.builder.get_video(self.file)
            if res:
                return res
        return self.file


@dataclass
class Html:
    url: str
    data: Union[list, dict]
    is_file: bool = True
    render_time: int = DEFAULT_RENDER_TIME
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    builder: Optional[ChainBuilder] = None

    async def create_html_image(self):
        async with log.catch('html convert error:'):
            page: Optional[Page] = await basic_browser_service.open_page(
                self.url,
                is_file=self.is_file,
                width=self.width,
                height=self.height,
            )

            if not page:
                log.warning(f'can not open page in {basic_browser_service}.')
                return None

            if self.data:
                injected = '''
                    if ('init' in window) {
                        init(%s)
                    } else {
                        console.warn('Can not execute "window.init(data)" because this function does not exist.')
                    }
                ''' % json.dumps(
                    self.data
                )

                await page.evaluate(injected)

            # 等待渲染
            await asyncio.sleep(self.render_time / 1000)

            # 执行钩子
            if self.builder:
                await self.builder.on_page_rendered(page)

            # 截图
            result = await page.screenshot(full_page=True)

            if self.builder:
                res = await self.builder.get_image(result)
                if res:
                    result = res

            if not BROWSER_PAGE_NOT_CLOSE:
                await page.close()

            if result:
                return result

        log.warning('html convert fail.')


@dataclass
class Embed:
    title: str
    prompt: str
    thumbnail: str
    fields: List[str]

    def get(self):
        return {
            'embed': {
                'title': self.title,
                'prompt': self.prompt,
                'thumbnail': {'url': self.thumbnail},
                'fields': [{'name': item} for item in self.fields],
            }
        }


@dataclass
class Ark:
    template_id: int
    kv: List[dict]

    def get(self):
        return {
            'ark': {
                'template_id': self.template_id,
                'kv': self.kv,
            }
        }


@dataclass
class Markdown:
    template_id: str
    params: List[dict]
    keyboard: Optional[InlineKeyboard] = None
    keyboard_template_id: Optional[str] = ''

    def get(self):
        data = {
            'markdown': {
                'custom_template_id': self.template_id,
                'params': self.params,
            }
        }

        if self.keyboard:
            data.update({'keyboard': {'content': self.keyboard.dict()}})

        if self.keyboard_template_id:
            data.update({'keyboard': {'id': self.keyboard_template_id}})

        return data


@dataclass
class Extend:
    data: Any

    def get(self):
        if isinstance(self.data, CQCode):
            return self.data.code
        return self.data


CHAIN_ITEM = Union[
    At,
    AtAll,
    Tag,
    Face,
    Text,
    Image,
    Voice,
    Video,
    Html,
    Embed,
    Ark,
    Markdown,
    Extend,
]
CHAIN_LIST = List[CHAIN_ITEM]
