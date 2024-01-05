import json
import asyncio

from typing import Optional, List
from dataclasses import dataclass
from amiyabot.network.httpRequests import http_requests
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol
from amiyabot.log import LoggerManager

log = LoggerManager('Tencent')


@dataclass
class MessageSendRequest:
    data: dict
    direct: bool
    user_id: str
    upload_image: bool = False


class QQGuildAPI(BotInstanceAPIProtocol):
    def __init__(self, appid: str, token: str, sandbox: bool = False, post_message_max_retry_times: int = 3):
        self.appid = appid
        self.token = token
        self.sandbox = sandbox
        self.post_message_max_retry_times = post_message_max_retry_times

    @property
    def headers(self):
        return {'Authorization': f'Bot {self.appid}.{self.token}'}

    @property
    def domain(self):
        return 'https://sandbox.api.sgroup.qq.com' if self.sandbox else 'https://api.sgroup.qq.com'

    async def get(self, url: str, params: Optional[dict] = None, *args, **kwargs):
        return await http_requests.get(
            self.domain + url,
            params,
            headers=self.headers,
        )

    async def post(self, url: str, payload: Optional[dict] = None, is_form_data: bool = False, *args, **kwargs):
        if is_form_data:
            return await http_requests.post_form(
                self.domain + url,
                payload,
                headers=self.headers,
            )

        return await http_requests.post(
            self.domain + url,
            payload,
            headers=self.headers,
        )

    async def request(self, url: str, method: str, payload: Optional[dict] = None, *args, **kwargs):
        return await http_requests.request(
            self.domain + url,
            method,
            data=payload,
            headers=self.headers,
        )

    async def gateway(self):
        return await self.get('/gateway')

    async def gateway_bot(self):
        return await self.get('/gateway/bot')

    async def get_me(self):
        return await self.get('/users/@me')

    async def get_me_dms(self, recipient_id: str, src_guild_id: str):
        return await self.post('/users/@me/dms', {'recipient_id': recipient_id, 'source_guild_id': src_guild_id})

    async def get_guilds(self, before: Optional[str] = None, after: Optional[str] = None, limit: int = 100):
        params = {'limit': limit}
        if before:
            params['before'] = before
        if after:
            params['after'] = after

        return await self.get('/users/@me/guilds', params)

    async def get_guild(self, guild_id: str):
        return await self.get(f'/guilds/{guild_id}')

    async def get_channels(self, guild_id: str):
        return await self.get(f'/guilds/{guild_id}/channels')

    async def get_channel(self, channel_id: str):
        return await self.get(f'/channels/{channel_id}')

    async def create_channel(
        self,
        guild_id: str,
        channel_name: str,
        channel_type: int,
        channel_sub_type: int,
        position: Optional[int] = None,
        parent_id: Optional[str] = None,
        private_type: Optional[int] = None,
        private_user_ids: Optional[List[str]] = None,
        speak_permission: Optional[int] = None,
        application_id: Optional[str] = None,
    ):
        return await self.post(
            f'/guilds/{guild_id}/channels',
            {
                'name': channel_name,
                'type': channel_type,
                'sub_type': channel_sub_type,
                'position': position,
                'parent_id': parent_id,
                'private_type': private_type,
                'private_user_ids': private_user_ids,
                'speak_permission': speak_permission,
                'application_id': application_id,
            },
        )

    async def modify_channel(
        self,
        channel_id: str,
        channel_name: str,
        position: Optional[int] = None,
        parent_id: Optional[str] = None,
        private_type: Optional[int] = None,
        speak_permission: Optional[int] = None,
    ):
        return await self.request(
            f'/channels/{channel_id}',
            'patch',
            {
                'name': channel_name,
                'position': position,
                'parent_id': parent_id,
                'private_type': private_type,
                'speak_permission': speak_permission,
            },
        )

    async def delete_channel(self, channel_id: str):
        return await self.request(f'/channels/{channel_id}', 'delete')

    async def get_channel_online_nums(self, channel_id: str):
        return await self.get(f'/channels/{channel_id}/online_nums')

    async def get_guild_members(
        self,
        guild_id: str,
        after: str = '0',
        limit: int = 1,
    ):
        return await self.get(f'/guilds/{guild_id}/members', {'after': after, 'limit': limit})

    async def get_guild_member(self, guild_id: str, user_id: str):
        return await self.get(f'/guilds/{guild_id}/members/{user_id}')

    async def delete_guild_member(
        self,
        guild_id: str,
        user_id: str,
        add_blacklist: bool = False,
        delete_history_msg_days: int = 0,
    ):
        return await self.request(
            f'/guilds/{guild_id}/members/{user_id}',
            'delete',
            {
                'add_blacklist': add_blacklist,
                'delete_history_msg_days': delete_history_msg_days,
            },
        )

    async def get_guild_roles_members(
        self,
        guild_id: str,
        role_id: str,
        start_index: str = '0',
        limit: int = 1,
    ):
        return await self.get(
            f'/guilds/{guild_id}/roles/{role_id}/members', {'start_index': start_index, 'limit': limit}
        )

    async def get_guild_roles(self, guild_id: str):
        return await self.get(f'/guilds/{guild_id}/roles')

    async def create_guild_role(
        self,
        guild_id: str,
        name: Optional[str] = None,
        color: Optional[int] = None,
        hoist: int = 0,
    ):
        return await self.post(
            f'/guilds/{guild_id}/roles',
            {
                'name': name,
                'color': color,
                'hoist': hoist,
            },
        )

    async def modify_guild_role(
        self,
        guild_id: str,
        role_id: str,
        name: Optional[str] = None,
        color: Optional[int] = None,
        hoist: int = 0,
    ):
        return await self.request(
            f'/guilds/{guild_id}/roles/{role_id}',
            'patch',
            {
                'name': name,
                'color': color,
                'hoist': hoist,
            },
        )

    async def delete_guild_role(self, guild_id: str, role_id: str):
        return await self.request(f'/guilds/{guild_id}/roles/{role_id}', 'delete')

    async def set_user_role(
        self,
        guild_id: str,
        user_id: str,
        role_id: str,
        channel_id: Optional[str] = None,
    ):
        return await self.request(
            f'/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
            'put',
            {'channel_id': channel_id} if role_id == '5' else None,
        )

    async def delete_user_role(self, guild_id: str, user_id: str, role_id: str):
        return await self.request(f'/guilds/{guild_id}/members/{user_id}/roles/{role_id}', 'delete')

    async def get_user_permission(self, channel_id: str, user_id: str):
        return await self.get(f'/channels/{channel_id}/members/{user_id}/permissions')

    async def set_user_permission(
        self,
        channel_id: str,
        user_id: str,
        add: Optional[str] = None,
        remove: Optional[str] = None,
    ):
        return await self.request(
            f'/channels/{channel_id}/members/{user_id}/permissions',
            'put',
            {
                'add': add,
                'remove': remove,
            },
        )

    async def get_role_permission(self, channel_id: str, role_id: str):
        return await self.get(f'/channels/{channel_id}/members/{role_id}/permissions')

    async def set_role_permission(
        self,
        channel_id: str,
        role_id: str,
        add: Optional[str] = None,
        remove: Optional[str] = None,
    ):
        return await self.request(
            f'/channels/{channel_id}/members/{role_id}/permissions',
            'put',
            {
                'add': add,
                'remove': remove,
            },
        )

    async def get_message(self, channel_id: str, message_id: str):
        return await self.get(f'/channels/{channel_id}/messages/{message_id}')

    async def post_message(self, guild_id: str, src_guild_id: str, channel_id: str, req: MessageSendRequest):
        if req.direct:
            if not guild_id or not req.data['msg_id']:
                create_direct = await self.get_me_dms(req.user_id, src_guild_id)
                guild_id = create_direct.json['guild_id']

            api = f'/dms/{guild_id}/messages'
        else:
            api = f'/channels/{channel_id}/messages'

        retry_times = 0
        while retry_times < self.post_message_max_retry_times:
            retry_times += 1

            res = await self.post(api, req.data, req.upload_image)
            if res:
                if 'code' in res.json and res.json['code'] not in http_requests.success + http_requests.async_success:
                    log.error(res.json['message'], 'message send error by code: %s --' % res.json['code'])
                else:
                    return res

            await asyncio.sleep(0)

    async def delete_message(self, message_id: str, target_id: str, is_direct: bool, hidetip: bool = True):
        if is_direct:
            return await self.request(
                f'/dms/{target_id}/messages/{message_id}?hidetip={json.dumps(hidetip)}',
                'delete',
            )
        return await self.request(
            f'/channels/{target_id}/messages/{message_id}?hidetip={json.dumps(hidetip)}',
            'delete',
        )

    async def get_message_setting(self, guild_id: str):
        return await self.get(f'/guilds/{guild_id}/message/setting')

    async def mute_all(self, guild_id: str, mute_end_timestamp: str, mute_seconds: str):
        return await self.request(
            f'/guilds/{guild_id}/mute',
            'patch',
            {
                'mute_end_timestamp': mute_end_timestamp,
                'mute_seconds': mute_seconds,
            },
        )

    async def mute_all_lift(self, guild_id: str):
        return await self.mute_all(guild_id, '0', '0')

    async def mute_users(self, guild_id: str, user_ids: List[str], mute_end_timestamp: str, mute_seconds: str):
        return await self.request(
            f'/guilds/{guild_id}/mute',
            'patch',
            {
                'mute_end_timestamp': mute_end_timestamp,
                'mute_seconds': mute_seconds,
                'user_ids': user_ids,
            },
        )

    async def mute_users_lift(self, guild_id: str, user_ids: List[str]):
        return await self.mute_users(guild_id, user_ids, '0', '0')

    async def mute_user(self, guild_id: str, user_id: str, mute_end_timestamp: str, mute_seconds: str):
        return await self.request(
            f'/guilds/{guild_id}/members/{user_id}/mute',
            'patch',
            {
                'mute_end_timestamp': mute_end_timestamp,
                'mute_seconds': mute_seconds,
            },
        )

    async def mute_user_lift(self, guild_id: str, user_id: str):
        return await self.mute_user(guild_id, user_id, '0', '0')

    async def create_announces(
        self,
        guild_id: str,
        message_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        announces_type: Optional[int] = None,
        recommend_channels: Optional[str] = None,
    ):
        return await self.post(
            f'/guilds/{guild_id}/announces',
            {
                'message_id': message_id,
                'channel_id': channel_id,
                'announces_type': announces_type,
                'recommend_channels': recommend_channels,
            },
        )

    async def delete_announces(self, guild_id: str, message_id: Optional[str] = None):
        return await self.request(f'/guilds/{guild_id}/announces/{message_id}', 'delete')

    async def get_pins(self, channel_id: str):
        return await self.get(f'/channels/{channel_id}/pins')

    async def add_pin(self, channel_id: str, message_id: str):
        return await self.request(f'/channels/{channel_id}/pins/{message_id}', 'put')

    async def delete_pin(self, channel_id: str, message_id: str):
        return await self.request(f'/channels/{channel_id}/pins/{message_id}', 'delete')

    async def get_schedules(self, channel_id: str, since: int = 0):
        return await self.get(f'/channels/{channel_id}/schedules', {'since': since})

    async def get_schedule(self, channel_id: str, schedule_id: str):
        return await self.get(f'/channels/{channel_id}/schedules/{schedule_id}')

    async def create_schedule(
        self,
        channel_id: str,
        name: str,
        description: str,
        start_timestamp: str,
        end_timestamp: str,
        creator: Optional[dict] = None,
        jump_channel_id: Optional[str] = None,
        remind_type: Optional[str] = None,
    ):
        return await self.post(
            f'/channels/{channel_id}/schedules',
            {
                'schedule': {
                    'name': name,
                    'description': description,
                    'start_timestamp': start_timestamp,
                    'end_timestamp': end_timestamp,
                    'creator': creator,
                    'jump_channel_id': jump_channel_id,
                    'remind_type': remind_type,
                }
            },
        )

    async def modify_schedule(
        self,
        channel_id: str,
        schedule_id: str,
        name: str,
        description: str,
        start_timestamp: str,
        end_timestamp: str,
        creator: Optional[dict] = None,
        jump_channel_id: Optional[str] = None,
        remind_type: Optional[str] = None,
    ):
        return await self.request(
            f'/channels/{channel_id}/schedules/{schedule_id}',
            'patch',
            {
                'schedule': {
                    'name': name,
                    'description': description,
                    'start_timestamp': start_timestamp,
                    'end_timestamp': end_timestamp,
                    'creator': creator,
                    'jump_channel_id': jump_channel_id,
                    'remind_type': remind_type,
                }
            },
        )

    async def delete_schedule(self, channel_id: str, schedule_id: str):
        return await self.request(f'/channels/{channel_id}/schedules/{schedule_id}', 'delete')

    async def get_message_reactions(
        self,
        channel_id: str,
        message_id: str,
        emoji_type: int,
        emoji_id: str,
        cookie: Optional[str] = '',
        limit: int = 20,
    ):
        return await self.get(
            f'/channels/{channel_id}/messages/{message_id}/reactions/{emoji_type}/{emoji_id}',
            {
                'cookie': cookie,
                'limit': limit,
            },
        )

    async def add_message_reaction(self, channel_id: str, message_id: str, emoji_type: int, emoji_id: str):
        return await self.request(
            f'/channels/{channel_id}/messages/{message_id}/reactions/{emoji_type}/{emoji_id}',
            'put',
        )

    async def delete_message_reaction(self, channel_id: str, message_id: str, emoji_type: int, emoji_id: str):
        return await self.request(
            f'/channels/{channel_id}/messages/{message_id}/reactions/{emoji_type}/{emoji_id}',
            'delete',
        )

    async def get_threads(self, channel_id: str):
        return await self.get(f'/channels/{channel_id}/threads')

    async def get_thread(self, channel_id: str, thread_id: str):
        return await self.get(f'/channels/{channel_id}/threads/{thread_id}')

    async def create_thread(self, channel_id: str, title: str, content: str, thread_format: int = 1):
        return await self.request(
            f'/channels/{channel_id}/threads',
            'put',
            {
                'title': title,
                'content': content,
                'format': thread_format,
            },
        )

    async def delete_thread(self, channel_id: str, thread_id: str):
        return await self.request(f'/channels/{channel_id}/threads/{thread_id}', 'delete')

    async def get_guild_api_permission(self, guild_id: str):
        return await self.get(f'/guilds/{guild_id}/api_permission')

    async def create_guild_api_permission_link(
        self,
        guild_id: str,
        channel_id: str,
        path: str,
        method: str,
        desc: str,
    ):
        return await self.post(
            f'/guilds/{guild_id}/api_permission/demand',
            {
                'channel_id': channel_id,
                'api_identify': {
                    'path': path,
                    'method': method,
                },
                'desc': desc,
            },
        )
