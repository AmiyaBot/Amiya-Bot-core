import json
import asyncio

from typing import Optional
from dataclasses import dataclass
from amiyabot.network.httpRequests import http_requests, ResponseException
from amiyabot.adapters.api import BotInstanceAPIProtocol
from amiyabot.log import LoggerManager

from .url import APIConstant, get_url

log = LoggerManager('Tencent')


@dataclass
class MessageSendRequest:
    data: dict
    direct: bool
    user_id: str
    upload_image: bool = False


class TencentAPI(BotInstanceAPIProtocol):
    def __init__(self, appid: str, token: str):
        self.appid = appid
        self.token = token

    @property
    def headers(self):
        return {'Authorization': f'Bot {self.appid}.{self.token}'}

    async def get(self, url: str, *args, **kwargs):
        return self.__check_response(
            await http_requests.get(
                get_url(url),
                headers=self.headers,
            ),
        )

    async def post(self, url: str, payload: Optional[dict] = None, is_form_data: bool = False, *args, **kwargs):
        if is_form_data:
            return self.__check_response(
                await http_requests.post_form(
                    get_url(url),
                    payload,
                    headers=self.headers,
                ),
            )
        return self.__check_response(
            await http_requests.post(
                get_url(url),
                payload,
                headers=self.headers,
            ),
        )

    async def request(self, url: str, method: str, payload: Optional[dict] = None, *args, **kwargs):
        return self.__check_response(
            await http_requests.request(
                get_url(url),
                method,
                data=payload,
                headers=self.headers,
            )
        )

    async def get_me(self):
        return await self.get(APIConstant.userMeURI)

    async def get_channel(self, channel_id: str):
        return await self.get(APIConstant.channelURI.format(channel_id=channel_id))

    async def get_channel_permissions(self, channel_id: str, user_id: str):
        return await self.get(APIConstant.channelPermissionsURI.format(channel_id=channel_id, user_id=user_id))

    async def get_role_list(self, guild_id: str):
        return await self.get(APIConstant.rolesURI.format(guild_id=guild_id))

    async def set_user_role(self, guild_id: str, user_id: str, role_id: str, channel_id: Optional[str] = None):
        if role_id == '5':
            return await self.request(
                APIConstant.memberRoleURI.format(guild_id=guild_id, user_id=user_id, role_id=role_id),
                'put',
                {'channel_id': channel_id},
            )

        return await self.request(
            APIConstant.memberRoleURI.format(guild_id=guild_id, user_id=user_id, role_id=role_id), 'put'
        )

    async def delete_user_role(self, guild_id: str, user_id: str, role_id: str):
        return await self.request(
            APIConstant.memberRoleURI.format(guild_id=guild_id, user_id=user_id, role_id=role_id), 'delete'
        )

    async def create_role(self, guild_id: str, name: str, color: Optional[int] = None, hoist: int = 0):
        if not color:
            color = 4285110493

        return await self.post(
            APIConstant.rolesURI.format(guild_id=guild_id), {'name': name, 'color': color, 'hoist': hoist}
        )

    async def update_role(self, guild_id: str, role_id: str, name: str, color: Optional[int] = None, hoist: int = 0):
        return await self.request(
            APIConstant.roleURI.format(guild_id=guild_id, role_id=role_id),
            'patch',
            {'name': name, 'color': color, 'hoist': hoist},
        )

    async def delete_role(self, guild_id: str, role_id: str):
        return await self.request(APIConstant.roleURI.format(guild_id=guild_id, role_id=role_id), 'delete')

    async def get_message(self, channel_id: str, message_id: str):
        return await self.get(APIConstant.messageURI.format(channel_id=channel_id, message_id=message_id))

    async def post_message(self, guild_id: str, src_guild_id: str, channel_id: str, req: MessageSendRequest):
        if req.direct:
            if not guild_id or not req.data['msg_id']:
                create_direct = await self.post(
                    APIConstant.userMeDMURI, {'recipient_id': req.user_id, 'source_guild_id': src_guild_id}
                )
                guild_id = create_direct['guild_id']

            api = APIConstant.dmsURI.format(guild_id=guild_id)
        else:
            api = APIConstant.messagesURI.format(channel_id=channel_id)

        complete = None
        retry_times = 0

        while complete is None and retry_times < 3:
            retry_times += 1
            try:
                complete = await self.post(api, req.data, req.upload_image)
            except ResponseException:
                complete = {}

            await asyncio.sleep(0)

        return complete

    @staticmethod
    def __check_response(response_text: Optional[str]) -> Optional[dict]:
        if response_text is None:
            return None

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ResponseException(-1, repr(e)) from e

        if 'code' in data and data['code'] != 200:
            raise ResponseException(**data)

        return data
