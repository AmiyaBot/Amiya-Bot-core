import abc
import asyncio
import json

from typing import Optional

from amiyabot.adapters import BotAdapterProtocol, PACKAGE_RESULT
from amiyabot.network.httpRequests import http_requests

from .define import *


class APIResponse:
    class RequestType(Enum):
        GET = 0
        POST = 1
        UNKNOWN = 2

        @classmethod
        def from_str(cls, value: str):
            if value.lower() == 'get':
                return cls.GET
            if value.lower() == 'post':
                return cls.POST
            return cls.UNKNOWN

    # 响应数据
    status: int
    origin: Optional[str]
    data: Optional[dict]

    # 请求信息
    method: RequestType
    path: str
    params: Optional[dict]
    headers: Optional[dict]
    kwargs: dict

    def __init__(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        res: Optional[str] = None,
        **kwargs,
    ):
        self.__init(res)
        self.method = self.RequestType.from_str(method)
        self.path = path
        self.params = params
        self.headers = headers
        self.kwargs = kwargs

    def __init(self, res: Optional[str] = None):
        if res:
            try:
                self.data = json.loads(res)
                self.status = 200
                self.origin = res
            except json.JSONDecodeError:
                self.data = None
                self.status = 500
                self.origin = res
        else:
            self.data = None
            self.status = 500
            self.origin = res

    async def retry(self, max_retry: int = 3, retry_interval: int = 1) -> 'APIResponse':
        """重试

        Args:
            max_retry (int, optional): 最大重试次数. 默认为 3
            retry_interval (int, optional): 重试间隔, 单位秒. 默认为 1

        Returns:
            APIResponse: HTTP 响应
        """
        if self.status == 200:
            return self

        for _ in range(max_retry):
            if self.method == self.RequestType.GET:
                res = await http_requests.get(self.path, self.params, **self.kwargs)
            elif self.method == self.RequestType.POST:
                res = await http_requests.post(self.path, self.params, self.headers, **self.kwargs)
            else:
                res = None

            if res:
                self.__init(res)
                if self.status == 200:
                    return self
            await asyncio.sleep(retry_interval)

        return self


