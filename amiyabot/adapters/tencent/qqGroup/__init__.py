import asyncio

from typing import Optional
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain, ChainBuilder
from amiyabot.adapters import HANDLER_TYPE
from amiyabot.adapters.tencent.qqGuild import QQGuildBotInstance

from .api import QQGroupAPI, log
from .builder import (
    QQGroupMessageCallback,
    QQGroupChainBuilder,
    QQGroupChainBuilderOptions,
    QQGroupMessageError,
    SeqService,
    build_message_send,
    raise_for_send_error,
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
        subscribe_group_member_event: bool = False,
    ):
        super().__init__(appid, token, shard_index, shards)

        self.__access_token_api = QQGroupAPI(self.appid, self.token, client_secret)
        self.__default_chain_builder = default_chain_builder
        self.__seq_service = SeqService()

        self.subscribe_group_member_event = subscribe_group_member_event

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

    @property
    def api(self):
        return self.__access_token_api

    @property
    def package_method(self):
        return package_qq_group_message

    @property
    def ws_auth_token(self) -> str:
        # v2 群机器人无需旧 token，WebSocket 鉴权使用 AccessToken
        # （官方文档仅保留 "QQBot {AccessToken}" 格式，旧 "Bot appid.token" 会返回 4004）
        # headers property 会在首次或临近过期时自动刷新
        _ = self.api.headers
        return f'QQBot {self.api.access_token}'

    async def start(self, handler: HANDLER_TYPE):
        if hasattr(self.__default_chain_builder, 'start'):
            self.__default_chain_builder.start()

        if not self.__seq_service.alive:
            asyncio.create_task(self.__seq_service.run())

        await super().start(handler)

    async def close(self):
        await self.__seq_service.stop()
        await super().close()

    async def recall_message(self, message_id: str, data: Optional[Message] = None):
        """
        撤回群聊/单聊消息。
        覆盖 qqGuild 的实现（其使用频道 `/channels/...` 端点，对群消息无效）。
        """
        if data is None:
            raise TypeError('recall_message() missing argument: "data"')

        if data.is_direct:
            return await self.api.delete_private_message(data.user_openid, message_id)

        return await self.api.delete_group_message(data.channel_openid, message_id)

    async def send_chain_message(self, chain: Chain, is_sync: bool = False):
        if not isinstance(chain.builder, QQGroupChainBuilder):
            chain.builder = self.__default_chain_builder

        payloads = await build_message_send(self.api, chain, self.__seq_service)
        res = []

        for payload in payloads:
            response = None

            async with log.catch('post error:', ignore=[asyncio.TimeoutError]):
                response = await (
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
                res.append(response)

            # 已知错误码（event_id 过期 / msg_id 越权 / 事件不支持回复）转成带 code 的异常，
            # 其余错误保持原有「仅记录日志」行为
            raise_for_send_error(response)

        return [QQGroupMessageCallback(chain.data, self, item) for item in res]

    async def send_event_message(self, chain: Chain, event_id: str = '', is_sync: bool = True):
        """
        以事件 ID 为锚点发送被动消息（按钮回调、入群事件等）。

        与 message_id 锚点二选一，msg_seq 由 SeqService 递增；同一事件 5 分钟内最多回复 5 条。

        :param chain:   消息 Chain 对象
        :param event_id: 事件 ID（事件最外层的 id），为空时使用 chain.data.event_id
        :param is_sync: 是否同步发送消息
        :return:        MessageCallback 列表
        """
        if chain.data is None:
            raise TypeError('send_event_message() missing chain data')

        if event_id:
            chain.data.event_id = event_id

        if not getattr(chain.data, 'event_id', ''):
            raise ValueError('send_event_message() missing argument: "event_id"')

        return await self.send_chain_message(chain, is_sync=is_sync)


qq_group = QQGroupBotInstance.build_adapter
