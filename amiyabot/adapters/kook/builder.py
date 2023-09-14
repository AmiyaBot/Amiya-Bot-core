from amiyabot.adapters import MessageCallback
from amiyabot.network.httpRequests import http_requests
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *
from amiyabot.log import LoggerManager

log = LoggerManager('KOOK')


class KOOKMessageCallback(MessageCallback):
    async def recall(self):
        if not self.response:
            log.warning('can not recall message because the response is None.')
            return False
        await self.instance.recall_message(self.response['data']['msg_id'])


async def build_message_send(instance, chain: Chain, custom_chain: Optional[CHAIN_LIST] = None):
    chain_list = custom_chain or chain.chain

    message = {'type': 9, 'content': ''}
    card_message = {'type': 'card', 'theme': 'none', 'size': 'lg', 'modules': []}

    use_card = len(chain_list) > 1 and len([n for n in chain_list if type(n) in [Image, Html, Extend]])

    async def make_text_message(data):
        if use_card:
            if card_message['modules'] and card_message['modules'][-1]['type'] == 'section':
                card_message['modules'][-1]['text']['content'] += data
                return

            card_message['modules'].append({'type': 'section', 'text': {'type': 'kmarkdown', 'content': data}})
            return

        message['content'] += data

    async def make_image_message(data):
        res = await http_requests.request(instance.base_url + '/asset/create', data=data, headers=instance.headers)
        if res:
            async with log.catch():
                url = json.loads(res)['data']['url']

            if use_card:
                card_message['modules'].append({'type': 'container', 'elements': [{'type': 'image', 'src': url}]})
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
            await make_image_message({'file': await item.get()})

        # Voice
        if isinstance(item, Voice):
            pass

        # Html
        if isinstance(item, Html):
            result = await item.create_html_image()
            if result:
                await make_image_message({'file': result})
            else:
                log.warning('html convert fail.')

        # Extend
        if isinstance(item, Extend):
            if use_card:
                card_message['modules'].append(item.get())
            else:
                message = item.get()

    return {'type': 10, 'content': json.dumps([card_message])} if use_card else message
