import time

from typing import Type
from graiax import silkcoder
from amiyabot.adapters import MessageCallback
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *
from amiyabot.util import is_valid_url

from .payload import WebsocketAdapter, HttpAdapter, MiraiPostPayload
from .api import MiraiAPI


class MiraiMessageCallback(MessageCallback):
    async def recall(self):
        if not self.response:
            log.warning('can not recall message because the response is None.')
            return False

        await self.instance.recall_message(self.response.json['messageId'], self.data)

    async def get_message(self):
        return None


async def build_message_send(
    api: MiraiAPI,
    chain: Chain,
    custom_chain: Optional[CHAIN_LIST] = None,
    chain_only: bool = False,
    use_http: bool = False,
):
    chain_list = custom_chain or chain.chain
    chain_data = []
    voice_list = []

    payload_builder = HttpAdapter if use_http else WebsocketAdapter

    if chain_list:
        for item in chain_list:
            # At
            if isinstance(item, At):
                chain_data.append({'type': 'At', 'target': item.target or chain.data.user_id})

            # AtAll
            if isinstance(item, AtAll):
                chain_data.append({'type': 'AtAll'})

            # Face
            if isinstance(item, Face):
                chain_data.append({'type': 'Face', 'faceId': item.face_id})

            # Text
            if isinstance(item, Text):
                chain_data.append({'type': 'Plain', 'text': item.content})

            # Image
            if isinstance(item, Image):
                target = await item.get()
                if is_valid_url(target):
                    chain_data.append({'type': 'Image', 'url': target})
                else:
                    chain_data.append(
                        {
                            'type': 'Image',
                            'imageId': await get_image_id(api, target, chain.data.message_type),
                        }
                    )

            # Voice
            if isinstance(item, Voice):
                voice_item = {
                    'type': 'Voice',
                    'voiceId': await get_voice_id(api, item.file, chain.data.message_type),
                }
                if chain_only:
                    voice_list.append(voice_item)
                else:
                    voice_list.append(select_type(chain, api.session, [voice_item], payload_builder))

            # Html
            if isinstance(item, Html):
                result = await item.create_html_image()
                if result:
                    chain_data.append(
                        {
                            'type': 'Image',
                            'imageId': await get_image_id(api, result, chain.data.message_type),
                        }
                    )

            # Extend
            if isinstance(item, Extend):
                chain_data.append(item.get())

    if chain_only:
        return chain_data, voice_list

    return select_type(chain, api.session, chain_data, payload_builder), voice_list


async def get_image_id(http: MiraiAPI, target: Union[str, bytes], msg_type: str):
    if isinstance(target, str):
        with open(target, mode='rb') as file:
            target = file.read()

    # 在图片里夹点私货，让 Mirai 返回不一样的 ID
    target += str(time.time()).encode()

    return await http.upload_image(target, msg_type)


async def get_voice_id(http: MiraiAPI, path: str, msg_type: str):
    return await http.upload_voice(await silkcoder.async_encode(path, ios_adaptive=True), msg_type)


def select_type(
    chain: Chain,
    session: str,
    chain_data: List[dict],
    payload_builder: Type[MiraiPostPayload],
):
    reply = None

    if chain_data:
        if chain.data.message_type == 'group':
            reply = payload_builder.group_message(
                session,
                chain.data.channel_id,
                chain_data,
                quote=chain.data.message_id if chain.reference else None,
            )
        if chain.data.message_type == 'temp':
            reply = payload_builder.temp_message(session, chain.data.user_id, chain.data.channel_id, chain_data)
        if chain.data.message_type == 'friend':
            reply = payload_builder.friend_message(session, chain.data.user_id, chain_data)

    return reply
