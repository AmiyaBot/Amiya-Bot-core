import time
import shutil

from graiax import silkcoder
from amiyahttp import HttpServer, ServerConfig
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from amiyautils import create_dir, get_public_ip, random_code
from amiyabot.adapters import MessageCallback
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *
from typing import Dict, Tuple

from .api import QQGroupAPI, log
from .media import ERROR_UNSUPPORTED_FORMAT, MediaDownload, download_media, upload_media


class SeqService:
    def __init__(self):
        self.seq_rec = {}
        self.alive = False

    def msg_req(self, msg_id: str):
        if msg_id not in self.seq_rec:
            self.seq_rec[msg_id] = {'last': time.time(), 'seq': 0}

        self.seq_rec[msg_id]['seq'] += 1

        return self.seq_rec[msg_id]['seq']

    async def run(self):
        if not self.alive:
            self.alive = True

            while self.alive:
                await asyncio.sleep(1)
                self.seq_rec = {m_id: item for m_id, item in self.seq_rec.items() if time.time() - item['last'] < 300}

    async def stop(self):
        self.alive = False


class PortSingleton(type):
    ports = {}

    def __call__(cls, *args, **kwargs):
        options: QQGroupChainBuilderOptions = args[0]

        if options.port not in cls.ports:
            cls.ports[options.port] = super(PortSingleton, cls).__call__(*args, **kwargs)

        return cls.ports[options.port]


@dataclass
class GroupPayload:
    content: str = ''
    msg_type: int = 0
    markdown: Optional[dict] = None
    keyboard: Optional[dict] = None
    media: Optional[dict] = None
    ark: Optional[dict] = None
    image: Optional[str] = None
    message_reference: Optional[dict] = None
    event_id: Optional[str] = None
    msg_id: Optional[str] = None
    msg_seq: Optional[int] = None


DEFAULT_MEDIA_DOWNLOAD_TIMEOUT = 10.0
DEFAULT_MEDIA_MAX_BYTES = 20 * 1024 * 1024


@dataclass
class QQGroupChainBuilderOptions:
    host: str = '0.0.0.0'
    port: int = 8086
    resource_path: str = './resource'
    server_config: ServerConfig = field(default_factory=ServerConfig)

    download_media: bool = False
    """True 时，http(s) 图片先由框架下载再上传（适用于内网地址）；False 保持现状（平台侧下载）。"""

    media_download_timeout: float = DEFAULT_MEDIA_DOWNLOAD_TIMEOUT
    """下载超时（秒）。内网图床通常很快，10s 足够。"""

    media_max_bytes: int = DEFAULT_MEDIA_MAX_BYTES
    """单文件上限，超过直接跳过（图片官方软限制 20MB）。"""

    media_trust_env: bool = False
    """下载时是否读取 HTTP_PROXY/NO_PROXY。默认 False —— 全局代理会把内网请求劫持成 502。"""


class QQGroupChainBuilder(ChainBuilder, metaclass=PortSingleton):
    def __init__(self, options: QQGroupChainBuilderOptions):
        create_dir(options.resource_path)

        self.server = HttpServer(options.host, options.port, options.server_config)
        self.server.add_static_folder('/resource', options.resource_path)

        self.ip = options.host if options.host != '0.0.0.0' else get_public_ip()
        self.http = 'https' if self.server.server.config.is_ssl else 'http'
        self.options = options

        self.file_caches = {}

        self.running = False

    @property
    def domain(self):
        return f'{self.http}://{self.ip}:{self.options.port}/resource'

    def start(self):
        if not self.running:
            asyncio.create_task(self.server.serve())
        self.running = True

    def temp_filename(self, suffix: str):
        filename = f'{int(time.time())}{random_code(10)}.{suffix}'
        path = f'{self.options.resource_path}/{filename}'
        url = f'{self.domain}/{filename}'

        create_dir(path, is_file=True)

        self.file_caches[url] = path

        return path, url

    def remove_file(self, url: str):
        if url in self.file_caches:
            os.remove(self.file_caches[url])
            del self.file_caches[url]

    async def get_image(self, image: Union[str, bytes]) -> Union[str, bytes]:
        if isinstance(image, bytes):
            path, url = self.temp_filename('png')

            with open(path, mode='wb') as f:
                f.write(image)

            return url
        return image

    async def get_voice(self, voice_file: str) -> str:
        if voice_file.startswith('http'):
            return voice_file

        voice = await silkcoder.async_encode(voice_file, ios_adaptive=True)
        path, url = self.temp_filename('silk')

        with open(path, mode='wb') as f:
            f.write(voice)

        return url

    async def get_video(self, video_file: str) -> str:
        if video_file.startswith('http'):
            return video_file

        path, url = self.temp_filename('mp4')
        shutil.copy(video_file, path)
        return url


