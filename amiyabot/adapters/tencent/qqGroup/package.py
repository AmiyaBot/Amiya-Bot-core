from amiyabot.builtin.message import Event, Message
from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters.common import text_convert


async def package_qq_group_message(instance: BotAdapterProtocol, event: str, message: dict, is_reference: bool = False):
    message_created = [
        'C2C_MESSAGE_CREATE',
        'GROUP_AT_MESSAGE_CREATE',
    ]
    if event in message_created:
        data = Message(instance, message)
        data.is_direct = event == 'C2C_MESSAGE_CREATE'

        data.user_id = message['author']['id']
        data.user_openid = message['author']['member_openid']
        data.channel_id = message['group_id']
        data.channel_openid = message['group_openid']
        data.message_id = message['id']

        if 'content' in message:
            data = text_convert(data, message['content'].strip(), message['content'])

        return data

    return Event(instance, event, message)
