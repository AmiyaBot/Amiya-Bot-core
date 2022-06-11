import qqbot
import asyncio

from qqbot.api import User
from qqbot.model import AudioControl
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot import log

from contextlib import asynccontextmanager
from typing import Optional


class BotInstance:
    def __init__(self, appid: str, token: str):
        self.appid = appid
        self.token = qqbot.Token(appid, token)

        self.user_api = qqbot.AsyncUserAPI(self.token, False)
        self.guild_api = qqbot.AsyncGuildAPI(self.token, False)
        self.channel_api = qqbot.AsyncChannelAPI(self.token, False)

        self.audio_api = qqbot.AsyncAudioAPI(self.token, False)
        self.message_api = qqbot.AsyncMessageAPI(self.token, False)

        self.bot: Optional[User] = None

    async def get_me(self) -> User:
        if not self.bot:
            self.bot = await self.user_api.me()
        return self.bot

    async def send_chain_message(self, messages: Chain):
        reqs = await messages.build()
        for req in reqs:
            async with log.catch('post error:', ignore=[asyncio.TimeoutError]):
                if type(req) is qqbot.MessageSendRequest:
                    await self.message_api.post_message(messages.data.channel_id, req)
                elif type(req) is AudioControl:
                    await self.audio_api.post_audio(messages.data.channel_id, req)

    @asynccontextmanager
    async def send_message(self, channel_id: str, user_id: str = None):
        custom = qqbot.Message()
        author = User()

        author.id = user_id
        custom.author = author
        custom.channel_id = channel_id

        chain = Chain(Message(self, custom))

        yield chain

        await self.send_chain_message(chain)
