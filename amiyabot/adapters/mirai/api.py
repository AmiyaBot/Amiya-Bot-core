import re
import json
import hashlib

from typing import Optional, Union
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol
from amiyabot.network.download import download_async
from amiyabot.network.httpRequests import http_requests

from .payload import HttpAdapter


class MiraiAPI(BotInstanceAPIProtocol):
    def __init__(self, host: str, port: int, session: str):
        self.session = session
        self.host = f'http://{host}:{port}'

    async def get(self, url: str, params: Optional[dict] = None, *args, **kwargs):
        return await http_requests.get(
            self.host + url,
            params,
            **kwargs,
        )

    async def post(self, url: str, data: Optional[dict] = None, *args, **kwargs):
        return await http_requests.post(
            self.host + url,
            {
                'sessionKey': self.session,
                **data,
            },
            **kwargs,
        )

    async def request(self, url: str, method: str, *args, **kwargs):
        return await http_requests.request(
            self.host + url,
            method,
            **kwargs,
        )

    async def get_user_avatar(self, user_id: str, *args, **kwargs) -> Optional[str]:
        url = f'https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640'
        data = await download_async(url)
        if data and hashlib.md5(data).hexdigest() == 'acef72340ac0e914090bd35799f5594e':
            url = f'https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=100'

        return url

    async def upload(self, interface: str, field_type: str, file: bytes, msg_type: str):
        res = await http_requests.post_upload(
            self.host + interface,
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
        return await self.post(*HttpAdapter.group_message(self.session, group_id, chain_list))

    async def send_group_notice(
        self,
        group_id: str,
        content: str,
        send_to_new_member: Optional[bool] = None,
        pinned: Optional[bool] = None,
        show_edit_card: Optional[bool] = None,
        show_pop_up: Optional[bool] = None,
        require_confirm: Optional[bool] = None,
        image: Optional[Union[str, bytes]] = None,
    ) -> Optional[bool]:
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
        if image is not None:
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
        if send_to_new_member is not None:
            data['sendToNewMember'] = send_to_new_member
        if pinned is not None:
            data['pinned'] = pinned
        if show_edit_card is not None:
            data['showEditCard'] = show_edit_card
        if show_pop_up is not None:
            data['showPopup'] = show_pop_up
        if require_confirm is not None:
            data['requireConfirmation'] = require_confirm

        return await self.post('/anno/publish', data)

    async def send_nudge(self, user_id: str, group_id: str):
        await self.post(*HttpAdapter.nudge(self.session, user_id, group_id))
