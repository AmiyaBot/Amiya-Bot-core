import json
import time
import requests

from typing import Optional, List
from ..qqGuild.api import QQGuildAPI, log


class QQGroupAPI(QQGuildAPI):
    def __init__(self, appid: str, token: str, client_secret: str):
        super().__init__(appid, token)

        self.appid = appid
        self.client_secret = client_secret
        self.access_token = ''
        self.expires_time = 0

    @property
    def headers(self):
        if not self.access_token or self.expires_time - time.time() <= 60:
            try:
                res = requests.post(
                    url='https://bots.qq.com/app/getAppAccessToken',
                    data=json.dumps(
                        {
                            'appId': self.appid,
                            'clientSecret': self.client_secret,
                        }
                    ),
                    headers={
                        'Content-Type': 'application/json',
                    },
                    timeout=3,
                )
                data = json.loads(res.text)

                self.access_token = data['access_token']
                self.expires_time = int(time.time()) + int(data['expires_in'])

            except Exception as e:
                log.error(e, desc='accessToken requests error:')

        return {
            'Authorization': f'QQBot {self.access_token}',
            'X-Union-Appid': f'{self.appid}',
        }

    @property
    def domain(self):
        return 'https://api.sgroup.qq.com'

    # ============================== 消息 ==============================

    async def post_group_message(self, group_openid: str, payload: dict):
        return await self.post(f'/v2/groups/{group_openid}/messages', payload)

    async def post_private_message(self, user_openid: str, payload: dict):
        return await self.post(f'/v2/users/{user_openid}/messages', payload)

    async def delete_group_message(self, group_openid: str, message_id: str):
        return await self.request(f'/v2/groups/{group_openid}/messages/{message_id}', 'delete')

    async def delete_private_message(self, user_openid: str, message_id: str):
        return await self.request(f'/v2/users/{user_openid}/messages/{message_id}', 'delete')

    async def post_stream_message(
        self,
        user_openid: str,
        content_raw: str,
        index: int = 0,
        input_state: int = 1,
        input_mode: str = 'replace',
        content_type: str = 'markdown',
        stream_msg_id: Optional[str] = None,
        msg_id: Optional[str] = None,
        event_id: Optional[str] = None,
        msg_seq: Optional[int] = None,
    ):
        payload = {
            'content_raw': content_raw,
            'index': index,
            'input_state': input_state,
            'input_mode': input_mode,
            'content_type': content_type,
        }
        if stream_msg_id:
            payload['stream_msg_id'] = stream_msg_id
        if msg_id:
            payload['msg_id'] = msg_id
        if event_id:
            payload['event_id'] = event_id
        if msg_seq is not None:
            payload['msg_seq'] = msg_seq

        return await self.post(f'/v2/users/{user_openid}/stream_messages', payload)

    # ============================== 富媒体 ==============================

    async def upload_file(
        self,
        openid: str,
        file_type: int,
        url: str = '',
        srv_send_msg: bool = False,
        is_direct: bool = False,
        file_name: Optional[str] = None,
        upload_id: Optional[str] = None,
    ):
        payload = {
            'file_type': file_type,
            'url': url,
            'srv_send_msg': srv_send_msg,
        }
        if file_name:
            payload['file_name'] = file_name
        if upload_id:
            payload['upload_id'] = upload_id

        return await self.post(f'/v2/users/{openid}/files' if is_direct else f'/v2/groups/{openid}/files', payload)

    async def upload_prepare(
        self,
        openid: str,
        file_type: int,
        file_size: int,
        file_name: str,
        md5: str,
        sha1: str,
        md5_10m: str,
        is_direct: bool = False,
    ):
        return await self.post(
            f'/v2/users/{openid}/upload_prepare' if is_direct else f'/v2/groups/{openid}/upload_prepare',
            {
                'file_type': file_type,
                'file_size': file_size,
                'file_name': file_name,
                'md5': md5,
                'sha1': sha1,
                'md5_10m': md5_10m,
            },
        )

    async def upload_part_finish(
        self,
        openid: str,
        upload_id: str,
        part_index: int,
        block_size: int = 0,
        md5: Optional[str] = None,
        is_direct: bool = False,
    ):
        payload = {
            'upload_id': upload_id,
            'part_index': part_index,
            'block_size': block_size,
        }
        if md5:
            payload['md5'] = md5

        return await self.post(
            f'/v2/users/{openid}/upload_part_finish' if is_direct else f'/v2/groups/{openid}/upload_part_finish',
            payload,
        )

    # ============================== 群管理 ==============================

    async def get_group_info(self, group_openid: str):
        return await self.get(f'/v2/groups/{group_openid}/info')

    async def get_group_bot_state(self, group_openid: str):
        return await self.get(f'/v2/groups/{group_openid}/bot_state')

    async def get_group_members(self, group_openid: str, cursor: str = ''):
        return await self.get(f'/v2/groups/{group_openid}/members', {'cursor': cursor})

    async def get_group_member(self, group_openid: str, member_openid: str):
        return await self.get(f'/v2/groups/{group_openid}/members/{member_openid}')

    async def batch_remove_group_members(
        self,
        group_openid: str,
        member_openids: List[str],
        add_to_member_blacklist: bool = False,
    ):
        return await self.post(
            f'/v2/groups/{group_openid}/batch_remove_members',
            {
                'member_openids': member_openids,
                'add_to_member_blacklist': add_to_member_blacklist,
            },
        )

    async def get_group_member_blacklist(self, group_openid: str, cursor: str = '', limit: int = 20):
        return await self.get(
            f'/v2/groups/{group_openid}/member_blacklist',
            {
                'cursor': cursor,
                'limit': limit,
            },
        )

    async def modify_group_member_blacklist(self, group_openid: str, op: str, member_openids: List[str]):
        return await self.post(
            f'/v2/groups/{group_openid}/member_blacklist',
            {
                'op': op,
                'member_openids': member_openids,
            },
        )

    async def get_group_restrict_chat_setting(self, group_openid: str):
        return await self.get(f'/v2/groups/{group_openid}/restrict_chat_setting')

    async def set_group_member_mute(self, group_openid: str, members: List[dict]):
        return await self.post(f'/v2/groups/{group_openid}/restrict_chat_setting', {'members': members})

    async def get_group_join_request_list(self, group_openid: str, cursor: str = '', limit: int = 20):
        return await self.get(
            f'/v2/groups/{group_openid}/join_request/list',
            {
                'cursor': cursor,
                'limit': limit,
            },
        )

    async def approval_group_join_request(
        self,
        group_openid: str,
        member_openid: str,
        op: str,
        join_request_id: Optional[str] = None,
        reject_reason: Optional[str] = None,
        add_to_member_blacklist: bool = False,
    ):
        payload = {
            'op': op,
            'add_to_member_blacklist': add_to_member_blacklist,
        }
        if join_request_id:
            payload['join_request_id'] = join_request_id
        if reject_reason:
            payload['reject_reason'] = reject_reason

        return await self.post(f'/v2/groups/{group_openid}/approval_join_request/{member_openid}', payload)

    # ============================== 互动与其他 ==============================

    async def put_interaction_response(self, interaction_id: str, code: int = 0):
        return await self.request(f'/interactions/{interaction_id}', 'put', {'code': code})

    async def generate_url_link(self, callback_data: Optional[str] = None):
        return await self.post('/v2/generate_url_link', {'callback_data': callback_data})
