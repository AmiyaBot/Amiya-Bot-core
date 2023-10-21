from amiyabot.adapters.onebot12 import OneBot12Instance
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

    async def package_message(self, event: str, message: dict):
        return await package_com_wechat_message(self, message)

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        reply = await build_message_send(self.api, chain)

        res = []
        request = await self.api.post('/', {'action': 'send_message', 'params': reply})
        if request:
            res.append(request)

        return [ComWeChatMessageCallback(self, item) for item in res]
