import base64

from graiax import silkcoder
from amiyabot.adapters import MessageCallback
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *
from amiyabot.util import is_valid_url
from amiyabot import log

from .api import OneBot11API
from .package import package_onebot11_message


class OneBot11MessageCallback(MessageCallback):
    async def recall(self):
        if not self.response:
            log.warning('can not recall message because the response is None.')
            return False

        await self.instance.recall_message(self.response.json['data']['message_id'])

    async def get_message(self):
        if not self.response:
            return None

        api: OneBot11API = self.instance.api

        message_id = self.response.json['data']['message_id']

        message_res = await api.get_msg(message_id)
        message_data = message_res.json

        if message_data:
            return await package_onebot11_message(
                self.instance,
                '',
                {'post_type': 'message', **message_data['data']},
            )


async def build_message_send(chain: Chain, chain_only: bool = False):
    chain_list = chain.chain
    chain_data = []
    voice_list = []
    cq_codes = []

    if chain.reference and chain.data and chain.data.message_id:
        chain_data.append({'type': 'reply', 'data': {'id': chain.data.message_id}})

    if chain_list:
        for item in chain_list:
            # At
            if isinstance(item, At):
                chain_data.append({'type': 'at', 'data': {'qq': item.target or chain.data.user_id}})

            # AtAll
            if isinstance(item, AtAll):
                chain_data.append({'type': 'at', 'data': {'qq': 'all'}})

            # Face
            if isinstance(item, Face):
                chain_data.append({'type': 'face', 'data': {'id': item.face_id}})

            # Text
            if isinstance(item, Text):
                chain_data.append({'type': 'text', 'data': {'text': item.content}})

            # Image
            if isinstance(item, Image):
                img = await item.get()
                chain_data.append(await append_image(img))

            # Voice
            if isinstance(item, Voice):
                voice_item = await append_voice(item.file)
                if chain_only:
                    voice_list.append(voice_item)
                else:
                    voice_list.append(send_msg(chain, [voice_item]))

            # Html
            if isinstance(item, Html):
                result = await item.create_html_image()
                if result:
                    chain_data.append(await append_image(result))

            # Extend
            if isinstance(item, Extend):
                data = item.get()
                if isinstance(data, str):
                    cq_codes.append(send_msg(chain, data))
                else:
                    chain_data.append(data)

    if chain_only:
        return chain_data, voice_list, cq_codes

    return send_msg(chain, chain_data), voice_list, cq_codes


async def append_image(img: Union[bytes, str]):
    if isinstance(img, bytes):
        data = {'file': 'base64://' + base64.b64encode(img).decode()}
    elif is_valid_url(img):
        data = {'url': img}
    else:
        data = {'file': img}

    return {'type': 'image', 'data': data}


async def append_voice(file: str):
    if os.path.exists(file):
        file = 'base64://' + base64.b64encode(await silkcoder.async_encode(file, ios_adaptive=True)).decode()

    return {'type': 'record', 'data': {'file': file}}


def send_msg(chain: Chain, chain_data: Union[str, list]):
    msg_data = {
        'message_type': chain.data.message_type,
        'user_id': chain.data.user_id,
        'group_id': chain.data.channel_id,
        'message': chain_data,
    }
    msg_data = {k: v for k, v in msg_data.items() if v is not None and v != ''}

    return msg_data
