import json
import time
import requests

from typing import List, Optional

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

    async def upload_file(
        self,
        openid: str,
        file_type: int,
        url: str,
        srv_send_msg: bool = False,
        is_direct: bool = False,
        file_name: Optional[str] = None,
        upload_id: Optional[str] = None,
    ):
        """
        富媒体上传。
        file_type: 1=图片 2=视频 3=语音 4=文件
        传 upload_id 时走「分片上传合并」路径，此时 url 可为空。
        """
        payload = {
            'file_type': file_type,
            'url': url,
            'srv_send_msg': srv_send_msg,
        }

        if file_name is not None:
            payload['file_name'] = file_name

        if upload_id is not None:
            payload['upload_id'] = upload_id

        return await self.post(
            f'/v2/users/{openid}/files' if is_direct else f'/v2/groups/{openid}/files',
            payload,
        )

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
        """
        分片上传第一步：预上传，返回 upload_id / block_size / 各分片预签名 URL。
        file_size / block_size 官方要求为字符串以避免精度问题。
        https://bot.q.qq.com/wiki/develop/api-v2/server-inter/message/rich-media.html
        """
        return await self.post(
            f'/v2/users/{openid}/upload_prepare' if is_direct else f'/v2/groups/{openid}/upload_prepare',
            {
                'file_type': file_type,
                'file_size': str(file_size),
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
        """分片上传第三步：通知服务端某个分片已完成。"""
        payload = {
            'upload_id': upload_id,
            'part_index': part_index,
            'block_size': str(block_size),
        }

        if md5 is not None:
            payload['md5'] = md5

        return await self.post(
            f'/v2/users/{openid}/upload_part_finish' if is_direct else f'/v2/groups/{openid}/upload_part_finish',
            payload,
        )

    async def post_group_message(self, channel_openid: str, payload: dict):
        return await self.post(f'/v2/groups/{channel_openid}/messages', payload)

    async def post_private_message(self, user_openid: str, payload: dict):
        return await self.post(f'/v2/users/{user_openid}/messages', payload)

    async def delete_group_message(self, group_openid: str, message_id: str):
        """撤回群聊消息，发送超过 2 分钟不可撤回。"""
        return await self.request(f'/v2/groups/{group_openid}/messages/{message_id}', 'delete')

    async def delete_private_message(self, user_openid: str, message_id: str):
        """撤回单聊消息，发送超过 2 分钟不可撤回。"""
        return await self.request(f'/v2/users/{user_openid}/messages/{message_id}', 'delete')

    # ------------------------------------------------------------------
    # 群聊管理
    # ⚠️ 除「入群申请审批」外，以下接口官方标注「该能力正在内邀接入中」，
    #    普通机器人调用会返回 11253（应用无接口访问权限），需向平台申请白名单。
    # https://bot.q.qq.com/wiki/develop/api-v2/autogen/api/
    # ------------------------------------------------------------------

    async def get_group_info(self, group_openid: str):
        """获取群基本信息。"""
        return await self.get(f'/v2/groups/{group_openid}/info')

    async def get_group_bot_state(self, group_openid: str):
        """获取机器人在指定群中的状态信息。"""
        return await self.get(f'/v2/groups/{group_openid}/bot_state')

    async def get_group_members(self, group_openid: str, cursor: str = ''):
        """获取群成员列表，每次最多返回 30 条。"""
        return await self.get(f'/v2/groups/{group_openid}/members', {'cursor': cursor})

    async def get_group_member(self, group_openid: str, member_openid: str):
        """获取群成员信息。"""
        return await self.get(f'/v2/groups/{group_openid}/members/{member_openid}')

    async def batch_remove_group_members(
        self,
        group_openid: str,
        member_openids: List[str],
        add_to_member_blacklist: bool = False,
    ):
        """群成员批量移除，单次最多 20 个。"""
        return await self.post(
            f'/v2/groups/{group_openid}/batch_remove_members',
            {
                'member_openids': member_openids,
                'add_to_member_blacklist': add_to_member_blacklist,
            },
        )

    async def get_group_member_blacklist(self, group_openid: str, cursor: str = '', limit: int = 20):
        """查询群黑名单列表。"""
        return await self.get(
            f'/v2/groups/{group_openid}/member_blacklist',
            {'cursor': cursor, 'limit': limit},
        )

    async def modify_group_member_blacklist(self, group_openid: str, op: str, member_openids: List[str]):
        """
        群黑名单操作。
        op: add 加入黑名单（目标需不在群中）/ del 移出黑名单
        """
        return await self.post(
            f'/v2/groups/{group_openid}/member_blacklist',
            {'op': op, 'member_openids': member_openids},
        )

    async def get_group_restrict_chat_setting(self, group_openid: str):
        """查询群禁言状态（需机器人拥有群管理员身份）。"""
        return await self.get(f'/v2/groups/{group_openid}/restrict_chat_setting')

    async def set_group_member_mute(self, group_openid: str, members: List[dict]):
        """
        设置群成员禁言（需群管理员身份，最长 30 天）。
        members 每项: {'op': 'add'|'update'|'del', 'member_openid': str, 'mute_expire_at': str}
        """
        return await self.post(
            f'/v2/groups/{group_openid}/restrict_chat_setting',
            {'members': members},
        )

    async def get_group_join_request_list(self, group_openid: str, cursor: str = '', limit: int = 20):
        """拉取入群申请列表（需群管理员身份）。"""
        return await self.get(
            f'/v2/groups/{group_openid}/join_request_list',
            {'cursor': cursor, 'limit': limit},
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
        """
        审批入群申请（需群管理员身份）。
        op: approve 通过 / decline 拒绝
        """
        payload = {
            'op': op,
            'add_to_member_blacklist': add_to_member_blacklist,
        }

        if join_request_id is not None:
            payload['join_request_id'] = join_request_id

        if reject_reason is not None:
            payload['reject_reason'] = reject_reason

        return await self.post(f'/v2/groups/{group_openid}/approval_join_request/{member_openid}', payload)

    async def generate_url_link(self, callback_data: Optional[str] = None):
        """生成机器人分享链接。"""
        return await self.post('/v2/generate_url_link', {'callback_data': callback_data})

    async def put_interaction_response(self, interaction_id: str, code: int = 0):
        """
        回应互动事件（按钮回调等）。
        code: 0=成功 1=操作失败 2=操作频繁 3=重复操作 4=没有权限 5=仅管理员操作
        """
        return await self.request(f'/interactions/{interaction_id}', 'put', {'code': code})

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
        """
        流式发送单聊消息（仅单聊）。
        input_state: 1=生成中 10=生成结束；首片响应 id 即后续 stream_msg_id。
        """
        payload = {
            'input_mode': input_mode,
            'input_state': input_state,
            'index': index,
            'content_type': content_type,
            'content_raw': content_raw,
        }

        if stream_msg_id is not None:
            payload['stream_msg_id'] = stream_msg_id
        if msg_id is not None:
            payload['msg_id'] = msg_id
        if event_id is not None:
            payload['event_id'] = event_id
        if msg_seq is not None:
            payload['msg_seq'] = msg_seq

        return await self.post(f'/v2/users/{user_openid}/stream_messages', payload)
