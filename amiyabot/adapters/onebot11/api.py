from typing import Optional
from amiyabot.adapters import BotAdapterProtocol
from .._adapterApi import BotAdapterAPI, BotAdapterType, GroupId, UserId


class OneBot11API(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.ONEBOT11)

    async def get_user_avatar(self, user_id: UserId, **kwargs) -> Optional[bytes]:
        return None

    async def send_group_notice(self, group_id: GroupId, content: str, **kwargs) -> Optional[bool]:
        return None

    async def send_nudge(self, user_id: UserId, group_id: GroupId):
        return None

    async def send_private_msg(self, *args, **kwargs):
        ...

    async def send_group_msg(self, *args, **kwargs):
        ...

    async def send_msg(self, *args, **kwargs):
        ...

    async def delete_msg(self, *args, **kwargs):
        ...

    async def get_msg(self, *args, **kwargs):
        ...

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
