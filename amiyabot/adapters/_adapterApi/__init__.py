import abc
import json

from typing import Dict, Optional, Union

from amiyabot.adapters import BotAdapterProtocol, PACKAGE_RESULT
from amiyabot.network.httpRequests import http_requests

from .define import *


def get_json_result(res: Optional[str]) -> dict:
    """获取 JSON 结果

    Args:
        res (str): HTTP 响应

    Returns:
        dict: JSON 结果
    """
    return json.loads(res)


class BotAdapterAPI:
    def __init__(self, instance: BotAdapterProtocol, adapter_type: BotAdapterType):
        self.instance = instance
        self.adapter_type = adapter_type
        self.token = instance.token
        self.url = f'http://{instance.host}:{instance.http_port}'

    @property
    def session(self) -> str:
        if self.adapter_type == BotAdapterType.MIRAI:
            return self.instance.session
        return ''

    async def get(self, path: str, params: Dict = {}, **kwargs):
        """GET 请求

        Args:
            path (str): 接口路径
            params (dict, optional): 请求参数. 默认为 None.
            **kwargs: 其他参数

        Returns:
            HTTPResponse: HTTP 响应
        """
        if not path.startswith('/'):
            path = '/' + path

        if self.adapter_type == BotAdapterType.CQHTTP:
            return await http_requests.get(
                self.url + path,
                params=params,
                headers={'Authorization': self.token},
                **kwargs,
            )

        if self.adapter_type == BotAdapterType.MIRAI:
            params['sessionKey'] = self.session
            return await http_requests.get(self.url + path, params=params, **kwargs)

    async def post(
        self, path: str, params: dict = None, headers: dict = None, **kwargs
    ):
        """POST 请求

        Args:
            path (str): 接口路径
            params (dict, optional): 请求参数. 默认为 None
            headers (dict, optional): 请求头. 默认为 {}
            **kwargs: 其他参数

        Returns:
            HTTPResponse: HTTP 响应
        """
        if not path.startswith('/'):
            path = '/' + path

        if self.adapter_type == BotAdapterType.CQHTTP:
            if headers:
                headers.update({'Authorization': self.token})
            else:
                headers = {'Authorization': self.token}
            return await http_requests.post(self.url + path, params, headers, **kwargs)

        if self.adapter_type == BotAdapterType.MIRAI:
            params['sessionKey'] = self.session
            return await http_requests.post(self.url + path, params, headers, **kwargs)

    # 缓存操作

    async def get_message(
        self, message_id: MessageId, target: Optional[Union[UserId, GroupId]] = None
    ) -> Optional[PACKAGE_RESULT]:
        """通过消息 ID 获取消息

        Args:
            message_id (int): 消息 ID - all: required
            target: 好友id或群id - mirai: required
        Returns:
            Optional[PACKAGE_RESULT]: 消息 - all: have
        """
        if not message_id:
            return None

        message_id = int(message_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/get_msg', {'message_id': message_id})
            result = json.loads(res)
            if result['status'] == 'ok':
                return await self.instance.package_message('', result['data'])

        if self.adapter_type == BotAdapterType.MIRAI:
            if not target:
                return None

            target = int(target)
            res = await self.get(
                '/messageFromId', {'messageId': message_id, 'target': target}
            )
            result = json.loads(res)
            if result['code'] == 0:
                return await self.instance.package_message('', result['data'])

    async def delete_message(self, message_id: str, target_id: Optional[str] = None) -> bool:
        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/delete_msg', {'message_id': message_id})

            result = json.loads(res)
            return result['status'] == 'ok'

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.post(
                '/recall',
                {
                    'sessionKey': self.session,
                    'messageId': message_id,
                    'target': target_id,
                },
            )
            result = json.loads(res)
            return result['code'] == 0

        return False

    # 获取账号信息

    async def get_friend_list(self) -> Optional[list]:
        """获取好友列表

        Returns:
            Optional[list]: 好友列表 - all: have
                each[dict]:
                    id(int): QQ号 - all: have
                    nickname(str): 昵称 - all: have
                    remark(str): 昵称 - all: have
        """
        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/get_friend_list')
            result = json.loads(res)
            if result['status'] == 'ok':
                for i in res['data']:
                    i['id'] = i.pop('user_id')
                return result['data']

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.get('/friendList')
            result = json.loads(res)
            if result['code'] == 0:
                return result['data']

    async def get_group_list(self, nocache: bool = False) -> Optional[list]:
        """获取群列表

        Args:
            nocache (bool, optional): 是否不使用缓存. 默认为 False. - cqhttp: required

        Returns:
            Optional[list]: 群列表
                each[dict]:
                    id(int): 群号 - all: have
                    name(str): 群名 - all: have

                    permission(UserPermission): Bot权限 - mirai: have

                    remark(str): 群备注 - cqhttp: have
                    create_time(int): 创建时间 - cqhttp: have
                    level(int): 群等级 - cqhttp: have
                    count(int): 群人数 - cqhttp: have
                    max_count(int): 最大群人数 - cqhttp: have
        """
        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/get_group_list', {'no_cache': nocache})
            result = json.loads(res)
            if result['status'] == 'ok':
                for i in res['data']:
                    i['id'] = i.pop('group_id')
                    i['name'] = i.pop('group_name')
                    i['remark'] = i.pop('group_memo')
                    i['create_time'] = i.pop('group_create_time')
                    i['level'] = i.pop('group_level')
                    i['count'] = i.pop('member_count')
                    i['max_count'] = i.pop('max_member_count')
                return result['data']

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.get('/groupList')
            result = json.loads(res)
            if result['code'] == 0:
                group_list = {}
                for i in res['data']:
                    if i['id'] not in group_list:
                        i['permission'] = UserPermission.from_str(i.pop('permission'))
                        group_list[i['id']] = i
                return list(group_list.values())

    async def get_group_member_list(
        self, group_id: GroupId, nocache: bool = False
    ) -> Optional[list]:
        """获取群成员列表

        Args:
            group_id (Union[str, int]): 群号 - all: required
            nocache (bool, optional): 是否不使用缓存. 默认为 False. - all: optional

        Returns:
            Optional[list]: 群成员列表
                each[dict]:
                    group_id(int): 群号 - all: have
                    user_id(int): QQ号 - all: have
                    nickname(str): 群昵称 - all: have
                    age(int): 年龄 - all: have
                    level(str): 等级 - all: have
                    gender(UserGender): 性别 - all: have
                    permission(UserPermission): 权限 - all: have
                    title(str): 群头衔 - all: have
                    join_time(int): 加入时间 - all: have
                    last_sent_time(int): 最后发言时间 - all: have

                    email(str): 邮箱 - mirai: have
                    sign(str): 登录设备 - mirai: have
                    mute_time_remaining(int): 禁言剩余时间 - mirai: have

                    name(str): 昵称 - cqhttp: have
                    area(str): 地区 - cqhttp: have
                    unfriendly(bool): 是否不良记录成员 - cqhttp: have
                    title_expire_time(int): 群头衔过期时间 - cqhttp: have
                    card_changeable(bool): 是否允许修改群名片 - cqhttp: have
                    mute_expire_time(int): 禁言到期时间 - cqhttp: have
        """
        if not group_id:
            return None

        group_id = int(group_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post(
                '/get_group_member_list', {'group_id': group_id, 'no_cache': nocache}
            )
            result = json.loads(res)
            result_list = []
            if result['status'] == 'ok':
                for i in res['data']:
                    ires = await self.post(
                        '/get_group_member_info',
                        {
                            'group_id': group_id,
                            'user_id': i['user_id'],
                            'no_cache': nocache,
                        },
                    )
                    iresult = json.loads(ires)
                    if iresult['status'] == 'ok':
                        data = iresult['data']
                        result_list.append(
                            {
                                'group_id': data['group_id'],
                                'user_id': data['user_id'],
                                'nickname': data['card'],
                                'age': data['age'],
                                'level': data['level'],
                                'gender': UserGender.from_str(data['sex']),
                                'permission': UserPermission.from_str(data['role']),
                                'title': data['title'],
                                'join_time': data['join_time'],
                                'last_sent_time': data['last_sent_time'],
                                'name': data['nickname'],
                                'area': data['area'],
                                'unfriendly': data['unfriendly'],
                                'title_expire_time': data['title_expire_time'],
                                'card_changeable': data['card_changeable'],
                                'mute_expire_time': data['shut_up_timestamp'],
                            }
                        )
                return result_list

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.get(
                '/latestMemberList' if nocache else '/memberList', {'target': group_id}
            )
            result = json.loads(res)
            result_list = []
            if result['code'] == 0:
                for i in result['data']:
                    ires = await self.get(
                        '/memberProfile', {'target': group_id, 'memberId': i['id']}
                    )
                    iresult = json.loads(ires)
                    if iresult['code'] == 0:
                        data = iresult['data']
                        result_list.append(
                            {
                                'group_id': i['group']['id'],
                                'user_id': i['id'],
                                'nickname': i['memberName'],
                                'age': data['age'],
                                'level': data['level'],
                                'gender': UserGender.from_str(data['sex']),
                                'permission': UserPermission.from_str(i['permission']),
                                'title': i['specialTitle'],
                                'join_time': i['joinTimestamp'],
                                'last_sent_time': i['lastSpeakTimestamp'],
                                'sign': data['sign'],
                                'email': data['email'],
                                'mute_time_remaining': data['muteTimeRemaining'],
                            }
                        )
                return result_list

    async def get_user_info(
        self,
        user_id: UserId,
        relation_type: RelationType = RelationType.STRANGER,
        group_id: Optional[GroupId] = None,
        no_cache: bool = False,
    ) -> Optional[dict]:
        """获取用户信息

        Args:
            user_id (Union[str, int]): QQ号 - all: required
            relation_type (RelationType, optional): 与用户的关系 [1:FRIEND, 2:GROUP, 3:STRANGER].
                                           默认为 RelationType.STRANGER. - all: optional
            group_id (Optional[Union[str, int]], optional): 群号[type为2时需要指定] - all: optional
            no_cache (bool, optional): 是否不使用缓存. 默认为 False. - all: optional

        Returns:
            Optional[dict]: 用户信息=
            GROUP -
                同 get_group_member_list 信息
            FRIEND, STRANGER -
                user_id(int): QQ号 - all: have
                nickname(str): 昵称 - all: have
                age(int): 年龄 - all: have
                level(str): 等级 - all: have
                gender(UserGender): 性别 - all: have

                sign(str): 登录设备 - mirai: have

                qid(str): qid ID身份卡 - cqhttp: have
                login_days(int): 登录天数 - cqhttp: have
        """
        if not user_id:
            return None

        user_id = int(user_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            result = None
            if relation_type == RelationType.GROUP:
                if not group_id:
                    return None
                res = await self.get_group_member_list(group_id, no_cache)
                if res:
                    for i in res:
                        if i['user_id'] == user_id:
                            result = i
            elif relation_type in [RelationType.FRIEND, RelationType.STRANGER]:
                res = await self.post(
                    '/get_stranger_info', {'user_id': user_id, 'no_cache': no_cache}
                )
                result = json.loads(res)
                if result['status'] == 'ok':
                    result = result['data']
                    result['gender'] = UserGender.from_str(result.pop('sex'))
                else:
                    result = None
            return result

        if self.adapter_type == BotAdapterType.MIRAI:
            result = None
            if relation_type == RelationType.GROUP:
                if not group_id:
                    return None
                res = await self.get_group_member_list(group_id, no_cache)
                if res:
                    for i in res:
                        if i['user_id'] == user_id:
                            result = i
            elif relation_type == RelationType.FRIEND:
                res = await self.get('/friendProfile', {'target': user_id})
                result = json.loads(res)
                result['gender'] = UserGender.from_str(result.pop('sex'))
            elif relation_type == RelationType.STRANGER:
                res = await self.get('/userProfile', {'target': user_id})
                result = json.loads(res)
                result['gender'] = UserGender.from_str(result.pop('sex'))
            return result

    # 账号管理

    async def delete_friend(self, user_id: UserId) -> bool:
        """删除好友

        Args:
            user_id (Union[str, int]): QQ号 - all: required

        Returns:
            bool: 是否成功
        """
        if not user_id:
            return False

        user_id = int(user_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/delete_friend', {'user_id': user_id})
            result = json.loads(res)
            return result['status'] == 'ok'

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.post('/deleteFriend', {'target': user_id})
            result = json.loads(res)
            return result['code'] == 0

        return False

    # 群操作

    async def mute(self, group_id: GroupId, user_id: UserId, time: int) -> bool:
        """禁言

        Args:
            group_id (Union[str, int]): 群号 - all: required
            user_id (Union[str, int]): QQ号 - all: required
            time (int): 禁言时间(秒) [0为解除] - all: required

        Returns:
            bool: 是否成功
        """
        if not group_id or not user_id or not time or time < 0:
            return False

        group_id = int(group_id)
        user_id = int(user_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post(
                '/set_group_ban',
                {'group_id': group_id, 'user_id': user_id, 'duration': time},
            )
            result = json.loads(res)
            return result['status'] == 'ok'

        if self.adapter_type == BotAdapterType.MIRAI:
            if time == 0:
                res = await self.post(
                    '/unmute', {'target': group_id, 'memberId': user_id}
                )
            else:
                res = await self.post(
                    '/mute', {'target': group_id, 'memberId': user_id, 'time': time}
                )
            result = json.loads(res)
            return result['code'] == 0

        return False

    async def remove_group_member(
        self,
        group_id: GroupId,
        user_id: UserId,
        reject: bool = False,
        msg: Optional[str] = None,
    ) -> bool:
        """移除群成员

        Args:
            group_id (Union[str, int]): 群号 - all: required
            user_id (Union[str, int]): QQ号 - all: required
            reject (bool, optional): 拒绝再加群 - all: optional, 默认False
            msg (Optional[str], optional): 退群信息 - mirai: optional, 默认None

        Returns:
            bool: 是否成功
        """
        if not group_id or not user_id:
            return False

        group_id = int(group_id)
        user_id = int(user_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post(
                '/set_group_kick',
                {
                    'group_id': group_id,
                    'user_id': user_id,
                    'reject_add_request': reject,
                },
            )
            result = json.loads(res)
            return result['status'] == 'ok'

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.post(
                '/kick',
                {'target': group_id, 'memberId': user_id, 'block': reject, 'msg': msg},
            )
            result = json.loads(res)
            return result['code'] == 0

        return False

    async def exit_group(self, group_id: GroupId, is_dismiss: bool = False) -> bool:
        """退出群

        Args:
            group_id (Union[str, int]): 群号 - all: required
            is_dismiss (bool, optional): 是否解散 - cqhttp: optional, 默认False (经过测试, cqhttp, mirai均不支持解散群)

        Returns:
            bool: 是否成功
        """
        if not group_id:
            return False

        group_id = int(group_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post(
                '/set_group_leave', {'group_id': group_id, 'is_dismiss': is_dismiss}
            )
            result = json.loads(res)
            return result['status'] == 'ok'

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.get('/quit', {'target': group_id})
            result = json.loads(res)
            return result['code'] == 0

        return False

    async def mute_all(self, group_id: GroupId, enable: bool = True) -> bool:
        """全员禁言

        Args:
            group_id (Union[str, int]): 群号 - all: required
            enable (bool, optional): 禁言(True)/解除禁言(False) - all: optional, 默认True

        Returns:
            bool: 是否成功
        """
        if not group_id:
            return False

        group_id = int(group_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post(
                '/set_group_whole_ban', {'group_id': group_id, 'enable': enable}
            )
            result = json.loads(res)
            return result['status'] == 'ok'

        if self.adapter_type == BotAdapterType.MIRAI:
            if enable:
                res = await self.post('/muteAll', {'target': group_id})
            else:
                res = await self.post('/unmuteAll', {'target': group_id})
            result = json.loads(res)
            return result['code'] == 0

        return False

    async def set_essence_msg(
        self, message_id: MessageId, group_id: Optional[GroupId] = None
    ) -> bool:
        """设置精华消息

        Args:
            message_id (Union[str, int]): 消息ID - all: required
            group_id (Optional[Union[str, int]], optional): - mirai required.

        Returns:
            bool: 是否成功
        """
        if not message_id:
            return False

        message_id = int(message_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/set_essence_msg', {'message_id': message_id})
            result = json.loads(res)
            return result['status'] == 'ok'

        if self.adapter_type == BotAdapterType.MIRAI:
            if not group_id:
                return False

            group_id = int(group_id)
            res = await self.post(
                '/recall', {'target': group_id, 'messageId': message_id}
            )
            result = json.loads(res)
            return result['code'] == 0

        return False

    async def delete_essence_msg(self, message_id: MessageId) -> bool:
        """移除精华消息(仅cqhttp支持)

        Args:
            message_id (Union[str, int]): 消息ID - cqhttp: required

        Returns:
            bool: 是否成功
        """
        if not message_id:
            return False

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/delete_essence_msg', {'message_id': message_id})
            result = json.loads(res)
            return result['status'] == 'ok'

        return False

    @abc.abstractmethod
    async def send_group_notice(self, group_id: str, content: str, **kwargs) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def send_nudge(self, user_id: str, group_id: str):
        raise NotImplementedError

    async def set_member_info(self, user_id: )
