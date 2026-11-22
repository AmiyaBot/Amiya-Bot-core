"""QQ 群适配器「框架下载并上传富媒体」的 payload 级用例。

不依赖网络：`aiohttp.ClientSession` 与 API 对象都被替换为记录请求的假实现，
断言只落在「发出了什么请求」与「最终 payload 长什么样」。
"""

import json
import asyncio

from types import SimpleNamespace

import pytest

from amiyabot.builtin import messageChain as chain_module
from amiyabot.builtin.messageChain import Chain, ChainBuilder
from amiyabot.adapters.tencent.qqGroup import builder as group_builder
from amiyabot.adapters.tencent.qqGroup import media as media_module
from amiyabot.adapters.tencent.qqGroup.builder import (
    SeqService,
    QQGroupChainBuilderOptions,
    build_message_send,
)

PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 120
URL = 'http://192.168.1.2:9000/image/a.png'
BIG_URL = 'http://192.168.1.2:9000/image/big.png'

# silk：完整文件以 #!SILK_V3 起头，裸流直接以版本字节 0x02 起头
SILK = b'#!SILK_V3' + b'\x00' * 200
SILK_BARE = b'\x02' + b'\x00' * 200
MP4 = b'\x00\x00\x00\x18ftypisom' + b'\x00' * 200

VOICE_URL = 'http://192.168.1.2:9000/resource/voice.silk'
VIDEO_URL = 'http://192.168.1.2:9000/resource/v.mp4'


# ---------------------------------------------------------------------------
# 假 HTTP 层
# ---------------------------------------------------------------------------


class FakeContent:
    def __init__(self, body: bytes):
        self.body = body

    async def iter_chunked(self, size: int):
        for index in range(0, len(self.body), size):
            yield self.body[index : index + size]


