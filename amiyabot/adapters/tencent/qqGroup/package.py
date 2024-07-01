from amiyabot.builtin.message import Event, Message
from amiyabot.adapters import BotAdapterProtocol


async def package_qq_group_message(instance: BotAdapterProtocol, event: str, message: dict, is_reference: bool = False):
    message_created = [
        'C2C_MESSAGE_CREATE',
        'GROUP_AT_MESSAGE_CREATE',
    ]
    if event in message_created:
        data = Message(instance, message)
        data.is_direct = event == 'C2C_MESSAGE_CREATE'
        data.is_at = True

        data.message_id = message['id']
        data.user_id = message['author']['id']

        if data.is_direct:
            data.user_openid = message['author']['user_openid']
        else:
            data.user_openid = message['author']['member_openid']
            data.channel_id = message['group_id']
            data.channel_openid = message['group_openid']

        if 'attachments' in message:
            for item in message['attachments']:
                if item['content_type'].startswith('image'):
                    data.image.append(item['url'])

        if 'content' in message:
            data.set_text(message['content'])

        return data

    return Event(instance, event, message)
