import asyncio

from typing import Optional
from amiyabot.builtin.messageChain import Chain, ChainBuilder
from amiyabot.adapters import HANDLER_TYPE
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


class QQGroupBotInstance(QQGuildBotInstance):
    def __init__(
        self,
        appid: str,
        token: str,
        client_secret: str,
        default_chain_builder: ChainBuilder,
        shard_index: int,
        shards: int,
    ):
        super().__init__(appid, token, shard_index, shards)

        self.__access_token_api = QQGroupAPI(self.appid, self.token, client_secret)
        self.__default_chain_builder = default_chain_builder
        self.__seq_service = SeqService()

    def __str__(self):
        return 'QQGroup'

    @classmethod
    def build_adapter(
        cls,
        client_secret: str,
        default_chain_builder: Optional[ChainBuilder] = None,
        default_chain_builder_options: QQGroupChainBuilderOptions = QQGroupChainBuilderOptions(),
        shard_index: int = 0,
        shards: int = 1,
    ):
        def adapter(appid: str, token: str):
            if default_chain_builder:
                cb = default_chain_builder
            else:
                cb = QQGroupChainBuilder(default_chain_builder_options)

            return cls(appid, token, client_secret, cb, shard_index, shards)

        return adapter

    @property
    def api(self):
        return self.__access_token_api

    @property
    def package_method(self):
        return package_qq_group_message

    async def start(self, handler: HANDLER_TYPE):
        if hasattr(self.__default_chain_builder, 'start'):
            self.__default_chain_builder.start()

        if not self.__seq_service.alive:
            asyncio.create_task(self.__seq_service.run())

        await super().start(handler)

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
                    await (
                        self.api.post_private_message(
                            chain.data.user_openid,
                            payload,
                        )
                        if chain.data.is_direct
                        else self.api.post_group_message(
                            chain.data.channel_openid,
                            payload,
                        )
                    )
                )

        return [QQGroupMessageCallback(chain.data, self, item) for item in res]


qq_group = QQGroupBotInstance.build_adapter