class QQGroupMessageCallback(MessageCallback):
    async def recall(self):
        if not self.response:
            log.warning('can not recall message because the response is None.')
            return False

        res = self.response.json
        message_id = res.get('id')
        if not message_id:
            return False

        api: QQGroupAPI = self.instance.api

        if self.data.is_direct:
            return await api.delete_private_message(self.data.user_openid, message_id)
        return await api.delete_group_message(self.data.channel_openid, message_id)

    async def get_message(self):
        # 群聊/单聊暂未提供按 ID 获取消息的接口
        return None


class PayloadBuilder:
    def __init__(self, api: QQGroupAPI, chain: Chain, seq_service: SeqService):
        self.api = api
        self.chain = chain
        self.seq_service = seq_service

        self.chain_list = chain.chain
        self.msg_id = chain.data.message_id

        # 引用回复：chain.reference=True 时携带 message_reference。
        # 被引用消息索引来自 message_scene.ext 的 msg_idx（非机器人消息）。
        self.message_reference = None
        reference_id = getattr(chain.data, 'reference_message_id', '')
        if chain.reference and reference_id:
            self.message_reference = {'message_id': reference_id}

        self.payload_list: List[GroupPayload] = []
        self.payload = self.__new_payload()

        # 同一 payload（同一条 Chain）内重复的 URL 只上传一次：url -> (file_info, file_type)
        self.media_cache: Dict[str, Tuple[dict, int]] = {}

    def __new_payload(self):
        payload = GroupPayload(msg_id=self.msg_id, msg_seq=self.seq_service.msg_req(self.msg_id))
        if self.message_reference:
            payload.message_reference = self.message_reference
        return payload

    def refresh_payload(self, safe: bool = False):
        if not safe or self.payload.content:
            self.payload_list.append(self.payload)

        self.payload = self.__new_payload()

    @contextmanager
    def lone_payload(self):
        self.refresh_payload(True)
        yield
        self.refresh_payload()

    @property
    def openid(self) -> str:
        """单聊取用户 openid，群聊取群 openid（两类接口互相隔离，不能混用）。"""
        return self.chain.data.user_openid if self.chain.data.is_direct else self.chain.data.channel_openid

    @property
    def media_options(self) -> Optional[QQGroupChainBuilderOptions]:
        return getattr(self.chain.builder, 'options', None)

    def __download_enabled(self, download: Optional[bool], file_type: int) -> bool:
        # 只有图片走「框架下载」；语音/视频/文件维持平台侧下载
        if file_type != 1:
            return False

        if download is not None:
            return download

        options = self.media_options
        return bool(options and options.download_media)

    async def __resolve_by_download(self, url: str) -> Tuple[Optional[dict], int, bool]:
        """
        下载并由框架上传，返回 (file_info, 实际 file_type, 是否允许兜底)。
        没有 file_info 时由调用方决定「兜底回平台侧下载」还是「直接放弃」。
        """
        if url in self.media_cache:
            file_info, file_type = self.media_cache[url]
            return file_info, file_type, False

        options = self.media_options
        trust_env = options.media_trust_env if options else False

        timeout = options.media_download_timeout if options else DEFAULT_MEDIA_DOWNLOAD_TIMEOUT
        max_bytes = options.media_max_bytes if options else DEFAULT_MEDIA_MAX_BYTES

        cached_media: MediaDownload = await download_media(
            url,
            timeout=timeout,
            max_bytes=max_bytes,
            trust_env=trust_env,
        )

        if not cached_media.media:
            return None, 1, cached_media.allow_fallback

        result = await upload_media(
            self.api,
            self.openid,
            cached_media.media,
            file_type=1,
            is_direct=self.chain.data.is_direct,
            trust_env=trust_env,
        )

        if not result.ok and result.code == ERROR_UNSUPPORTED_FORMAT:
            # file_type=1 官方只保证 png/jpg，其余格式降级为「按文件发送」
            log.warning('media upload downgrade to file_type=4 url=%s code=%s', url, result.code)
            result = await upload_media(
                self.api,
                self.openid,
                cached_media.media,
                file_type=4,
                is_direct=self.chain.data.is_direct,
                trust_env=trust_env,
            )

        if result.ok:
            self.media_cache[url] = (result.file_info, result.file_type)
            return result.file_info, result.file_type, False

        # 上传失败：公网图仍可能被平台侧救回来，允许兜底
        return None, 1, True

    def __append_media(self, file_info: dict, file_type: int = 1):
        # 非图片（语音 / 视频 / 文件）需独占一条消息，先把已累积的文本冲刷出去。
        # safe=True：没有文本时不再追加空 payload。
        if file_type != 1:
            self.refresh_payload(True)

        self.payload.msg_type = 7
        self.payload.media = {'file_info': file_info}

        self.refresh_payload()

    async def insert_media(self, url: str, file_type: int = 1, download: Optional[bool] = None):
        if not isinstance(url, str):
            log.warning(f'unsupported file type "{type(url)}".')
            return

        if not url.startswith('http'):
            log.warning(f'media file must be network paths.')
            return

        try:
            if self.__download_enabled(download, file_type):
                file_info, effective_type, allow_fallback = await self.__resolve_by_download(url)

                if file_info:
                    self.__append_media(file_info, effective_type)
                    return

                if not allow_fallback:
                    # 内容层面被拒（非图片 / 超出上限）或上传失败已记录日志，不再重复请求
                    return

                log.warning('media fallback to platform upload url=%s', url)

            res = await self.api.upload_file(
                self.openid,
                file_type,
                url,
                is_direct=self.chain.data.is_direct,
            )

            body = res.json if res else None

            if isinstance(body, dict) and body.get('file_info'):
                self.__append_media(body['file_info'], file_type)
            else:
                log.warning(
                    'file upload fail url=%s code=%s message=%s',
                    url,
                    body.get('code', '-') if isinstance(body, dict) else '-',
                    body.get('message', '-') if isinstance(body, dict) else (getattr(res, 'text', '') or '-'),
                )
        finally:
            # 无论走哪条路径，本地临时文件都已用完（远程 URL 不在缓存里，是空操作）
            if isinstance(self.chain.builder, QQGroupChainBuilder):
                self.chain.builder.remove_file(url)

    async def build(self):
        for item in self.chain_list:
            # At
            # QQ 群官方语法：<@user_openid>
            if isinstance(item, At):
                self.payload.content += f'<@{item.target}>'

            # AtAll
            if isinstance(item, AtAll):
                self.payload.content += '<@everyone>'

            # Text
            if isinstance(item, Text):
                self.payload.content += item.content

            # Image
            if isinstance(item, Image):
                await self.insert_media(await item.get(), download=item.download)

            # Voice
            if isinstance(item, Voice):
                await self.insert_media(await item.get(), 3)

            # Video
            if isinstance(item, Video):
                await self.insert_media(await item.get(), 2)

            # Html
            if isinstance(item, Html):
                await self.insert_media(await item.create_html_image())

            # Ark
            if isinstance(item, Ark):
                with self.lone_payload():
                    self.payload.msg_type = 3
                    self.payload.ark = item.get()['ark']

            # Markdown
            if isinstance(item, Markdown):
                with self.lone_payload():
                    md = item.get()

                    self.payload.msg_type = 2
                    self.payload.markdown = md['markdown']
                    if 'keyboard' in md:
                        self.payload.keyboard = md['keyboard']

            # Markdown（自定义内容，无需申请模版）
            if isinstance(item, MarkdownContent):
                with self.lone_payload():
                    md = item.get()

                    self.payload.msg_type = 2
                    self.payload.markdown = md['markdown']
                    if 'keyboard' in md:
                        self.payload.keyboard = md['keyboard']

        if self.payload.content:
            self.payload_list.append(self.payload)

        return [asdict(item) for item in self.payload_list]


async def build_message_send(api: QQGroupAPI, chain: Chain, seq_service: SeqService):
    return await PayloadBuilder(api, chain, seq_service).build()
