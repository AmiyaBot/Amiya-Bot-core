import time
import shutil

from graiax import silkcoder
from dataclasses import asdict, field
from amiyabot.util import create_dir, get_public_ip, random_code, Singleton
from amiyabot.adapters import MessageCallback
from amiyabot.network.httpServer import HttpServer
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *

from .api import QQGroupAPI, log


class SeqService:
    def __init__(self):
        self.seq_rec = {}
        self.alive = True

    def msg_req(self, msg_id: str):
        if msg_id not in self.seq_rec:
            self.seq_rec[msg_id] = {'last': time.time(), 'seq': 0}

        self.seq_rec[msg_id]['seq'] += 1

        return self.seq_rec[msg_id]['seq']

    async def run(self):
        while self.alive:
            await asyncio.sleep(1)
            self.seq_rec = {m_id: item for m_id, item in self.seq_rec.items() if time.time() - item['last'] < 30}

    async def stop(self):
        self.alive = False


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


@dataclass
class QQGroupChainBuilderOptions:
    host: str = '0.0.0.0'
    port: int = 8086
    resource_path: str = './resource'
    http_server_options: dict = field(default_factory=dict)


class QQGroupChainBuilder(ChainBuilder, metaclass=Singleton):
    def __init__(self, options: QQGroupChainBuilderOptions):
        create_dir(options.resource_path)

        self.server = HttpServer(options.host, options.port, **options.http_server_options)
        self.server.add_static_folder('/resource', options.resource_path)

        self.ip = options.host if options.host != '0.0.0.0' else get_public_ip()
        self.http = 'https' if self.server.server.config.is_ssl else 'http'
        self.options = options

        self.file_caches = {}

    @property
    def domain(self):
        return f'{self.http}://{self.ip}:{self.options.port}/resource'

    def start(self):
        asyncio.create_task(self.server.serve())

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
        voice = await silkcoder.async_encode(voice_file, ios_adaptive=True)
        path, url = self.temp_filename('silk')

        with open(path, mode='wb') as f:
            f.write(voice)

        return url

    async def get_video(self, video_file: str) -> str:
        path, url = self.temp_filename('mp4')
        shutil.copy(video_file, path)
        return url


class QQGroupMessageCallback(MessageCallback):
    async def recall(self):
        ...

    async def get_message(self):
        ...


async def build_message_send(api: QQGroupAPI, chain: Chain, seq_service: SeqService):
    chain_list = chain.chain
    msg_id = chain.data.message_id

    payload_list: List[GroupPayload] = []
    payload = GroupPayload(msg_id=msg_id, msg_seq=seq_service.msg_req(msg_id))

    async def insert_media(url: str, file_type: int = 1):
        nonlocal payload

        if not isinstance(url, str):
            log.warning(f'unsupported file type "{type(url)}".')
            return

        if url.startswith('http'):
            res = await api.upload_file(chain.data.channel_openid, file_type, url)
            if res:
                if 'file_info' in res.json:
                    file_info = res.json['file_info']

                    payload.msg_type = 7
                    payload.media = {'file_info': file_info}

                    payload_list.append(payload)
                    payload = GroupPayload(msg_id=msg_id, msg_seq=seq_service.msg_req(msg_id))
                else:
                    log.warning('file upload fail.')

            if isinstance(chain.builder, QQGroupChainBuilder):
                chain.builder.remove_file(url)
        else:
            log.warning(f'media file must be network paths.')

    for item in chain_list:
        # Text
        if isinstance(item, Text):
            payload.content += item.content

        # Image
        if isinstance(item, Image):
            await insert_media(await item.get())

        # Voice
        if isinstance(item, Voice):
            await insert_media(await item.get(), 3)

        # Video
        if isinstance(item, Video):
            await insert_media(await item.get(), 2)

        # Html
        if isinstance(item, Html):
            await insert_media(await item.create_html_image())

    if payload.content:
        payload_list.append(payload)

    return [asdict(item) for item in payload_list]
