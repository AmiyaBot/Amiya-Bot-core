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


CHAIN_LIST = List[
    Union[
        At, Face, Text, Image, Voice, Html
    ]
]
