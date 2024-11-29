from typing import Optional
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol
from amiyabot.network.httpRequests import http_requests


class OneBot11API(BotInstanceAPIProtocol):
    def __init__(self, host: str, port: int, token: str):
        self.token = token
        self.host = f'http://{host}:{port}'

    @property
    def headers(self):
        return {'Authorization': self.token}

    async def get(self, url: str, params: Optional[dict] = None, *args, **kwargs):
        return await http_requests.get(
            self.host + url,
            params,
            headers=self.headers,
            **kwargs,
        )

    async def post(self, url: str, data: Optional[dict] = None, *args, **kwargs):
        return await http_requests.post(
            self.host + url,
            data,
            headers=self.headers,
            **kwargs,
        )

    async def request(self, url: str, method: str, *args, **kwargs):
        return await http_requests.request(
            self.host + url,
            method,
            headers=self.headers,
            **kwargs,
        )

    async def send_private_msg(self, user_id: int, message: str, auto_escape: bool = False):
        return await self.post(
            '/send_private_msg',
            data={
                'user_id': user_id,
                'message': message,
                'auto_escape': auto_escape,
            },
        )

    async def send_group_msg(self, group_id: int, message: str, auto_escape: bool = False):
        return await self.post(
            '/send_group_msg',
            data={
                'group_id': group_id,
                'message': message,
                'auto_escape': auto_escape,
            },
        )

    async def send_msg(self, message_type: str, user_id: int, group_id: int, message: str, auto_escape: bool = False):
        return await self.post(
            '/send_msg',
            data={
                'message_type': message_type,
                'user_id': user_id,
                'group_id': group_id,
                'message': message,
                'auto_escape': auto_escape,
            },
        )

    async def delete_msg(self, message_id: str):
        return await self.post('/delete_msg', data={'message_id': message_id})

    async def get_msg(self, message_id: str):
        return await self.post('/get_msg', data={'message_id': message_id})

    async def get_forward_msg(self, msg_id: str):
        return await self.post('/get_forward_msg', data={'id': msg_id})

    async def send_like(self, user_id: int, times: int):
        return await self.post('/send_like', data={'user_id': user_id, 'times': times})

    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False):
        return await self.post(
            '/set_group_kick', data={'group_id': group_id, 'user_id': user_id, 'reject_add_request': reject_add_request}
        )

    async def set_group_ban(self, group_id: int, user_id: int, duration: int):
        return await self.post('/set_group_ban', data={'group_id': group_id, 'user_id': user_id, 'duration': duration})

    # async def set_group_anonymous_ban(self, *args, **kwargs):
    # ...

    async def set_group_whole_ban(self, group_id: int, enable: bool = True):
        return await self.post('/set_group_whole_ban', data={'group_id': group_id, 'enable': enable})

    async def set_group_admin(self, group_id: int, user_id: int, enable: bool = True):
        return await self.post('/set_group_admin', data={'group_id': group_id, 'user_id': user_id, 'enable': enable})

    # async def set_group_anonymous(self, *args, **kwargs):
    # ...

    async def set_group_card(self, group_id: int, user_id: int, card: str = ""):
        return await self.post('/set_group_card', data={'group_id': group_id, 'user_id': user_id, 'card': card})

    async def set_group_name(self, group_id: int, group_name: str):
        return await self.post('/set_group_name', data={'group_id': group_id, 'group_name': group_name})

    async def set_group_leave(self, group_id: int, is_dismiss: bool = False):
        return await self.post('/set_group_leave', data={'group_id': group_id, 'is_dismiss': is_dismiss})

    # async def set_group_special_title(self, *args, **kwargs):
    # ...

    async def set_friend_add_request(self, flag: str, approve: bool = True, remark: str = ""):
        return await self.post(
            '/set_friend_add_request',
            data={
                'flag': flag,
                'approve': approve,
                'remark': remark,
            },
        )

    async def set_group_add_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = ""):
        return await self.post(
            '/set_group_add_request',
            data={
                'flag': flag,
                'sub_type': sub_type,
                'approve': approve,
                'reason': reason,
            },
        )

    async def get_login_info(self):
        return await self.post('/get_login_info')

    async def get_stranger_info(self, user_id: int, no_cache: bool = False):
        return await self.post('/get_stranger_info', data={'user_id': user_id, 'no_cache': no_cache})

    async def get_friend_list(self):
        return await self.post('/get_friend_list')

    async def get_group_info(self, group_id: int, no_cache: bool = False):
        return await self.post('/get_group_info', data={'group_id': group_id, 'no_cache': no_cache})

    async def get_group_list(self):
        return await self.post('/get_group_list')

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = False):
        return await self.post(
            '/get_group_member_info',
            data={
                'group_id': group_id,
                'user_id': user_id,
                'no_cache': no_cache,
            },
        )

    async def get_group_member_list(self, group_id: int):
        return await self.post('/get_group_member_list', data={'group_id': group_id})

    async def get_group_honor_info(self, group_id: int, info_type: str):
        return await self.post('/get_group_honor_info', data={'group_id': group_id, 'type': info_type})

    async def get_cookies(self, domain: str):
        return await self.post('/get_cookies', data={'domain': domain})

    async def get_csrf_token(self):
        return await self.post('/get_csrf_token')

    async def get_credentials(self, domain: str):
        return await self.post('/get_credentials', data={'domain': domain})

    async def get_record(self, file: str, out_format: str):
        return await self.post('/get_record', data={'file': file, 'out_format': out_format})

    async def get_image(self, file: str):
        return await self.post('/get_image', data={'file': file})

    async def can_send_image(self):
        return await self.post('/can_send_image')

    async def can_send_record(self):
        return await self.post('/can_send_record')

    async def get_status(self):
        return await self.post('/get_status')

    async def get_version_info(self):
        return await self.post('/get_version_info')

    async def set_restart(self, delay: int = 0):
        return await self.post('/set_restart', data={'delay': delay})

    async def clean_cache(self):
        return await self.post('/clean_cache')
