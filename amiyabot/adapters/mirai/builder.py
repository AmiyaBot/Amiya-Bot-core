from graiax import silkcoder
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *

from .payload import WebsocketAdapter
from .api import MiraiAPI


async def get_image_id(http: MiraiAPI, target, msg_type):
    if type(target) is str:
        with open(target, mode='rb') as file:
            target = file.read()

    return await http.upload_image(target, msg_type)


async def get_voice_id(http: MiraiAPI, path, msg_type):
    return await http.upload_voice(await silkcoder.async_encode(path), msg_type)


async def build_message_send(address: str, session: str, chain: Chain, custom_chain: CHAIN_LIST = None):
    chain_list = custom_chain or chain.chain
    chain_data = []
    voice_list = []

    api = MiraiAPI(address, session)

    if chain_list:
        for item in chain_list:
            # At
            if type(item) is At:
                chain_data.append({
                    'type': 'At',
                    'target': item.target or chain.data.user_id
                })

            # Face
            if type(item) is Face:
                chain_data.append({
                    'type': 'Face',
                    'faceId': item.face_id
                })

            # Text
            if type(item) is Text:
                chain_data.append({
                    'type': 'Plain',
                    'text': item.content
                })

            # Image
            if type(item) is Image:
                chain_data.append({
                    'type': 'Image',
                    'imageId': await get_image_id(api, item.url or item.content, chain.data.message_type)
                })

            # Voice
            if type(item) is Voice:
                voice_list.append(select_type(chain, session, {
                    'type': 'Voice',
                    'voiceId': await get_voice_id(api, item.url, chain.data.message_type)
                }))

            # Html
            if type(item) is Html:
                chain_data.append({
                    'type': 'Image',
                    'imageId': await get_image_id(api, await item.create_html_image(), chain.data.message_type)
                })

    return select_type(chain, session, chain_data), voice_list


def select_type(chain: Chain, session: str, chain_data):
    reply = None

    if chain_data:
        if chain.data.message_type == 'group':
            reply = WebsocketAdapter.group_message(session,
                                                   chain.data.channel_id,
                                                   chain_data,
                                                   quote=chain.data.message_id if chain.reference else None)
        if chain.data.message_type == 'temp':
            reply = WebsocketAdapter.temp_message(session,
                                                  chain.data.user_id,
                                                  chain.data.channel_id,
                                                  chain_data)
        if chain.data.message_type == 'friend':
            reply = WebsocketAdapter.friend_message(session,
                                                    chain.data.user_id,
                                                    chain_data)

    return reply
