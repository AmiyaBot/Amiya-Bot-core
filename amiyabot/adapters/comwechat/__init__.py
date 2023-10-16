import json

from amiyabot import Chain
from amiyabot.adapters.onebot12 import OneBot12Instance, build_message_send


def com_wechat(host: str, ws_port: int, http_port: int):
    def adapter(appid: str, token: str):
        return ComWeChatBotInstance(appid, token, host, ws_port, http_port)

    return adapter


class ComWeChatBotInstance(OneBot12Instance):
    ...
