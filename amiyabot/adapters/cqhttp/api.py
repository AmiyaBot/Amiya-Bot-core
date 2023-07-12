import hashlib
from typing import Optional
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.network.download import download_async
from .._adapterApi import BotAdapterAPI, BotAdapterType, UserId


class CQHttpAPI(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.CQHTTP)

    async def get_user_avatar(self, user_id: UserId, **kwargs) -> Optional[bytes]:
        """获取用户头像

        Args:
            user_id (UserId): 用户ID

        Returns:
            Optional[bytes]: 头像数据
        """
        url = f'https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640'
        data = await download_async(url)
        if data and hashlib.md5(data).hexdigest() == 'acef72340ac0e914090bd35799f5594e':
            url = f'https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=100'
            data = await download_async(url)
        return data

    async def send_cq_code(self, user_id: str, group_id: str = '', code: str = ''):
        await self.post('/send_msg', {
            'message_type': 'group' if group_id else 'private',
            'user_id': user_id,
            'group_id': group_id,
            'message': code
        })

    async def send_group_forward_msg(self, group_id: str, forward_node: list):
        res = await self.post('/send_group_forward_msg', {
            'group_id': group_id,
            'messages': forward_node
        })
        return res.origin

    async def send_group_notice(self, group_id: str, content: str, **kwargs) -> Optional[bool]:
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
        if res.data and res.data['status'] == 'ok':
            return True
        return False

    async def send_nudge(self, user_id: str, group_id: str):
        await self.send_cq_code(user_id, group_id, f'[CQ:poke,qq={user_id}]')