class FakeHTTPResponse:
    def __init__(self, status: int = 200, body: bytes = b'', content_type: str = ''):
        self.status = status
        self.body = body
        self.headers = {'Content-Type': content_type} if content_type else {}
        self.content_length = len(body)
        self.content = FakeContent(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeSession:
    """替换 aiohttp.ClientSession，按 FakeHTTP.routes 返回预置响应。"""

    def __init__(self, *args, **kwargs):
        FakeHTTP.sessions.append(kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def get(self, url, **kwargs):
        status, body, content_type = FakeHTTP.routes.get(url, (404, b'', 'text/plain'))
        return FakeHTTPResponse(status, body, content_type)

    def put(self, url, data=None, **kwargs):
        FakeHTTP.puts.append((url, data))
        return FakeHTTPResponse(200)


class FakeHTTP:
    routes = {}
    puts = []
    sessions = []

    @classmethod
    def reset(cls):
        cls.routes = {}
        cls.puts = []
        cls.sessions = []


@pytest.fixture(name='http')
def http_fixture(monkeypatch):
    FakeHTTP.reset()
    monkeypatch.setattr(media_module.aiohttp, 'ClientSession', FakeSession)
    return FakeHTTP


# ---------------------------------------------------------------------------
# 假 API / Builder
# ---------------------------------------------------------------------------


class FakeResult:
    def __init__(self, body=None):
        self.json = body
        self.text = json.dumps(body) if body is not None else ''
        self.error = None


class FakeAPI:
    """记录每次调用；upload_body 可为 body 或 (file_type) -> body 的函数。"""

    def __init__(self, upload_body=None, prepare_body=None, part_finish_body=None):
        self.upload_body = upload_body or (lambda file_type: {'file_info': f'FI{file_type}', 'ttl': 3600})
        self.prepare_body = prepare_body
        self.part_finish_body = part_finish_body if part_finish_body is not None else {'code': 0}
        self.calls = []

    async def upload_file(
        self,
        openid,
        file_type,
        url=None,
        srv_send_msg=False,
        is_direct=False,
        file_name=None,
        upload_id=None,
        file_data=None,
    ):
        self.calls.append(
            {
                'method': 'upload_file',
                'openid': openid,
                'file_type': file_type,
                'url': url,
                'file_name': file_name,
                'upload_id': upload_id,
                'file_data': file_data,
            }
        )

        body = self.upload_body(file_type) if callable(self.upload_body) else self.upload_body
        return FakeResult(body)

    async def upload_prepare(self, openid, file_type, file_size, file_name, md5, sha1, md5_10m, is_direct=False):
        self.calls.append(
            {
                'method': 'upload_prepare',
                'openid': openid,
                'file_type': file_type,
                'file_size': file_size,
                'file_name': file_name,
                'md5': md5,
                'sha1': sha1,
                'md5_10m': md5_10m,
            }
        )

        if self.prepare_body is None:
            return FakeResult(
                {
                    'upload_id': 'uid-1',
                    'block_size': str(5 * 1024 * 1024),
                    'parts': [
                        {
                            'index': 0,
                            'presigned_url': 'https://cos.example.com/part0',
                            'block_size': str(5 * 1024 * 1024),
                        },
                        {
                            'index': 1,
                            'presigned_url': 'https://cos.example.com/part1',
                            'block_size': str(5 * 1024 * 1024),
                        },
                    ],
                }
            )

        return FakeResult(self.prepare_body)

    async def upload_part_finish(self, openid, upload_id, part_index, block_size=0, md5=None, is_direct=False):
        self.calls.append(
            {
                'method': 'upload_part_finish',
                'upload_id': upload_id,
                'part_index': part_index,
                'block_size': block_size,
                'md5': md5,
            }
        )

        return FakeResult(self.part_finish_body)


class StubBuilder(ChainBuilder):
    def __init__(self, options: QQGroupChainBuilderOptions):
        self.options = options


def make_chain(options: QQGroupChainBuilderOptions) -> Chain:
    data = SimpleNamespace(
        message_id='msg-1',
        user_openid='user-1',
        channel_openid='group-1',
        is_direct=False,
        reference_message_id='',
    )

    return Chain(data=data, at=False, chain_builder=StubBuilder(options))


def send(api: FakeAPI, chain: Chain):
    return asyncio.run(build_message_send(api, chain, SeqService()))


def options(**kwargs) -> QQGroupChainBuilderOptions:
    return QQGroupChainBuilderOptions(**kwargs)


# ---------------------------------------------------------------------------
# 用例
# ---------------------------------------------------------------------------


def test_download_false_keeps_platform_download(http):
    """download=False：请求打在 /files 且带 url，不下载。"""
    api = FakeAPI()
    chain = make_chain(options(download_media=True)).image(url=URL, download=False)

    payloads = send(api, chain)

    assert [item['method'] for item in api.calls] == ['upload_file']
    assert api.calls[0]['url'] == URL
    assert api.calls[0]['file_data'] is None
    assert http.sessions == []
    assert payloads[0]['msg_type'] == 7
    assert payloads[0]['media'] == {'file_info': 'FI1'}


def test_download_true_uploads_binary_then_sends_media(http):
    """download=True + 200 image/png：先 file_data 上传，再发 msg_type=7。"""
    http.routes[URL] = (200, PNG, 'image/png')

    api = FakeAPI()
    chain = make_chain(options()).image(url=URL, download=True)

    payloads = send(api, chain)

    assert [item['method'] for item in api.calls] == ['upload_file']
    assert api.calls[0]['url'] is None
    assert api.calls[0]['file_data'] is not None
    assert api.calls[0]['file_type'] == 1
    assert api.calls[0]['file_name'].endswith('.png')
    assert payloads[0]['msg_type'] == 7
    assert payloads[0]['media'] == {'file_info': 'FI1'}


def test_download_true_rejects_non_image(http, monkeypatch):
    """图片链路遇到非 image/*：不发请求，只 warn。"""
    http.routes[URL] = (200, b'<html>error page</html>', 'text/html')

    records = record_warnings(monkeypatch)

    api = FakeAPI()
    chain = make_chain(options()).image(url=URL, download=True)

    payloads = send(api, chain)

    assert api.calls == []
    assert payloads == []
    assert any('reason=type_mismatch' in item for item in records)


def test_download_true_rejects_oversized_media(http, monkeypatch):
    """超过 media_max_bytes：不发请求，只 warn。"""
    http.routes[URL] = (200, PNG + b'0' * 512, 'image/png')

    records = record_warnings(monkeypatch)

    api = FakeAPI()
    chain = make_chain(options(media_max_bytes=64)).image(url=URL, download=True)

    payloads = send(api, chain)

    assert api.calls == []
    assert payloads == []
    assert any('reason=too_large' in item for item in records)


def test_download_404_falls_back_to_platform_url(http, monkeypatch):
    """下载 404：退回 url= 上传（兜底），日志含 status。"""
    records = record_warnings(monkeypatch)

    api = FakeAPI()
    chain = make_chain(options()).image(url=URL, download=True)

    payloads = send(api, chain)

    assert [item['method'] for item in api.calls] == ['upload_file']
    assert api.calls[0]['url'] == URL
    assert any('status=404' in item for item in records)
    assert payloads[0]['media'] == {'file_info': 'FI1'}


def test_download_true_uses_chunked_upload_for_large_media(http):
    """5MB < size ≤ 20MB：upload_prepare → PUT → upload_part_finish → upload_file(upload_id)。"""
    body = PNG + b'0' * (6 * 1024 * 1024)
    http.routes[BIG_URL] = (200, body, 'image/png')

    api = FakeAPI()
    chain = make_chain(options()).image(url=BIG_URL, download=True)

    payloads = send(api, chain)

    methods = [item['method'] for item in api.calls]
    assert methods == ['upload_prepare', 'upload_part_finish', 'upload_part_finish', 'upload_file']

    prepare = api.calls[0]
    assert prepare['file_size'] == len(body)
    assert len(prepare['md5']) == 32
    assert len(prepare['sha1']) == 40
    assert len(prepare['md5_10m']) == 32

    assert [item[0] for item in http.puts] == ['https://cos.example.com/part0', 'https://cos.example.com/part1']
    assert sum(len(item[1]) for item in http.puts) == len(body)

    final = api.calls[-1]
    assert final['upload_id'] == 'uid-1'
    assert final['file_data'] is None
    assert payloads[0]['media'] == {'file_info': 'FI1'}


def test_duplicate_url_uploads_once(http):
    """同一 Chain 内两个相同 URL：只上传一次。"""
    http.routes[URL] = (200, PNG, 'image/png')

    api = FakeAPI()
    chain = make_chain(options()).image(url=URL, download=True).image(url=URL, download=True)

    payloads = send(api, chain)

    assert [item['method'] for item in api.calls] == ['upload_file']
    assert [item['media']['file_info'] for item in payloads] == ['FI1', 'FI1']


def test_unsupported_format_downgrades_to_file_type_4(http, monkeypatch):
    """850019：保持原行为先按图片传，失败降级 file_type=4。"""

    def upload_body(file_type):
        if file_type == 1:
            return {'code': 850019, 'message': '不支持的文件格式'}
        return {'file_info': 'FI4', 'ttl': 3600}

    http.routes[URL] = (200, PNG, 'image/png')

    records = record_warnings(monkeypatch)

    api = FakeAPI(upload_body=upload_body)
    chain = make_chain(options()).image(url=URL, download=True)

    payloads = send(api, chain)

    assert [item['file_type'] for item in api.calls] == [1, 4]
    assert payloads[0]['media'] == {'file_info': 'FI4'}
    assert any('850019' in item for item in records)


def test_target_accepts_http_url(http):
    """target 里的 http(s) 地址等价于 url（旧版会被静默丢弃）。"""
    http.routes[URL] = (200, PNG, 'image/png')

    api = FakeAPI()
    chain = make_chain(options(download_media=True)).image(target=[URL])

    payloads = send(api, chain)

    assert len(chain.chain) == 1
    assert chain.chain[0].url == URL
    assert payloads[0]['media'] == {'file_info': 'FI1'}


def test_missing_local_file_warns_instead_of_silent_drop(http, monkeypatch):
    """不存在的本地路径：warn 而不是静默丢弃。"""
    records = record_warnings(monkeypatch)

    api = FakeAPI()
    chain = make_chain(options()).image(target=['./not-exists.png'])

    payloads = send(api, chain)

    assert chain.chain == []
    assert payloads == []
    assert any('not found' in item for item in records)


def test_media_failure_does_not_break_text(http):
    """下载失败不应中断整条 Chain，文本照常发出。"""
    api = FakeAPI()
    chain = make_chain(options()).text('hello').image(url=URL, download=True)

    payloads = send(api, chain)

    text_payloads = [item for item in payloads if item['content'] == 'hello']
    assert len(text_payloads) == 1


# ---------------------------------------------------------------------------
# 语音 / 视频：「框架下载直传」按 file_type 放开（issue #130）
# ---------------------------------------------------------------------------


def test_voice_download_disabled_by_default(http):
    """默认 download_media_types=(1,)：语音仍走平台侧 URL 下载，不碰本地媒体。"""
    api = FakeAPI()
    chain = make_chain(options(download_media=True)).voice(VOICE_URL)

    payloads = send(api, chain)

    assert [item['method'] for item in api.calls] == ['upload_file']
    assert api.calls[0]['file_type'] == 3
    assert api.calls[0]['url'] == VOICE_URL
    assert api.calls[0]['file_data'] is None
    assert http.sessions == []
    assert payloads[0]['media'] == {'file_info': 'FI3'}


def test_voice_download_opt_in_uploads_binary(http):
    """download_media_types 含 3：silk 走 file_data 直传，file_type 透传为 3。"""
    http.routes[VOICE_URL] = (200, SILK, '')

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 3))).voice(VOICE_URL)

    payloads = send(api, chain)

    assert [item['method'] for item in api.calls] == ['upload_file']
    call = api.calls[0]
    assert call['file_type'] == 3
    assert call['url'] is None
    assert call['file_data'] is not None
    assert call['file_name'].endswith('.silk')
    assert payloads[0]['msg_type'] == 7
    assert payloads[0]['media'] == {'file_info': 'FI3'}


