from dataclasses import asdict
from amiyabot.adapters import MessageCallback
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *

from .api import QQGroupAPI, log


class QQGroupMessageCallback(MessageCallback):
    async def recall(self):
        ...

    async def get_message(self):
        ...


@dataclass
class GroupPayload:
    content: str = ''
    msg_type: int = 0
    markdown: Optional[dict] = None
    keyboard: Optional[dict] = None
    media: Optional[dict] = None
    ark: Optional[dict] = None
    image: Optional[str] = None
    message_reference: Optional[dict] = None
    event_id: Optional[str] = None
    msg_id: Optional[str] = None
    msg_seq: Optional[int] = None


async def build_message_send(api: QQGroupAPI, chain: Chain, custom_chain: Optional[CHAIN_LIST] = None):
    chain_list = custom_chain or chain.chain

    payload_list: List[GroupPayload] = []
    payload = GroupPayload(msg_id=chain.data.message_id)

    async def insert_media(url: str, file_type: int = 1):
        nonlocal payload

        if not isinstance(url, str):
            log.warning(f'unsupported file type "{type(url)}".')
            return

        if url.startswith('http'):
            res = await api.upload_file(chain.data.channel_openid, file_type, url)
            if res:
                file_info = res.json['file_info']

                payload.msg_type = 7
                payload.media = {'file_info': file_info}

                payload_list.append(payload)
                payload = GroupPayload(msg_id=chain.data.message_id)
        else:
            log.warning(f'media file must be network paths.')

    for item in chain_list:
        # Text
        if isinstance(item, Text):
            payload.content += item.content

        # Image
        if isinstance(item, Image):
            await insert_media(await item.get())

        # Voice
        if isinstance(item, Voice):
            await insert_media(await item.get(), 3)

        # Video
        if isinstance(item, Video):
            await insert_media(await item.get(), 2)

        # Html
        if isinstance(item, Html):
            await insert_media(await item.create_html_image())

    if payload.content:
        payload_list.append(payload)

    return [asdict(item) for item in payload_list]
