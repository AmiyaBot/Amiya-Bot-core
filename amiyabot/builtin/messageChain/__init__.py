import re

from amiyabot.builtin.message import MessageStructure
from amiyabot.builtin.lib.imageCreator import create_image, IMAGES_TYPE

from .element import *

cur_file_path = os.path.abspath(__file__)
cur_file_folder = os.path.dirname(cur_file_path)

PADDING = 10
IMAGE_WIDTH = 700
MAX_SEAT = IMAGE_WIDTH - PADDING * 2


class ChainConfig:
    max_length = argv('text-max-length', int) or 100
    md_template = os.path.join(cur_file_folder, '../../_assets/markdown/template.html')


class Chain:
    def __init__(
        self,
        data: Optional[MessageStructure] = None,
        at: bool = True,
        reference: bool = False,
        chain_builder: Optional[ChainBuilder] = None,
    ):
        """
        创建回复消息

        :param data:      Message 对象
        :param at:        是否 at 用户
        :param reference: 是否引用该 Message 对象的消息
        """
        self.data = data
        self.reference = reference

        self.chain: CHAIN_LIST = []
        self.raw_chain: Optional[Any] = None

        if data and at and not data.is_direct:
            self.at(enter=True)

        self._builder = chain_builder or ChainBuilder()
        self.use_default_builder = not bool(chain_builder)

    @property
    def builder(self):
        return self._builder

    @builder.setter
    def builder(self, value: ChainBuilder):
        self._builder = value
        self.use_default_builder = False

        for item in self.chain:
            if hasattr(item, 'builder'):
                item.builder = value

    def at(self, user: Optional[str] = None, enter: bool = False):
        if self.data and self.data.is_direct:
            return self

        self.chain.append(At(user or self.data.user_id))
        if enter:
            return self.text('\n')

        return self

    def at_all(self):
        self.chain.append(AtAll())
        return self

    def tag(self, target: Union[str, int]):
        self.chain.append(Tag(target))
        return self

    def face(self, face_id: Union[str, int]):
        self.chain.append(Face(face_id))
        return self

    def text(self, text: str, auto_convert: bool = False):
        chain = []

        if re.findall(r'\[cl\s(.*?)@#(.*?)\scle]', text):
            return self.text_image(text)

        if text.rstrip('\n') != '':
            text = text.rstrip('\n')

        r = re.findall(r'(\[face:(\d+)])', text)
        if r:
            face = []
            for item in r:
                text = text.replace(item[0], ':face')
                face.append(item[1])

            for index, item in enumerate(text.split(':face')):
                if item != '':
                    chain.append(Text(item))
                if index <= len(face) - 1:
                    chain.append(Face(face[index]))
        else:
            if auto_convert and len(text) >= ChainConfig.max_length:
                self.text_image(text)
            else:
                chain.append(Text(text))

        self.chain += chain

        return self

    def text_image(
        self,
        text: str,
        images: Optional[IMAGES_TYPE] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        bgcolor: str = '#F5F5F5',
    ):
        return self.image(
            target=create_image(
                text,
                images=(images or []),
                width=width,
                height=height,
                padding=PADDING,
                max_seat=MAX_SEAT,
                bgcolor=bgcolor,
            )
        )

    def image(self, target: Optional[Union[str, bytes, List[Union[str, bytes]]]] = None, url: Optional[str] = None):
        if url:
            self.chain.append(Image(url=url, builder=self.builder))
        else:
            if not isinstance(target, list):
                target = [target]

            for item in target:
                if isinstance(item, str):
                    if os.path.exists(item):
                        with open(item, mode='rb') as f:
                            self.chain.append(Image(content=f.read(), builder=self.builder))
                else:
                    self.chain.append(Image(content=item, builder=self.builder))

        return self

    def voice(self, file: str, title: str = 'voice'):
        self.chain.append(Voice(file, title, builder=self.builder))
        return self

    def video(self, file: str):
        self.chain.append(Video(file, builder=self.builder))
        return self

    def html(
        self,
        path: str,
        data: Optional[Union[dict, list]] = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        is_template: bool = True,
        render_time: int = DEFAULT_RENDER_TIME,
    ):
        self.chain.append(
            Html(
                url=path,
                data=data,
                width=width,
                height=height,
                is_file=is_template,
                render_time=render_time,
                builder=self.builder,
            )
        )
        return self

    def markdown(
        self,
        content: str,
        max_width: int = 960,
        css_style: str = '',
        render_time: int = DEFAULT_RENDER_TIME,
        is_dark: bool = False,
    ):
        return self.html(
            ChainConfig.md_template,
            width=50,
            height=50,
            data={
                'content': content,
                'max_width': max_width,
                'css_style': css_style,
                'is_dark': is_dark,
            },
            render_time=render_time,
        )

    def markdown_template(
        self,
        template_id: str,
        params: List[dict],
        keyboard: Optional[InlineKeyboard] = None,
        keyboard_template_id: Optional[str] = '',
    ):
        self.chain.append(Markdown(template_id, params, keyboard, keyboard_template_id))
        return self

    def embed(self, title: str, prompt: str, thumbnail: str, fields: List[str]):
        self.chain.append(Embed(title, prompt, thumbnail, fields))
        return self

    def ark(self, template_id: int, kv: List[dict]):
        self.chain.append(Ark(template_id, kv))
        return self

    def extend(self, data: Any):
        self.chain.append(Extend(data))
        return self
