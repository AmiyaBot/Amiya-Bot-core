from .qqGuild import QQGuildBotInstance, QQGuildSandboxBotInstance


class TencentBotInstance(QQGuildBotInstance):
    def __init__(self, appid: str, token: str):
        super().__init__(appid, token)


class TencentSandboxBotInstance(QQGuildSandboxBotInstance):
    def __init__(self, appid: str, token: str):
        super().__init__(appid, token)


notice = (
    '"{name}" is deprecated and will be removed in future versions. '
    'Please using "from amiyabot.adapters.tencent.qqGuild import {new_name}"'
)
print('\n==== Warning ===============================================')
print(notice.format(name=TencentBotInstance.__name__, new_name=QQGuildBotInstance.__name__))
print(notice.format(name=TencentSandboxBotInstance.__name__, new_name=QQGuildSandboxBotInstance.__name__))
print('============================================================\n')
