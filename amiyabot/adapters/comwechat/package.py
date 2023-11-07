from amiyabot.adapters import BotAdapterProtocol
from amiyabot.adapters.onebot.v12 import package_onebot12_message


async def package_com_wechat_message(instance: BotAdapterProtocol, data: dict):
    msg = await package_onebot12_message(instance, data)

    if msg:
        if data['type'] == 'message':
            message_chain = data['message']

            if message_chain:
                for chain in message_chain:
                    chain_data = chain['data']

                    if chain['type'] == 'wx.emoji':
                        msg.face.append(chain_data['file_id'])

        else:
            if data['detail_type']:
                if data['sub_type']:
                    msg.append(instance, '{type}.{detail_type}.{sub_type}'.format(**data), data)

    return msg
