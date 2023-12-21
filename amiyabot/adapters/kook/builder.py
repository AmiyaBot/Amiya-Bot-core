from amiyabot.adapters import MessageCallback
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *

from .api import KOOKAPI, log


class KOOKMessageCallback(MessageCallback):
    async def recall(self):
        if not self.response:
            log.warning('can not recall message because the response is None.')
            return False

        await self.instance.recall_message(self.response.json['data']['msg_id'])

    async def get_message(self):
        if not self.response:
            return None

        api: KOOKAPI = self.instance.api

        message = await api.get_message(self.response.json['data']['msg_id'])

        if message.json['code'] != 0:
            return None

        message_data = message.json['data']
        user = message_data['author']

        data = Message(self.instance, message_data)

        data.message_id = message_data['id']
        data.message_type = 'GROUP'

        data.is_at = bool(message_data['mention'])
        data.at_target = message_data['mention']

        data.user_id = user['id']
        data.guild_id = message_data.get('guild_id', '')
        data.channel_id = message_data['channel_id']
        data.nickname = user['nickname'] or user['username']
        data.avatar = user['vip_avatar'] or user['avatar']

        data.text = message_data['content']

        return data


async def build_message_send(api: KOOKAPI, chain: Chain, custom_chain: Optional[CHAIN_LIST] = None):
    chain_list = custom_chain or chain.chain

    message = {
        'type': 9,
        'content': '',
    }
    card_message = {
        'type': 'card',
        'theme': 'none',
        'size': 'lg',
        'modules': [],
    }

    use_card = len(chain_list) > 1 and len([n for n in chain_list if type(n) in [Image, Html, Extend]])

    async def make_text_message(data):
        if use_card:
            if card_message['modules'] and card_message['modules'][-1]['type'] == 'section':
                card_message['modules'][-1]['text']['content'] += data
                return

            card_message['modules'].append(
                {
                    'type': 'section',
                    'text': {'type': 'kmarkdown', 'content': data},
                }
            )
            return

        message['content'] += data

    async def make_image_message(data):
        res = await api.create_asset(data)
        if res:
            async with log.catch('make image error'):
                url = res.json['data']['url']

            if use_card:
                card_message['modules'].append(
                    {
                        'type': 'container',
                        'elements': [{'type': 'image', 'src': url}],
                    }
                )
            else:
                message['type'] = 2
                message['content'] = url

    for item in chain_list:
        # At
        if isinstance(item, At):
            await make_text_message(f'(met){item.target}(met)')

        # AtAll
        if isinstance(item, AtAll):
            await make_text_message('(met)all(met)')

        # Face
        if isinstance(item, Face):
            await make_text_message(f'(emj){item.face_id}(emj)[{item.face_id}]')

        # Text
        if isinstance(item, Text):
            await make_text_message(item.content)

        # Image
        if isinstance(item, Image):
            await make_image_message(await item.get())

        # Html
        if isinstance(item, Html):
            result = await item.create_html_image()
            if result:
                await make_image_message(result)

        # Extend
        if isinstance(item, Extend):
            if use_card:
                card_message['modules'].append(item.get())
            else:
                message = item.get()

    return {'type': 10, 'content': json.dumps([card_message])} if use_card else message