def test_voice_download_accepts_silk_under_text_plain(http):
    """.silk 被静态服务器当成 text/plain：按魔数纠正，不能误杀。"""
    http.routes[VOICE_URL] = (200, SILK, 'text/plain')

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 3))).voice(VOICE_URL)

    payloads = send(api, chain)

    assert api.calls[0]['file_type'] == 3
    assert api.calls[0]['file_data'] is not None
    assert payloads[0]['media'] == {'file_info': 'FI3'}


def test_voice_download_accepts_bare_silk_stream(http):
    """裸 silk 流（无 #!SILK_V3 头，首字节 0x02）同样识别为语音。"""
    http.routes[VOICE_URL] = (200, SILK_BARE, 'application/octet-stream')

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 3))).voice(VOICE_URL)

    send(api, chain)

    assert api.calls[0]['file_type'] == 3
    assert api.calls[0]['file_data'] is not None


def test_voice_download_rejects_html(http, monkeypatch):
    """语音 URL 返回 HTML 错误页：拒绝直传，也不回退平台侧（平台同样下载不到）。"""
    http.routes[VOICE_URL] = (200, b'<html>404</html>', 'text/html')

    records = record_warnings(monkeypatch)

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 3))).voice(VOICE_URL)

    payloads = send(api, chain)

    assert api.calls == []
    assert payloads == []
    assert any('reason=type_mismatch' in item and 'file_type=3' in item for item in records)


