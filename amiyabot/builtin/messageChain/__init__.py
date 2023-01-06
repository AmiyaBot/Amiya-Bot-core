import re
import os

from amiyabot.builtin.message import Message
from amiyabot.builtin.lib.imageCreator import create_image, IMAGES_TYPE

from .element import *

cur_file_path = os.path.abspath(__file__)
cur_file_folder = os.path.dirname(cur_file_path)

md_template = os.path.join(cur_file_folder, '../../_assets/markdown/template.html')

PADDING = 10
IMAGE_WIDTH = 700
MAX_SEAT = IMAGE_WIDTH - PADDING * 2


class ConvertSetting:
    max_length = 100


class ChainBuilder:
    @staticmethod
    async def image_getter_hook(image: Union[str, bytes]):
        return image


class Chain:
    def __init__(self,
                 data: Message = None,
                 at: bool = True,
                 reference: bool = False,
                 builder: ChainBuilder = ChainBuilder()):
        """
        创建回复消息

        :param data:      Message 对象
        :param at:        是否 at 用户
        :param reference: 是否引用该 Message 对象的消息
        """
        self.data = data
        self.builder = builder
        self.reference = reference

        self.chain: CHAIN_LIST = []

        if data and at and not data.is_direct:
            self.at(enter=True)

    def at(self, user: str = None, enter: bool = False):
        if self.data and self.data.is_direct:
            return self

        self.chain.append(At(user or self.data.user_id))
        if enter:
            return self.text('\n')

        return self

    def face(self, face_id: int):
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
            if auto_convert and len(text) >= ConvertSetting.max_length:
                self.text_image(text)
            else:
                chain.append(Text(text))

        self.chain += chain

        return self

    def text_image(self,
                   text: str,
                   images: IMAGES_TYPE = None,
                   width: int = None,
                   height: int = None,
                   bgcolor: str = '#F5F5F5'):
        return self.image(target=create_image(text,
                                              images=(images or []),
                                              width=width,
                                              height=height,
                                              padding=PADDING,
                                              max_seat=MAX_SEAT,
                                              bgcolor=bgcolor))

    def image(self, target: Union[str, bytes, List[Union[str, bytes]]] = None, url: str = None):
        if url:
            self.chain.append(Image(url=url, getter_hook=self.builder.image_getter_hook))
        else:
            if type(target) is not list:
                target = [target]

            for item in target:
                if type(item) is str:
                    if os.path.exists(item):
                        with open(item, mode='rb') as f:
                            self.chain.append(Image(content=f.read(), getter_hook=self.builder.image_getter_hook))
                else:
                    self.chain.append(Image(content=item, getter_hook=self.builder.image_getter_hook))

        return self

    def voice(self, file: str, title: str = 'voice'):
        self.chain.append(Voice(file, title))
        return self

    def markdown(self, content: str, render_time: int = DEFAULT_RENDER_TIME):
        return self.html(md_template,
                         width=50,
                         height=50,
                         data={'content': content},
                         render_time=render_time)

    def html(self,
             path: str,
             data: Union[dict, list] = None,
             width: int = DEFAULT_WIDTH,
             height: int = DEFAULT_HEIGHT,
             is_template: bool = True,
             render_time: int = DEFAULT_RENDER_TIME):
        self.chain.append(Html(
            url=path,
            data=data,
            width=width,
            height=height,
            is_file=is_template,
            render_time=render_time,
            getter_hook=self.builder.image_getter_hook
        ))
        return self

    def extend(self, data: Any):
        self.chain.append(Extend(data))
        return self
