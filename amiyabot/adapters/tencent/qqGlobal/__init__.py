from amiyabot.builtin.messageChain import Chain, ChainBuilder
from amiyabot.adapters.tencent.qqGuild import QQGuildBotInstance
from amiyabot.adapters.tencent.qqGroup import QQGroupBotInstance

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
    ):
        super().__init__(appid, token, client_secret, default_chain_builder, shard_index, shards)

        self.guild = QQGuildBotInstance(appid, token, shard_index, shards)

    def __str__(self):
        return 'QQGlobal'

    @property
    def package_method(self):
        return package_qq_global_message

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        if not (chain.data.channel_openid or chain.data.user_openid):
            return await self.guild.send_chain_message(chain, is_sync)
        return await super().send_chain_message(chain, is_sync)


qq_global = QQGlobalBotInstance.build_adapter