def test_voice_download_rejects_image_body(http, monkeypatch):
    """file_type=3 只收 audio/*：图片内容即使魔数清晰也要拒绝。"""
    http.routes[VOICE_URL] = (200, PNG, 'image/png')

    records = record_warnings(monkeypatch)

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 3))).voice(VOICE_URL)

    payloads = send(api, chain)

    assert api.calls == []
    assert payloads == []
    assert any('reason=type_mismatch' in item for item in records)


def test_image_download_still_rejects_silk(http, monkeypatch):
    """回归：图片链路不能因为放开语音而接受 silk。"""
    http.routes[URL] = (200, SILK, 'audio/silk')

    records = record_warnings(monkeypatch)

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 3))).image(url=URL)

    payloads = send(api, chain)

    assert api.calls == []
    assert payloads == []
    assert any('reason=type_mismatch' in item for item in records)


def test_video_download_opt_in(http):
    """download_media_types 含 2：video/mp4 走直传，file_type=2。"""
    http.routes[VIDEO_URL] = (200, MP4, 'video/mp4')

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 2))).video(VIDEO_URL)

    payloads = send(api, chain)

    assert api.calls[0]['file_type'] == 2
    assert api.calls[0]['file_data'] is not None
    assert payloads[0]['media'] == {'file_info': 'FI2'}


def test_voice_download_failure_falls_back_to_platform(http, monkeypatch):
    """下载 500：语音仍回退平台侧 URL 上传（公网场景可能救回来）。"""
    http.routes[VOICE_URL] = (500, b'', 'text/plain')

    record_warnings(monkeypatch)

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 3))).voice(VOICE_URL)

    payloads = send(api, chain)

    assert [item['method'] for item in api.calls] == ['upload_file']
    assert api.calls[0]['url'] == VOICE_URL
    assert api.calls[0]['file_type'] == 3
    assert payloads[0]['media'] == {'file_info': 'FI3'}


def test_voice_download_cached_per_type(http):
    """同一 Chain 内重复的语音 URL 只上传一次。"""
    http.routes[VOICE_URL] = (200, SILK, '')

    api = FakeAPI()
    chain = make_chain(options(download_media=True, download_media_types=(1, 3)))
    chain.voice(VOICE_URL).voice(VOICE_URL)

    payloads = send(api, chain)

    assert [item['method'] for item in api.calls] == ['upload_file']
    assert [item['media']['file_info'] for item in payloads] == ['FI3', 'FI3']


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


class WarningRecorder:
    def __init__(self):
        self.records = []

    def __call__(self, text: str, *args, **kwargs):
        self.records.append(text % args if args else text)

    def __iter__(self):
        return iter(self.records)


def record_warnings(monkeypatch) -> WarningRecorder:
    # builder 与 media 引用同一个 LoggerManager；Chain 用的是全局 Default logger
    recorder = WarningRecorder()
    monkeypatch.setattr(media_module.log, 'warning', recorder)
    monkeypatch.setattr(chain_module.log, 'warning', recorder)

    return recorder
