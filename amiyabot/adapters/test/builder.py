import uuid
import base64

from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *


async def build_message_send(chain: Chain, custom_chain: Optional[CHAIN_LIST] = None):
    chain_list = custom_chain or chain.chain
    chain_data = []
    voice_list = []

    if chain.data and chain.data.message_id:
        event_id = chain.data.message_id
    else:
        event_id = str(uuid.uuid4())

    if chain_list:
        for item in chain_list:
            # At
            if isinstance(item, At):
                chain_data.append({'type': 'text', 'data': f'@{chain.data.nickname}'})

            # AtAll
            if isinstance(item, AtAll):
                chain_data.append({'type': 'text', 'data': '@All'})

            # Face
            if isinstance(item, Face):
                chain_data.append({'type': 'face', 'data': item.face_id})

            # Text
            if isinstance(item, Text):
                chain_data.append({'type': 'text', 'data': item.content})

            # Image
            if isinstance(item, Image):
                img = await item.get()
                chain_data.append({'type': 'image', 'data': await append_image(img)})

            # Voice
            if isinstance(item, Voice):
                d, t = await append_voice(item.file)
                voice_list.append(
                    send_msg(
                        event_id,
                        [
                            {
                                'type': 'voice',
                                'data': d,
                                'file': os.path.basename(item.file),
                                'audio_type': f'audio/{t}',
                            }
                        ],
                    )
                )

            # Html
            if isinstance(item, Html):
                result = await item.create_html_image()
                if result:
                    chain_data.append({'type': 'image', 'data': await append_image(result)})

    return send_msg(event_id, chain_data), voice_list


async def append_image(img: Union[bytes, str]):
    if isinstance(img, bytes):
        img = 'data:image/png;base64,' + base64.b64encode(img).decode()
    return img


async def append_voice(file: str):
    _type = os.path.splitext(file)[-1].strip('.')

    with open(file, mode='rb') as vf:
        data = vf.read()

    return f'data:audio/{_type};base64,{base64.b64encode(data).decode()}', _type


def send_msg(event_id: str, chain_data: list):
    return json.dumps(
        {
            'event': 'message',
            'event_id': event_id,
            'event_data': chain_data,
        },
        ensure_ascii=False,
    )
