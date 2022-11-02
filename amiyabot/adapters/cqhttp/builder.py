import os
import json
import base64

from graiax import silkcoder
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *
from amiyabot import log


async def build_message_send(chain: Chain, custom_chain: CHAIN_LIST = None):
    chain_list = custom_chain or chain.chain
    chain_data = []
    voice_list = []

    if chain_list:
        for item in chain_list:
            # At
            if type(item) is At:
                chain_data.append({
                    'type': 'at',
                    'data': {
                        'qq': item.target or chain.data.user_id
                    }
                })

            # Face
            if type(item) is Face:
                chain_data.append({
                    'type': 'face',
                    'data': {
                        'id': item.face_id
                    }
                })

            # Text
            if type(item) is Text:
                chain_data.append({
                    'type': 'text',
                    'data': {
                        'text': item.content
                    }
                })

            # Image
            if type(item) is Image:
                img = await item.get()
                chain_data.append(await append_image(img))

            # Voice
            if type(item) is Voice:
                voice_list.append(send_msg(chain, [await append_voice(item.file)]))

            # Html
            if type(item) is Html:
                result = await item.create_html_image()
                if result:
                    chain_data.append(await append_image(result))
                else:
                    log.warning('html convert fail.')

    return send_msg(chain, chain_data), voice_list


async def append_image(img: Union[bytes, str]):
    if type(img) is bytes:
        img = 'base64://' + base64.b64encode(img).decode()

    return {
        'type': 'image',
        'data': {
            'file': img
        }
    }


async def append_voice(file: str):
    if os.path.exists(file):
        file = 'base64://' + base64.b64encode(await silkcoder.async_encode(file, ios_adaptive=True)).decode()

    return {
        'type': 'record',
        'data': {
            'file': file
        }
    }


def send_msg(chain: Chain, chain_data: list):
    return json.dumps({
        'action': 'send_msg',
        'params': {
            'message_type': chain.data.message_type,
            'user_id': chain.data.user_id,
            'group_id': chain.data.channel_id,
            'message': chain_data
        }
    })
