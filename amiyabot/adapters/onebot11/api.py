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

    async def send_private_msg(self, *args, **kwargs):
        ...

    async def send_group_msg(self, *args, **kwargs):
        ...

    async def send_msg(self, *args, **kwargs):
        ...

    async def delete_msg(self, *args, **kwargs):
        ...

    async def get_msg(self, message_id: str):
        return await self.post('/get_msg', data={'message_id': message_id})

    async def get_forward_msg(self, *args, **kwargs):
        ...

    async def send_like(self, *args, **kwargs):
        ...

    async def set_group_kick(self, *args, **kwargs):
        ...

    async def set_group_ban(self, *args, **kwargs):
        ...

    async def set_group_anonymous_ban(self, *args, **kwargs):
        ...

    async def set_group_whole_ban(self, *args, **kwargs):
        ...

    async def set_group_admin(self, *args, **kwargs):
        ...

    async def set_group_anonymous(self, *args, **kwargs):
        ...

    async def set_group_card(self, *args, **kwargs):
        ...

    async def set_group_name(self, *args, **kwargs):
        ...

    async def set_group_leave(self, *args, **kwargs):
        ...

    async def set_group_special_title(self, *args, **kwargs):
        ...

    async def set_friend_add_request(self, *args, **kwargs):
        ...

    async def set_group_add_request(self, *args, **kwargs):
        ...

    async def get_login_info(self, *args, **kwargs):
        ...

    async def get_stranger_info(self, *args, **kwargs):
        ...

    async def get_friend_list(self, *args, **kwargs):
        ...

    async def get_group_info(self, *args, **kwargs):
        ...

    async def get_group_list(self, *args, **kwargs):
        ...

    async def get_group_member_info(self, *args, **kwargs):
        ...

    async def get_group_member_list(self, *args, **kwargs):
        ...

    async def get_group_honor_info(self, *args, **kwargs):
        ...

    async def get_cookies(self, *args, **kwargs):
        ...

    async def get_csrf_token(self, *args, **kwargs):
        ...

    async def get_credentials(self, *args, **kwargs):
        ...

    async def get_record(self, *args, **kwargs):
        ...

    async def get_image(self, *args, **kwargs):
        ...

    async def can_send_image(self, *args, **kwargs):
        ...

    async def can_send_record(self, *args, **kwargs):
        ...

    async def get_status(self, *args, **kwargs):
        ...

    async def get_version_info(self, *args, **kwargs):
        ...

    async def set_restart(self, *args, **kwargs):
        ...

    async def clean_cache(self, *args, **kwargs):
        ...
