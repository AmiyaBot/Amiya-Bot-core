from typing import Union
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain

from .api import MiraiAPI
from .builder import build_message_send


class MiraiForwardMessage:
    def __init__(self, data: Message):
        self.data = data
        self.api: MiraiAPI = data.instance.api
        self.node = {
            'type': 'Forward',
            'nodeList': []
        }

    async def add_message(self,
                          chain: Union[Chain, dict],
                          user_id: int = None,
                          nickname: str = None,
                          time: int = 0):
        node = {
            'time': time,
            'senderId': user_id,
            'senderName': nickname
        }

        if type(chain) is Chain:
            if not chain.data:
                source = Message(self.data.instance)
                source.user_id = user_id
                source.nickname = nickname
                source.message_type = 'group'

                chain.data = source

            chain_data, voice_list = await build_message_send(self.api, chain, chain_only=True)

            node['senderId'] = chain.data.user_id
            node['senderName'] = chain.data.nickname

            self.node['nodeList'].append({**node, 'messageChain': chain_data})
            for _ in voice_list:
                self.node['nodeList'].append({**node, 'messageChain': [
                    {
                        'type': 'Plain',
                        'text': '[语音]'
                    }
                ]})
        else:
            self.node['nodeList'].append({**node, 'messageChain': [chain]})

    async def add_message_by_id(self, message_id: int):
        self.node['nodeList'].append({
            'messageId': message_id
        })

    async def add_message_by_ref(self, message_id: int, target: int):
        self.node['nodeList'].append({
            'messageRef': {
                'messageId': message_id,
                'target': target
            }
        })

    async def send(self):
        await self.api.send_group_message(self.data.channel_id, [self.node])
