from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *


@dataclass
class MessageSendRequest:
    data: dict
    direct: bool
    user_id: str
    upload_image: bool = False


class MessageSendRequestGroup:
    def __init__(self, user_id: str, message_id: str, reference: bool, direct: bool):
        self.req_list: List[MessageSendRequest] = []

        self.text: str = ''
        self.user_id: str = user_id
        self.message_id: str = message_id
        self.reference: bool = reference
        self.direct: bool = direct

    def __insert_req(self, content: str = '', image: Union[str, bytes] = None):
        # noinspection PyArgumentList
        req = MessageSendRequest(
            data={
                'msg_id': self.message_id
            },
            direct=self.direct,
            user_id=self.user_id
        )

        if content:
            req.data['content'] = content

        if type(image) is str:
            req.data['image'] = image

        if type(image) is bytes:
            req.data['file_image'] = image
            req.upload_image = True

        if self.reference:
            req.data['message_reference'] = {
                'message_id': self.message_id,
                'ignore_get_message_error': False
            }

        self.req_list.append(req)

    def add_text(self, text: str):
        if self.req_list:
            req = self.req_list[-1]

            if 'content' not in req.data:
                req.data['content'] = ''

            req.data['content'] += text
            return None

        self.text += text

    def add_image(self, image: Union[str, bytes]):
        self.__insert_req(content=self.text, image=image)
        self.text = ''

    def done(self):
        if self.text:
            self.__insert_req(content=self.text)


async def build_message_send(chain: Chain, custom_chain: CHAIN_LIST = None):
    chain_list = custom_chain or chain.chain

    messages = MessageSendRequestGroup(chain.data.user_id,
                                       chain.data.message_id,
                                       chain.reference,
                                       chain.data.is_direct)

    for item in chain_list:
        # At
        if type(item) is At:
            messages.add_text(f'<@{item.target}>')

        # Face
        if type(item) is Face:
            messages.add_text(f'<emoji:{item.face_id}>')

        # Text
        if type(item) is Text:
            messages.add_text(item.content)

        # Image
        if type(item) is Image:
            messages.add_image(await item.get())

        # Voice
        if type(item) is Voice:
            pass

        # Html
        if type(item) is Html:
            result = await item.create_html_image()
            if result:
                messages.add_image(result)
            else:
                log.warning('html convert fail.')

    messages.done()

    return messages
