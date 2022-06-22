from dataclasses import dataclass
from typing import Optional, Union, List


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


@dataclass
class MessageSendRequest:
    data: dict
    upload_image: bool = False


class MessageSendRequestGroup:
    def __init__(self, message_id: str, reference: bool):
        self.req_list: List[MessageSendRequest] = []

        self.text: str = ''
        self.message_id: str = message_id
        self.reference: bool = reference

    def __insert_req(self, content: str = '', image: Union[str, bytes] = None):
        req = MessageSendRequest(
            data={
                'msg_id': self.message_id
            }
        )

        if content:
            req.data['content'] = content

        if type(image) is str:
            req.data['image'] = image

        if type(image) is bytes:
            req.data['file_image'] = image
            req.upload_image = True

        if self.reference:
            req.data['message_reference'] = {
                'message_id': self.message_id,
                'ignore_get_message_error': False
            }

        self.req_list.append(req)

    def add_text(self, text: str):
        self.text += text

    def add_image(self, image: Union[str, bytes]):
        self.__insert_req(content=self.text, image=image)
        self.text = ''

    def done(self):
        if self.text:
            self.__insert_req(content=self.text)


CHAIN_LIST = List[
    Union[
        At, Face, Text, Image, Voice, Html
    ]
]
