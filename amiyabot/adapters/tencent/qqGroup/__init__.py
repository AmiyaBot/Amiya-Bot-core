import asyncio

from amiyabot.builtin.messageChain import Chain
from amiyabot.adapters.tencent.qqGuild import QQGuildBotInstance

from .api import QQGroupAPI, log
from .builder import QQGroupMessageCallback, build_message_send
from .package import package_qq_group_message


def qq_group(client_secret: str):
    def adapter(appid: str, token: str):
        return QQGroupBotInstance(appid, token, client_secret)

    return adapter


class QQGroupBotInstance(QQGuildBotInstance):
    def __init__(self, appid: str, token: str, client_secret: str):
        super().__init__(appid, token)

        self.__access_token_api = QQGroupAPI(self.appid, client_secret)

    def __str__(self):
        return 'QQGroup'

    @property
    def api(self):
        return self.__access_token_api

    @property
    def package_method(self):
        return package_qq_group_message

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        payloads = await build_message_send(self.api, chain)
        res = []

        for payload in payloads:
            async with log.catch('post error:', ignore=[asyncio.TimeoutError]):
                res.append(
                    await self.api.post_message(
                        chain.data.channel_openid,
                        payload,
                    )
                )

        return [QQGroupMessageCallback(chain.data, self, item) for item in res]
