import asyncio

from typing import Optional
from amiyabot.builtin.messageChain import Chain, ChainBuilder
from amiyabot.adapters.tencent.qqGuild import QQGuildBotInstance

from .api import QQGroupAPI, log
from .builder import (
    QQGroupMessageCallback,
    QQGroupChainBuilder,
    QQGroupChainBuilderOptions,
    SeqService,
    build_message_send,
)
from .package import package_qq_group_message
from ... import HANDLER_TYPE


def qq_group(
    client_secret: str,
    default_chain_builder: Optional[ChainBuilder] = None,
    default_chain_builder_options: QQGroupChainBuilderOptions = QQGroupChainBuilderOptions(),
):
    def adapter(appid: str, token: str):
        if default_chain_builder:
            cb = default_chain_builder
        else:
            cb = QQGroupChainBuilder(default_chain_builder_options)

        return QQGroupBotInstance(appid, token, client_secret, cb)

    return adapter


class QQGroupBotInstance(QQGuildBotInstance):
    def __init__(self, appid: str, token: str, client_secret: str, default_chain_builder: ChainBuilder):
        super().__init__(appid, token)

        self.__access_token_api = QQGroupAPI(self.appid, self.token, client_secret)
        self.__default_chain_builder = default_chain_builder
        self.__seq_service = SeqService()

    def __str__(self):
        return 'QQGroup'

    @property
    def api(self):
        return self.__access_token_api

    @property
    def package_method(self):
        return package_qq_group_message

    async def start(self, private: bool, handler: HANDLER_TYPE):
        if hasattr(self.__default_chain_builder, 'start'):
            self.__default_chain_builder.start()

        asyncio.create_task(self.__seq_service.run())

        await super().start(private, handler)

    async def close(self):
        await self.__seq_service.stop()
        await super().close()

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        if not isinstance(chain.builder, QQGroupChainBuilder):
            chain.builder = self.__default_chain_builder

        payloads = await build_message_send(self.api, chain, self.__seq_service)
        res = []

        for payload in payloads:
            async with log.catch('post error:', ignore=[asyncio.TimeoutError]):
                res.append(
                    await self.api.post_group_message(
                        chain.data.channel_openid,
                        payload,
                    )
                )

        return [QQGroupMessageCallback(chain.data, self, item) for item in res]
