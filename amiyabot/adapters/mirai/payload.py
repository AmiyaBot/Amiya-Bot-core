import abc
import json

from typing import List, Optional, Tuple, Union


class MiraiPostPayload:
    @classmethod
    @abc.abstractmethod
    def builder(
        cls,
        command: str,
        sub_command: Optional[str] = None,
        content: Optional[dict] = None,
        options: Optional[dict] = None,
    ) -> Tuple[str, Union[dict, str]]:
        raise NotImplementedError('builder must be implemented when inheriting class GeneralDefinition.')

    @classmethod
    def friend_message(cls, session: str, target_id: str, chains: List[dict]):
        return cls.builder(
            'sendFriendMessage',
            content={
                'sessionKey': session,
                'target': target_id,
                'messageChain': chains,
            },
        )

    @classmethod
    def group_message(
        cls,
        session: str,
        target_id: str,
        chains: List[dict],
        quote: Optional[int] = None,
    ):
        return cls.builder(
            'sendGroupMessage',
            options={'quote': quote},
            content={
                'sessionKey': session,
                'target': target_id,
                'messageChain': chains,
                'quote': quote,
            },
        )

    @classmethod
    def temp_message(cls, session: str, target_id: str, group_id: str, chains: List[dict]):
        return cls.builder(
            'sendTempMessage',
            content={
                'sessionKey': session,
                'qq': target_id,
                'group': group_id,
                'messageChain': chains,
            },
        )

    @classmethod
    def mute(cls, session: str, target_id: str, member_id: str, time: int):
        return cls.builder(
            'mute',
            content={
                'sessionKey': session,
                'target': target_id,
                'memberId': member_id,
                'time': time,
            },
        )

    @classmethod
    def nudge(cls, session: str, target_id: str, group_id: str):
        return cls.builder(
            'sendNudge',
            content={
                'sessionKey': session,
                'target': target_id,
                'subject': group_id,
                'kind': 'Group',
            },
        )


class WebsocketAdapter(MiraiPostPayload):
    @classmethod
    def builder(
        cls,
        command: str,
        sub_command: Optional[str] = None,
        content: Optional[dict] = None,
        options: Optional[dict] = None,
        sync_id: int = 1,
    ):
        return command, json.dumps(
            {
                'syncId': sync_id,
                'command': command,
                'subCommand': sub_command,
                'content': content,
                **(options or {}),
            },
            ensure_ascii=False,
        )


class HttpAdapter(MiraiPostPayload):
    @classmethod
    def builder(
        cls,
        command: str,
        sub_command: Optional[str] = None,
        content: Optional[dict] = None,
        options: Optional[dict] = None,
    ):
        return command, content
