from amiyabot.builtin.message import Event, Message
from amiyabot.adapters import BotAdapterProtocol


def package_mirai_message(instance: BotAdapterProtocol, account: str, data: dict):
    if 'type' not in data:
        return None

    if data['type'] == 'FriendMessage':
        msg = Message(instance, data)
        msg.message_type = 'friend'
        msg.is_direct = True
        msg.nickname = data['sender']['nickname']

    elif data['type'] in ['GroupMessage', 'TempMessage']:
        msg = Message(instance, data)
        msg.message_type = 'group' if data['type'] == 'GroupMessage' else 'temp'
        msg.channel_id = str(data['sender']['group']['id'])
        msg.nickname = data['sender']['memberName']
        msg.is_admin = data['sender']['permission'] in ['OWNER', 'ADMINISTRATOR']

    else:
        return Event(instance, data['type'], data)

    msg.user_id = str(data['sender']['id'])
    msg.avatar = f'https://q.qlogo.cn/headimg_dl?dst_uin={msg.user_id}&spec=100'

    message_chain = data['messageChain']
    text = ''

    if message_chain:
        for chain in message_chain:
            if chain['type'] == 'Source':
                msg.message_id = chain['id']

            if chain['type'] == 'At':
                if str(chain['target']) == str(account):
                    msg.is_at = True
                else:
                    msg.at_target.append(chain['target'])

            if chain['type'] == 'Plain':
                text += chain['text'].strip()

            if chain['type'] == 'Face':
                msg.face.append(chain['faceId'])

            if chain['type'] == 'Image':
                msg.image.append(chain['url'].strip())

    msg.set_text(text)
    return msg
