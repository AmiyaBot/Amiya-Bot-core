from amiyabot.adapters.onebot11 import OneBot11Instance

from .api import CQHttpAPI
from .forwardMessage import CQHTTPForwardMessage


def cq_http(host: str, ws_port: int, http_port: int):
    def adapter(appid: str, token: str):
        return CQHttpBotInstance(appid, token, host, ws_port, http_port)

    return adapter


class CQHttpBotInstance(OneBot11Instance):
    def __str__(self):
        return 'CQHttp'

    @property
    def api(self):
        return CQHttpAPI(self.host, self.http_port, self.token)

    def get_user_avatar(self, message: dict):
        return f'https://q.qlogo.cn/headimg_dl?dst_uin=%s&spec=100' % str(message['sender']['user_id'])
