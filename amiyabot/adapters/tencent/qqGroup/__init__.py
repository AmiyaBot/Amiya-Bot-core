from amiyabot.adapters.tencent.qqGuild import QQGuildBotInstance

from .api import QQGroupAPI
from .package import package_qq_group_message


def qq_group(client_secret: str):
    def adapter(appid: str, token: str):
        return QQGroupBotInstance(appid, token, client_secret)

    return adapter


class QQGroupBotInstance(QQGuildBotInstance):
    def __init__(self, appid: str, token: str, client_secret: str):
        super().__init__(appid, token)

        self.__access_token_api = QQGroupAPI(self.appid, client_secret)

    def __str__(self):
        return 'QQGroup'

    @property
    def api(self):
        return self.__access_token_api

    @property
    def package_method(self):
        return package_qq_group_message
