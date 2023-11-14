import copy

from typing import Union, Optional
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.adapters.onebot.v11.builder import build_message_send, OneBot11MessageCallback

from .api import CQHttpAPI


class CQHTTPForwardMessage:
    def __init__(self, data: Message):
        self.data = data
        self.api: CQHttpAPI = data.instance.api
        self.node = []

    async def add_message(
        self, chain: Union[Chain, list], user_id: Optional[int] = None, nickname: Optional[str] = None
    ):
        node = {
            'type': 'node',
            'data': {
                'uin': user_id,
                'name': nickname,
                'content': chain if isinstance(chain, list) else [],
            },
        }

        if isinstance(chain, Chain):
            if not chain.data:
                source = Message(self.data.instance)
                source.user_id = user_id
                source.nickname = nickname
                source.message_type = 'group'

                chain.data = source

            chain_data, voice_list, cq_codes = await build_message_send(chain, chain_only=True)

            node['data']['content'] = chain_data

            self.node.append(copy.deepcopy(node))

            for _ in voice_list:
                node['data']['content'] = [{'type': 'text', 'data': {'text': '[语音]'}}]
                self.node.append(copy.deepcopy(node))

            for item in cq_codes:
                node['data']['content'] = [{'type': 'text', 'data': {'text': item['message']}}]
                self.node.append(copy.deepcopy(node))
        else:
            self.node.append(node)

    async def add_message_by_id(self, message_id: int):
        self.node.append({'type': 'node', 'data': {'id': message_id}})

    async def send(self):
        chain = Chain()
        chain.raw_chain = self.node

        async with self.data.bot.processing_context(chain, self.data.factory_name):
            callback = OneBot11MessageCallback(
                self.data,
                self.data.instance,
                await self.api.send_group_forward_msg(self.data.channel_id, self.node),
            )

        return callback
