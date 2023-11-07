from typing import Optional

from amiyabot.adapters.onebot.v11.api import OneBot11API
from amiyabot.adapters.mirai.api import MiraiAPI


class CQHttpAPI(OneBot11API):
    get_user_avatar = MiraiAPI.get_user_avatar

    async def send_cq_code(self, user_id: str, group_id: str = '', code: str = ''):
        await self.post(
            '/send_msg',
            {
                'message_type': 'group' if group_id else 'private',
                'user_id': user_id,
                'group_id': group_id,
                'message': code,
            },
        )

    async def send_group_forward_msg(self, group_id: str, forward_node: list):
        return await self.post('/send_group_forward_msg', {'group_id': group_id, 'messages': forward_node})

    async def send_group_notice(self, group_id: str, content: str, image: Optional[str] = None):
        data = {'group_id': group_id, 'content': content}
        if image:
            data['image'] = image

        return await self.post('/set_group_notice', data)

    async def send_nudge(self, user_id: str, group_id: str):
        await self.send_cq_code(user_id, group_id, f'[CQ:poke,qq={user_id}]')
