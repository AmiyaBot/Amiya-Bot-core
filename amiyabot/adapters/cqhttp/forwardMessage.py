import copy

from typing import Union
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain

from .api import CQHttpAPI
from .builder import build_message_send


class CQHTTPForwardMessage:
    def __init__(self, data: Message):
        self.data = data
        self.node = []

    async def add_message(self,
                          chain: Union[Chain, list],
                          user_id: int = None,
                          nickname: str = None):
        node = {
            'type': 'node',
            'data': {
                'uin': user_id,
                'name': nickname,
                'content': chain if type(chain) is list else []
            }
        }

        if type(chain) is Chain:
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
                node['data']['content'] = [
                    {
                        'type': 'text',
                        'data': {
                            'text': '[语音]'
                        }
                    }
                ]
                self.node.append(copy.deepcopy(node))

            for item in cq_codes:
                node['data']['content'] = [
                    {
                        'type': 'text',
                        'data': {
                            'text': item['message']
                        }
                    }
                ]
                self.node.append(copy.deepcopy(node))
        else:
            self.node.append(node)

    async def add_message_by_id(self, message_id: int):
        self.node.append({
            'type': 'node',
            'data': {
                'id': message_id
            }
        })

    async def send(self):
        api: CQHttpAPI = self.data.instance.api
        await api.send_group_forward_msg(self.data.channel_id, self.node)
