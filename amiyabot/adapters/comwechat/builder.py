from amiyabot.adapters import MessageCallback
from amiyabot.adapters.api import BotInstanceAPIProtocol
from amiyabot.adapters.onebot12.builder import build_message_send as build_ob12
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *


class ComWeChatMessageCallback(MessageCallback):
    async def recall(self):
        return False


async def build_message_send(api: BotInstanceAPIProtocol, chain: Chain):
    async def handle_item(item: CHAIN_ITEM):
        # Face
        if isinstance(item, Face):
            return {'type': 'wx.emoji', 'data': {'file_id': item.face_id}}

    return build_ob12(api, chain, handle_item)
