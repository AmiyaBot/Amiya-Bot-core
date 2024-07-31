import asyncio

from amiyabot.adapters import HANDLER_TYPE
from amiyabot.adapters.onebot.v12 import OneBot12Instance
from amiyabot.builtin.messageChain import Chain

from .package import package_com_wechat_message
from .builder import build_message_send, ComWeChatMessageCallback


def com_wechat(host: str, ws_port: int, http_port: int):
    def adapter(appid: str, token: str):
        return ComWeChatBotInstance(appid, token, host, ws_port, http_port)

    return adapter


class ComWeChatBotInstance(OneBot12Instance):
    def __str__(self):
        return 'ComWeChat'

    async def start(self, handler: HANDLER_TYPE):
        while self.keep_run:
            await self.keep_connect(handler, package_method=package_com_wechat_message)
            await asyncio.sleep(10)

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        reply = await build_message_send(self.api, chain)

        res = []
        request = await self.api.post('/', self.api.ob12_action('send_message', reply))
        if request:
            res.append(request)

        return [ComWeChatMessageCallback(chain.data, self, item) for item in res]
