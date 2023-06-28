import json
from amiyabot.adapters import BotAdapterProtocol
from .._adapterApi import BotAdapterAPI, BotAdapterType


class CQHttpAPI(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.CQHTTP)

    async def send_cq_code(self, user_id: str, group_id: str = '', code: str = ''):
        await self.post('/send_msg', {
            'message_type': 'group' if group_id else 'private',
            'user_id': user_id,
            'group_id': group_id,
            'message': code
        })

    async def send_group_forward_msg(self, group_id: str, forward_node: list):
        return await self.post('/send_group_forward_msg', {
            'group_id': group_id,
            'messages': forward_node
        })

    async def send_group_notice(self, group_id: str, content: str, **kwargs) -> bool:
        """发布群公告

        Args:
            group_id (str): 群号
            content (str): 公告内容

            可选 -
            image (str): 图片链接

        Returns:
            bool: 是否成功
        """
        data = {'group_id': group_id, 'content': content}
        if kwargs.get('image'):
            data['image'] = kwargs['image']
        res = await self.post('/set_group_notice', data)
        result = json.loads(res)
        if result['status'] == 'ok':
            return True
        return False

    async def send_nudge(self, user_id: str, group_id: str):
        await self.send_cq_code(user_id, group_id, f'[CQ:poke,qq={user_id}]')
