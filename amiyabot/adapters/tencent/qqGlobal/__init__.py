from typing import Optional

from amiyabot.builtin.messageChain import Chain, ChainBuilder
from amiyabot.adapters.tencent.qqGuild import QQGuildBotInstance
from amiyabot.adapters.tencent.qqGroup import QQGroupBotInstance, QQGroupChainBuilder
from amiyabot.adapters.tencent.qqGroup.builder import QQGroupChainBuilderOptions

from .package import package_qq_global_message


class QQGlobalBotInstance(QQGroupBotInstance):
    def __init__(
        self,
        appid: str,
        token: str,
        client_secret: str,
        default_chain_builder: ChainBuilder,
        shard_index: int,
        shards: int,
        subscribe_group_member_event: bool = False,
    ):
        super().__init__(
            appid,
            token,
            client_secret,
            default_chain_builder,
            shard_index,
            shards,
            subscribe_group_member_event,
        )

        self.guild = QQGuildBotInstance(appid, token, shard_index, shards)

    def __str__(self):
        return 'QQGlobal'

    @property
    def package_method(self):
        return package_qq_global_message

    @classmethod
    def build_adapter(
        cls,
        client_secret: str,
        default_chain_builder: Optional[ChainBuilder] = None,
        default_chain_builder_options: QQGroupChainBuilderOptions = QQGroupChainBuilderOptions(),
        shard_index: int = 0,
        shards: int = 1,
        subscribe_group_member_event: bool = False,
    ):
        def adapter(appid: str, token: str):
            if default_chain_builder:
                cb = default_chain_builder
            else:
                cb = QQGroupChainBuilder(default_chain_builder_options)

            return cls(
                appid,
                token,
                client_secret,
                cb,
                shard_index,
                shards,
                subscribe_group_member_event,
            )

        return adapter

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        if not (chain.data.channel_openid or chain.data.user_openid):
            return await self.guild.send_chain_message(chain, is_sync)
        return await super().send_chain_message(chain, is_sync)


qq_global = QQGlobalBotInstance.build_adapter
