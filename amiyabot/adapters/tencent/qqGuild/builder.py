from amiyabot.adapters import MessageCallback
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *

from .api import QQGuildAPI, MessageSendRequest
from .package import package_qq_guild_message


class QQGuildMessageCallback(MessageCallback):
    async def recall(self):
        if not self.response:
            log.warning('can not recall message because the response is None.')
            return False

        await self.instance.recall_message(self.response.json['id'], self.data)

    async def get_message(self):
        if not self.response:
            return None

        api: QQGuildAPI = self.instance.api

        response = self.response.json
        message = await api.get_message(response['channel_id'], response['id'])
        data = message.json['message']

        if isinstance(data, dict):
            return await package_qq_guild_message(self.instance, 'MESSAGE_CREATE', data, True)


class MessageSendRequestGroup:
    def __init__(self, user_id: str, message_id: str, reference: bool, direct: bool):
        self.req_list: List[MessageSendRequest] = []

        self.text: str = ''
        self.user_id: str = user_id
        self.message_id: str = message_id
        self.reference: bool = reference
        self.direct: bool = direct

    def __insert_req(self, content: str = '', image: Optional[Union[str, bytes]] = None, data: Optional[dict] = None):
        req = MessageSendRequest(
            data={
                'msg_id': self.message_id,
                **(data or {}),
            },
            direct=self.direct,
            user_id=self.user_id,
        )

        if content:
            req.data['content'] = content

        if isinstance(image, str):
            req.data['image'] = image

        if isinstance(image, bytes):
            req.data['file_image'] = image
            req.upload_image = True

        if self.reference:
            req.data['message_reference'] = {
                'message_id': self.message_id,
                'ignore_get_message_error': False,
            }

        self.req_list.append(req)

    def add_text(self, text: str):
        if self.req_list:
            req_data = self.req_list[-1].data

            if 'embed' not in req_data and 'ark' not in req_data:
                if 'content' not in req_data:
                    req_data['content'] = ''

                req_data['content'] += text
                return None

        self.text += text

    def add_image(self, image: Union[str, bytes]):
        self.__insert_req(content=self.text, image=image)
        self.text = ''

    def add_data(self, data: Optional[dict]):
        self.done()
        self.__insert_req(data=data)

    def done(self):
        if self.text:
            self.__insert_req(content=self.text)
            self.text = ''


async def build_message_send(chain: Chain, custom_chain: Optional[CHAIN_LIST] = None):
    chain_list = custom_chain or chain.chain

    messages = MessageSendRequestGroup(
        chain.data.user_id,
        chain.data.message_id,
        chain.reference,
        chain.data.is_direct,
    )

    for item in chain_list:
        # At
        if isinstance(item, At):
            messages.add_text(f'<@{item.target}>')

        # AtAll
        if isinstance(item, AtAll):
            messages.add_text('<@everyone>')

        # Tag
        if isinstance(item, Tag):
            messages.add_text(f'<#{item.target}>')

        # Face
        if isinstance(item, Face):
            messages.add_text(f'<emoji:{item.face_id}>')

        # Text
        if isinstance(item, Text):
            messages.add_text(item.content)

        # Image
        if isinstance(item, Image):
            messages.add_image(await item.get())

        # Html
        if isinstance(item, Html):
            result = await item.create_html_image()
            if result:
                messages.add_image(result)

        # Embed
        if isinstance(item, Embed):
            messages.add_data(item.get())

        # Ark
        if isinstance(item, Ark):
            messages.add_data(item.get())

        # Markdown
        if isinstance(item, Markdown):
            messages.add_data(item.get())

    messages.done()

    return messages