class BotAdapterAPI:
    def __init__(self, instance: BotAdapterProtocol, adapter_type: BotAdapterType):
        self.instance = instance
        self.adapter_type = adapter_type
        self.token = instance.token
        if adapter_type in [BotAdapterType.CQHTTP, BotAdapterType.MIRAI]:
            self.url = f'http://{instance.host}:{instance.http_port}'
        elif adapter_type == BotAdapterType.KOOK:
            self.url = 'https://www.kookapp.cn/api/v3'

    @property
    def session(self) -> str:
        if self.adapter_type == BotAdapterType.MIRAI and self.instance.session:
            return self.instance.session
        return ''

    async def get(self, path: str, params: Optional[dict] = None, **kwargs) -> APIResponse:
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
            if kwargs.get('headers'):
                kwargs['headers'].update({'Authorization': self.token})
            else:
                kwargs['headers'] = {'Authorization': self.token}
            res = await http_requests.get(
                self.url + path,
                params=params,
                **kwargs,
            )
            if kwargs.get('headers'):
                headers = kwargs.pop('headers')
            else:
                headers = None
            return APIResponse('GET', path, params, headers, res, **kwargs)

        if self.adapter_type == BotAdapterType.MIRAI:
            if not params:
                params = {}
            params['sessionKey'] = self.session
            res = await http_requests.get(self.url + path, params=params, **kwargs)
            if kwargs.get('headers'):
                headers = kwargs.pop('headers')
            else:
                headers = None
            return APIResponse('GET', path, params, headers, res, **kwargs)

        if self.adapter_type == BotAdapterType.KOOK:
            if kwargs.get('headers'):
                kwargs['headers'].update({'Authorization': f'Bot {self.token}'})
            else:
                kwargs['headers'] = {'Authorization': f'Bot {self.token}'}
            res = await http_requests.get(self.url + path, params, **kwargs)
            if kwargs.get('headers'):
                headers = kwargs.pop('headers')
            else:
                headers = None
            return APIResponse('GET', path, params, headers, res, **kwargs)

        if kwargs.get('headers'):
            headers = kwargs.pop('headers')
        else:
            headers = None
        return APIResponse('GET', path, params, headers, None, **kwargs)

    async def post(
        self,
        path: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs,
    ) -> APIResponse:
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
            res = await http_requests.post(self.url + path, params, headers, **kwargs)
            return APIResponse('POST', path, params, headers, res, **kwargs)

        if self.adapter_type == BotAdapterType.MIRAI:
            if not params:
                params = {}
            params['sessionKey'] = self.session
            res = await http_requests.post(self.url + path, params, headers, **kwargs)
            return APIResponse('POST', path, params, headers, res, **kwargs)

        if self.adapter_type == BotAdapterType.KOOK:
            if headers:
                headers.update({'Authorization': f'Bot {self.token}'})
            else:
                headers = {'Authorization': f'Bot {self.token}'}
            res = await http_requests.post(self.url + path, params, headers, **kwargs)
            return APIResponse('POST', path, params, headers, res, **kwargs)

        return APIResponse('POST', path, params, headers, None, **kwargs)

    # 缓存操作

    async def get_message(
        self, message_id: MessageId, target: Optional[Union[UserId, GroupId]] = None
    ) -> Optional[PACKAGE_RESULT]:
        """通过消息 ID 获取消息

        Args:
            message_id (MessageId): 消息 ID - all: required
            target: 好友id或群id - mirai: required
        Returns:
            Optional[PACKAGE_RESULT]: 消息 - all: have
        """
        if not message_id:
            return None

        message_id = int(message_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/get_msg', {'message_id': message_id})
            if res.data and res.data['status'] == 'ok':
                message = res.data['data']
                message['post_type'] = 'message'
                return await self.instance.package_message('', message)

        if self.adapter_type == BotAdapterType.MIRAI:
            if not target:
                return None

            target = int(target)
            res = await self.get('/messageFromId', {'messageId': message_id, 'target': target})
            if res.data and res.data['code'] == 0:
                return await self.instance.package_message('', res.data['data'])

    async def delete_message(self, message_id: str, target_id: Optional[str] = None) -> Optional[bool]:
        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/delete_msg', {'message_id': message_id})
            if res.data and res.data['status'] == 'ok':
                return True
            return False

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.post(
                '/recall',
                {
                    'sessionKey': self.session,
                    'messageId': message_id,
                    'target': target_id,
                },
            )
            if res.data and res.data['code'] == 0:
                return True
            return False

        return None

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
            if res.data and res.data['status'] == 'ok':
                for i in res.data['data']:
                    i['id'] = i.pop('user_id')
                return res.data['data']

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.get('/friendList')
            if res.data and res.data['code'] == 0:
                return res.data['data']

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
            if res.data and res.data['status'] == 'ok':
                for i in res.data['data']:
                    i['id'] = i.pop('group_id')
                    i['name'] = i.pop('group_name')
                    i['remark'] = i.pop('group_memo') if i.get('group_memo') else ''
                    i['create_time'] = i.pop('group_create_time')
                    i['level'] = i.pop('group_level')
                    i['count'] = i.pop('member_count')
                    i['max_count'] = i.pop('max_member_count')
                return res.data['data']

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.get('/groupList')
            if res.data and res.data['code'] == 0:
                group_list = {}
                for i in res.data['data']:
                    if i['id'] not in group_list:
                        i['permission'] = UserPermission.from_str(i.pop('permission'))
                        group_list[i['id']] = i
                return list(group_list.values())

    async def get_group_member_list(self, group_id: GroupId, nocache: bool = False) -> Optional[list]:
        """获取群成员列表

        Args:
            group_id (GroupId): 群号 - all: required
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
            res = await self.post('/get_group_member_list', {'group_id': group_id, 'no_cache': nocache})
            result_list = []
            if res.data and res.data['status'] == 'ok':
                for i in res.data['data']:
                    ires = await self.post(
                        '/get_group_member_info',
                        {
                            'group_id': group_id,
                            'user_id': i['user_id'],
                            'no_cache': nocache,
                        },
                    )
                    if ires.data and ires.data['status'] == 'ok':
                        data = ires.data['data']
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
            res = await self.get('/latestMemberList' if nocache else '/memberList', {'target': group_id})
            result_list = []
            if res.data and res.data['code'] == 0:
                for i in res.data['data']:
                    ires = await self.get('/memberProfile', {'target': group_id, 'memberId': i['id']})
                    if ires.data and ires.data['code'] == 0:
                        data = ires.data['data']
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
            user_id (UserId): QQ号 - all: required
            relation_type (RelationType, optional): 与用户的关系 [1:FRIEND, 2:GROUP, 3:STRANGER].
                                           默认为 RelationType.STRANGER. - all: optional
            group_id (Optional[Union[str, int]], optional): 群号[type为2时需要指定] - all: optional
            no_cache (bool, optional): 是否不使用缓存. 默认为 False. - all: optional

        Returns:
            Optional[dict]: 用户信息
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
                res = await self.post('/get_stranger_info', {'user_id': user_id, 'no_cache': no_cache})
                if res.data and res.data['status'] == 'ok':
                    result = res.data['data']
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
                if res.data:
                    result = res.data
                    result['gender'] = UserGender.from_str(result.pop('sex'))
            elif relation_type == RelationType.STRANGER:
                res = await self.get('/userProfile', {'target': user_id})
                if res.data:
                    result = res.data
                    result['gender'] = UserGender.from_str(result.pop('sex'))
            return result

    @abc.abstractmethod
    async def get_user_avatar(self, user_id: UserId, **kwargs) -> Optional[bytes]:
        raise NotImplementedError

    # 账号管理

    async def delete_friend(self, user_id: UserId) -> Optional[bool]:
        """删除好友

        Args:
            user_id (UserId): QQ号 - all: required

        Returns:
            bool: 是否成功
        """
        if not user_id:
            return False

        user_id = int(user_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/delete_friend', {'user_id': user_id})
            if res.data and res.data['status'] == 'ok':
                return True
            return False

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.post('/deleteFriend', {'target': user_id})
            if res.data and res.data['code'] == 0:
                return True
            return False

        return None

    # 群操作

    async def mute(self, group_id: GroupId, user_id: UserId, time: int) -> Optional[bool]:
        """禁言

        Args:
            group_id (GroupId): 群号 - all: required
            user_id (UserId): QQ号 - all: required
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
            if res.data and res.data['status'] == 'ok':
                return True
            return False

        if self.adapter_type == BotAdapterType.MIRAI:
            if time == 0:
                res = await self.post('/unmute', {'target': group_id, 'memberId': user_id})
            else:
                res = await self.post('/mute', {'target': group_id, 'memberId': user_id, 'time': time})
            if res.data and res.data['code'] == 0:
                return True
            return False

        return None

    async def remove_group_member(
        self,
        group_id: GroupId,
        user_id: UserId,
        reject: bool = False,
        msg: Optional[str] = None,
    ) -> Optional[bool]:
        """移除群成员

        Args:
            group_id (GroupId): 群号 - all: required
            user_id (UserId): QQ号 - all: required
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
            if res.data and res.data['status'] == 'ok':
                return True
            return False

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.post(
                '/kick',
                {'target': group_id, 'memberId': user_id, 'block': reject, 'msg': msg},
            )
            if res.data and res.data['code'] == 0:
                return True
            return False

        return None

    async def exit_group(self, group_id: GroupId, is_dismiss: bool = False) -> Optional[bool]:
        """退出群

        Args:
            group_id (GroupId): 群号 - all: required
            is_dismiss (bool, optional): 是否解散 - cqhttp: optional, 默认False (经过测试, cqhttp, mirai均不支持解散群)

        Returns:
            bool: 是否成功
        """
        if not group_id:
            return False

        group_id = int(group_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/set_group_leave', {'group_id': group_id, 'is_dismiss': is_dismiss})
            if res.data and res.data['status'] == 'ok':
                return True
            return False

        if self.adapter_type == BotAdapterType.MIRAI:
            res = await self.get('/quit', {'target': group_id})
            if res.data and res.data['code'] == 0:
                return True
            return False

        return None

    async def mute_all(self, group_id: GroupId, enable: bool = True) -> Optional[bool]:
        """全员禁言

        Args:
            group_id (GroupId): 群号 - all: required
            enable (bool, optional): 禁言(True)/解除禁言(False) - all: optional, 默认True

        Returns:
            bool: 是否成功
        """
        if not group_id:
            return False

        group_id = int(group_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/set_group_whole_ban', {'group_id': group_id, 'enable': enable})
            if res.data and res.data['status'] == 'ok':
                return True
            return False

        if self.adapter_type == BotAdapterType.MIRAI:
            if enable:
                res = await self.post('/muteAll', {'target': group_id})
            else:
                res = await self.post('/unmuteAll', {'target': group_id})
            if res.data and res.data['code'] == 0:
                return True
            return False

        return None

    async def set_essence_msg(self, message_id: MessageId, group_id: Optional[GroupId] = None) -> Optional[bool]:
        """设置精华消息

        Args:
            message_id (MessageId): 消息ID - all: required
            group_id (Optional[GroupId], optional): - mirai required.

        Returns:
            bool: 是否成功
        """
        if not message_id:
            return False

        message_id = int(message_id)

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/set_essence_msg', {'message_id': message_id})
            if res.data and res.data['status'] == 'ok':
                return True
            return False

        if self.adapter_type == BotAdapterType.MIRAI:
            if not group_id:
                return False
            group_id = int(group_id)
            res = await self.post('/recall', {'target': group_id, 'messageId': message_id})
            if res.data and res.data['code'] == 0:
                return True
            return False

    async def delete_essence_msg(self, message_id: MessageId) -> Optional[bool]:
        """移除精华消息(仅cqhttp支持)

        Args:
            message_id (MessageId): 消息ID - cqhttp: required

        Returns:
            bool: 是否成功
        """
        if not message_id:
            return False

        if self.adapter_type == BotAdapterType.CQHTTP:
            res = await self.post('/delete_essence_msg', {'message_id': message_id})
            if res.data and res.data['status'] == 'ok':
                return True
            return False

        return None

    @abc.abstractmethod
    async def send_group_notice(self, group_id: GroupId, content: str, **kwargs) -> Optional[bool]:
        raise NotImplementedError

    @abc.abstractmethod
    async def send_nudge(self, user_id: UserId, group_id: GroupId):
        raise NotImplementedError

    async def set_member_info(
        self,
        group_id: GroupId,
        user_id: UserId,
        nickname: Optional[str] = None,
        special_title: Optional[str] = None,
    ) -> Optional[bool]:
        """设置群成员信息

        Args:
            group_id (GroupId): 群号 - all: required
            user_id (UserId): QQ号 - all: required
            nickname (Optional[str], optional): 群昵称 - all: optional
            special_title (Optional[str], optional): 群头衔 - all: optional

        Returns:
            Optional[bool]: 是否成功 - all: optional
        """
        if not user_id or not group_id:
            return False
        user_id = int(user_id)
        group_id = int(group_id)
        if not nickname and not special_title:
            return True
        if self.adapter_type == BotAdapterType.CQHTTP:
            flag = True
            if nickname:
                res = await self.post(
                    '/set_group_card',
                    {'group_id': group_id, 'user_id': user_id, 'card': nickname},
                )
                if res.data:
                    result = res.data
                    if result['status'] != 'ok':
                        flag = False
            if special_title:
                res = await self.post(
                    '/set_group_special_title',
                    {
                        'group_id': group_id,
                        'user_id': user_id,
                        'special_title': special_title,
                    },
                )
                if res.data:
                    result = res.data
                    if result['status'] != 'ok':
                        flag = False
            return flag
        if self.adapter_type == BotAdapterType.MIRAI:
            info = {}
            if nickname:
                info['name'] = nickname
            if special_title:
                info['specialTitle'] = special_title
            res = await self.post(
                '/memberInfo',
                {
                    'target': group_id,
                    'memberId': user_id,
                    'info': info,
                },
            )
            if res.data and res.data['code'] == 0:
                return True
            return False
