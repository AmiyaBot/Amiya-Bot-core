import abc
import json

from typing import Callable, Optional
from amiyabot.network.httpRequests import http_requests
from amiyabot.builtin.messageChain.element import MessageSendRequest
from amiyabot import log

from .url import APIConstant, get_url
from .model import GateWay, ConnectionHandler


class TencentConnect:
    def __init__(self, appid: str, token: str):
        self.appid = appid
        self.token = token

        self.headers = {
            'Authorization': f'Bot {appid}.{token}'
        }

    async def connect(self, private: bool, handler: Callable):
        resp = await self.__get_request(APIConstant.gatewayBotURI)
        gateway = GateWay(**resp)

        log.info(f'appid {self.appid} gateway resp: shards {gateway.shards}, remaining %d/%d' % (
            gateway.session_start_limit['remaining'],
            gateway.session_start_limit['total']
        ))

        await self.create_connection(
            ConnectionHandler(
                private=private,
                gateway=gateway,
                message_handler=handler
            )
        )

    async def get_me(self):
        return await self.__get_request(APIConstant.userMeURI)

    async def get_message(self, channel_id: str, message_id: str):
        return await self.__get_request(APIConstant.messageURI.format(channel_id=channel_id, message_id=message_id))

    async def post_message(self, guild_id: str, src_guild_id: str, channel_id: str, req: MessageSendRequest):
        if req.direct:
            if not guild_id or not req.data['msg_id']:
                create_direct = await self.__post_request(APIConstant.userMeDMURI, {
                    'recipient_id': req.user_id,
                    'source_guild_id': src_guild_id
                })
                guild_id = create_direct['guild_id']

            api = APIConstant.dmsURI.format(guild_id=guild_id)
        else:
            api = APIConstant.messagesURI.format(channel_id=channel_id)

        return await self.__post_request(api, req.data, req.upload_image)

    @abc.abstractmethod
    async def create_connection(self, gateway: ConnectionHandler, shards_index: int = 0):
        pass

    @staticmethod
    def __check_response(response_text: Optional[str]) -> Optional[dict]:
        if response_text is None:
            return None

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ResponseException(0, repr(e))

        if 'code' in data and data['code'] != 200:
            raise ResponseException(**data)

        return data

    async def __get_request(self, url: str):
        return self.__check_response(
            await http_requests.get(get_url(url), headers=self.headers)
        )

    async def __post_request(self, url: str, payload: dict = None, is_form_data: bool = False):
        if is_form_data:
            return self.__check_response(
                await http_requests.post_form_data(get_url(url), payload, headers=self.headers)
            )
        return self.__check_response(
            await http_requests.post(get_url(url), payload, headers=self.headers)
        )


class ResponseException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

    def __str__(self):
        return f'[{self.code}] {self.message}'
