import hashlib
import json
import re
from typing import Optional

from amiyabot.log import LoggerManager
from amiyabot.network.download import download_async
from amiyabot.network.httpRequests import http_requests
from amiyabot.adapters import BotAdapterProtocol

from .._adapterApi import BotAdapterAPI, BotAdapterType, UserId
from .payload import HttpAdapter

log = LoggerManager('Mirai')


class MiraiAPI(BotAdapterAPI):
    def __init__(self, instance: BotAdapterProtocol):
        super().__init__(instance, BotAdapterType.MIRAI)

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

    async def upload(self, interface: str, field_type: str, file: bytes, msg_type: str):
        res = await http_requests.post_upload(
            self.url + interface,
            file,
            file_field=field_type,
            payload={'sessionKey': self.session, 'type': msg_type},
        )
        if res:
            return json.loads(res)

    async def upload_image(self, file: bytes, msg_type: str):
        res = await self.upload('/uploadImage', 'img', file, msg_type)
        if res and 'imageId' in res:
            return res['imageId']

    async def upload_voice(self, file: bytes, msg_type: str):
        res = await self.upload('/uploadVoice', 'voice', file, msg_type)
        if res and 'voiceId' in res:
            return res['voiceId']

    async def send_group_message(self, group_id: str, chain_list: list):
        res = await self.post(
            *HttpAdapter.group_message(self.session, group_id, chain_list)
        )
        return res.origin

    async def send_group_notice(self, group_id: str, content: str, **kwargs) -> Optional[bool]:
        """发布群公告

        Args:
            group_id (str): 群号
            content (str): 公告内容

            可选 -
            send_to_new_member (bool): 是否发送给新成员
            pinned (bool): 是否置顶
            show_edit_card (bool): 是否显示修改群名片引导
            show_pop_up (bool): 是否弹窗提示
            require_confirm (bool): 是否需要确认
            image (Union[str, bytes]): 图片链接或图片文件

        Returns:
            bool: 是否成功
        """
        data = {'target': group_id, 'content': content}
        if kwargs.get('image'):
            image = kwargs['image']
            if isinstance(image, str):
                regex = re.compile(
                    r'^(?:http|ftp)s?://'  # http:// or https://
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                    r'localhost|'  # localhost...
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                    r'(?::\d+)?'  # optional port
                    r'(?:/?|[/?]\S+)$',
                    re.IGNORECASE,
                )
                if re.match(regex, image):
                    data['imageUrl'] = image
                else:
                    data['imagePath'] = image
            elif isinstance(image, bytes):
                data['imageBase64'] = image
        if kwargs.get('send_to_new_member'):
            data['sendToNewMember'] = kwargs['send_to_new_member']
        if kwargs.get('pinned'):
            data['pinned'] = kwargs['pinned']
        if kwargs.get('show_edit_card'):
            data['showEditCard'] = kwargs['show_edit_card']
        if kwargs.get('show_pop_up'):
            data['showPopup'] = kwargs['show_pop_up']
        if kwargs.get('require_confirm'):
            data['requireConfirmation'] = kwargs['require_confirm']
        res = await self.post('/anno/publish', data)
        if res.data and res.data.get('code') == 0:
            return True
        return False

    async def send_nudge(self, user_id: str, group_id: str):
        await self.post(*HttpAdapter.nudge(self.session, user_id, group_id))
