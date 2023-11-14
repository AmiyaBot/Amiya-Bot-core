from .qqGuild import QQGuildBotInstance, QQGuildSandboxBotInstance


notice = (
    '\nWarning: "{name}" is deprecated and will be removed in future versions. '
    'Please using "from amiyabot.adapters.tencent.qqGuild import {new_name}"\n'
)


class TencentBotInstance(QQGuildBotInstance):
    def __init__(self, appid: str, token: str):
        super().__init__(appid, token)

        print(notice.format(name=self.__class__.__name__, new_name=QQGuildBotInstance.__name__))


class TencentSandboxBotInstance(QQGuildSandboxBotInstance):
    def __init__(self, appid: str, token: str):
        super().__init__(appid, token)

        print(notice.format(name=self.__class__.__name__, new_name=QQGuildSandboxBotInstance.__name__))
