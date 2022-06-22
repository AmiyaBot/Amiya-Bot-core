import re
import asyncio

from amiyabot.builtin.message import Message
from amiyabot.builtin.lib.imageCreator import create_image, IMAGES_TYPE
from amiyabot.builtin.lib.htmlConverter import ChromiumBrowser, debug
from amiyabot import log

from .element import *

PADDING = 10
IMAGE_WIDTH = 700
MAX_SEAT = IMAGE_WIDTH - PADDING * 2


class ConvertSetting:
    max_length = 100


class Chain:
    def __init__(self, data: Message, at: bool = True, reference: bool = False):
        """
        创建回复消息

        :param data:  Message 对象
        :param at:    是否 at 用户
        """
        self.data = data
        self.reference = reference
        self.chain: CHAIN_LIST = []

        if at:
            self.at(enter=True)

    def __req(self, content: str = '', image_url: str = '', file_image: bytes = None):
        req = MessageSendRequest(
            data={
                'msg_id': self.data.message_id,
                'content': content,
                'image': image_url,
                'file_image': file_image,
                **({
                       'message_reference': {
                           'message_id': self.data.message_id,
                           'ignore_get_message_error': False
                       }
                   } if self.reference else {})
            }
        )

        if file_image:
            req.upload_image = True

        return req

    def at(self, user: int = None, enter: bool = False):
        self.chain.append(At(user or self.data.user_id))
        if enter:
            return self.text('\n')
        return self

    def face(self, face_id: int):
        self.chain.append(Face(face_id))
        return self

    def text(self, text, auto_convert: bool = False):
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
                   text,
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

    def image(self, target: Union[str, bytes, List[Union[str, bytes]]], url: str = None):
        if url:
            self.chain.append(Image(url=url))
        else:
            if type(target) is not list:
                target = [target]

            for item in target:
                if type(item) is str:
                    with open(item, mode='rb') as f:
                        self.chain.append(Image(content=f.read()))
                else:
                    self.chain.append(Image(content=item))

        return self

    def voice(self, url: str, title: str = 'voice'):
        self.chain.append(Voice(url, title))
        return self

    def html(self,
             path: str,
             data: Union[dict, list] = None,
             width: int = 1280,
             height: int = 720,
             is_template: bool = True,
             render_time: int = 200):
        self.chain.append(Html(**{
            'data': data,
            'width': width,
            'height': height,
            'template': path,
            'is_file': is_template,
            'render_time': render_time
        }))
        return self

    async def build(self, chain: CHAIN_LIST = None) -> List[MessageSendRequest]:
        chain = chain or self.chain

        messages = []

        text = ''
        has_content = False

        for item in chain:
            # At
            if type(item) is At:
                text += f'<@{item.target}>'

            # Face
            if type(item) is Face:
                has_content = True
                text += f'<emoji:{item.face_id}>'

            # Text
            if type(item) is Text:
                if item.content.strip('\n'):
                    has_content = True
                text += item.content

            # Image
            if type(item) is Image:
                if item.url:
                    messages.append(self.__req(image_url=item.url))
                else:
                    messages.append(self.__req(file_image=item.content))

            # Voice
            if type(item) is Voice:
                pass

            # Html
            if type(item) is Html:
                async with log.catch('html convert error:'):
                    browser = ChromiumBrowser()
                    page = await browser.open_page(item.template,
                                                   is_file=item.is_file,
                                                   width=item.width,
                                                   height=item.height)

                    if not page:
                        continue

                    if item.data:
                        await page.init_data(item.data)

                    await asyncio.sleep(item.render_time / 1000)

                    messages.append(self.__req(file_image=await page.make_image()))

                    if not debug:
                        await page.close()

        text = text.strip('\n')
        if text and has_content:
            messages.append(self.__req(content=text))

        return messages
