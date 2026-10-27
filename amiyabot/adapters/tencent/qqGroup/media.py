"""QQ 群聊富媒体：框架侧「下载 → 上传」，用于平台下载不到的资源。

平台侧的 URL 上传（`/files` 带 `url`）是由**腾讯服务器**去下载那个地址，
只要图片在内网（私有 IP / 只有内网 DNS 能解析），平台就够不着，
只会返回 ``850026 下载原始文件失败``，用户端什么也收不到。

官方文档给出的替代路径是「先把资源下载到本地，再上传二进制数据」，本模块实现它：

    下载（限时 / 限大小 / 校验 MIME）
        └─ ≤ 5MB   → base64 走 file_data 直传
        └─ ≤ max    → upload_prepare → 分片 PUT → upload_part_finish → 合并
    → file_info → 调用方用 msg_type=7 发出

https://bot.q.qq.com/wiki/develop/api-v2/server-inter/message/rich-media.html
"""

import os
import re
import base64
import hashlib
import asyncio

from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import unquote, urlparse

import aiohttp

from .api import QQGroupAPI, log

INLINE_UPLOAD_LIMIT = 5 * 1024 * 1024
"""官方「直接上传二进制数据」的上限 5MB，超过需走分片上传。"""

MD5_10M_SIZE = 10_002_432
"""`md5_10m` 固定取文件前 10002432 字节（约 9.54MB）的 MD5。"""

DOWNLOAD_CHUNK_SIZE = 64 * 1024

ERROR_UNSUPPORTED_FORMAT = 850019
"""file_type=1 不支持的格式，可降级 file_type=4（按文件发送）。"""

# 下载状态。allow_fallback 为 True 表示「平台侧也许还能救」，由调用方决定是否兜底。
STATUS_OK = 'ok'
STATUS_HTTP_ERROR = 'http_error'
STATUS_TIMEOUT = 'timeout'
STATUS_ERROR = 'error'
STATUS_NOT_IMAGE = 'not_image'
STATUS_TOO_LARGE = 'too_large'

FALLBACK_STATUS = (STATUS_HTTP_ERROR, STATUS_TIMEOUT, STATUS_ERROR)
"""传输层失败（非 200 / 超时 / 连接异常）才兜底回平台侧下载；
内容层面的拒绝（非图片、超出上限）平台同样处理不了，直接放弃。"""

MIME_EXTENSIONS = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/pjpeg': 'jpg',
    'image/gif': 'gif',
    'image/webp': 'webp',
    'image/bmp': 'bmp',
    'image/x-ms-bmp': 'bmp',
    'image/svg+xml': 'svg',
}

GENERIC_MIMES = ('', 'application/octet-stream', 'binary/octet-stream', 'application/unknown')


@dataclass
class MediaFile:
    """下载完成、等待上传的媒体文件。"""

    data: bytes
    mime: str
    name: str

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass
class MediaDownload:
    """下载结果。失败时 `media` 为空，`status` 说明原因。"""

    media: Optional[MediaFile] = None
    status: str = STATUS_OK
    detail: str = ''

    @property
    def ok(self) -> bool:
        return self.media is not None

    @property
    def allow_fallback(self) -> bool:
        return self.status in FALLBACK_STATUS


@dataclass
class UploadResult:
    """上传结果。`file_info` 为空表示失败，`code` / `message` 为 QQ 返回的原始错误。"""

    file_info: Optional[dict] = None
    file_type: int = 1
    code: Optional[int] = None
    message: str = ''

    @property
    def ok(self) -> bool:
        return bool(self.file_info)


def sniff_image_mime(data: bytes) -> str:
    """按文件头判断图片类型，避免把 HTML 错误页当成图片。"""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
    if data.startswith(b'BM'):
        return 'image/bmp'
    return ''


def filename_for(url: str, mime: str) -> str:
    """从 URL 与 MIME 推出带正确扩展名的文件名（QQ 要求 file_name 必须有扩展名）。"""
    stem, ext = os.path.splitext(os.path.basename(unquote(urlparse(url).path or '')))
    ext = MIME_EXTENSIONS.get(mime) or ext.lstrip('.').lower() or 'png'
    stem = re.sub(r'[^0-9A-Za-z_-]+', '_', stem).strip('_')[:32]

    return f'{stem or "image"}.{ext[:8]}'


async def download_media(
    url: str,
    timeout: float = 10.0,
    max_bytes: int = 20 * 1024 * 1024,
    trust_env: bool = False,
) -> MediaDownload:
    """
    下载 `url` 指向的图片。

    :param timeout:   总超时（秒）
    :param max_bytes: 单文件上限，超过直接放弃
    :param trust_env: 是否读取 HTTP_PROXY/NO_PROXY。默认 False ——
                      全局代理会把内网请求劫持成 502，与 MCP 内网地址的坑一致。
    """
    try:
        async with aiohttp.ClientSession(
            trust_env=trust_env,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as session:
            async with session.get(url) as response:
                return await _read_download(response, url, max_bytes)
    except asyncio.TimeoutError:
        log.warning('media download fail url=%s reason=timeout timeout=%s', url, timeout)
        return MediaDownload(status=STATUS_TIMEOUT, detail='timeout')
    except Exception as e:
        log.warning('media download fail url=%s reason=%s: %s', url, type(e).__name__, e)
        return MediaDownload(status=STATUS_ERROR, detail=f'{type(e).__name__}: {e}')


async def _read_download(response, url: str, max_bytes: int) -> MediaDownload:
    if response.status != 200:
        log.warning('media download fail url=%s status=%s', url, response.status)
        return MediaDownload(status=STATUS_HTTP_ERROR, detail=str(response.status))

    data = await _read_limited(response, max_bytes)
    if data is None:
        log.warning('media download fail url=%s reason=too_large limit=%s', url, max_bytes)
        return MediaDownload(status=STATUS_TOO_LARGE, detail=f'>{max_bytes}')

    if not data:
        log.warning('media download fail url=%s reason=empty_body', url)
        return MediaDownload(status=STATUS_HTTP_ERROR, detail='empty body')

    mime = _resolve_mime(response.headers.get('Content-Type', ''), data)
    if not mime.startswith('image/'):
        log.warning('media download fail url=%s reason=not_image content_type=%s', url, mime or '-')
        return MediaDownload(status=STATUS_NOT_IMAGE, detail=mime or 'unknown')

    return MediaDownload(media=MediaFile(data=data, mime=mime, name=filename_for(url, mime)))


async def upload_media(
    api: QQGroupAPI,
    openid: str,
    media: MediaFile,
    file_type: int = 1,
    is_direct: bool = False,
    trust_env: bool = False,
    part_timeout: float = 30.0,
) -> UploadResult:
    """上传已下载的字节，返回 `file_info`。小文件直传，大文件走分片。"""
    if media.size <= INLINE_UPLOAD_LIMIT:
        return await _upload_inline(api, openid, media, file_type, is_direct)

    return await _upload_by_parts(api, openid, media, file_type, is_direct, trust_env, part_timeout)


async def _upload_inline(api: QQGroupAPI, openid: str, media: MediaFile, file_type: int, is_direct: bool):
    res = await api.upload_file(
        openid,
        file_type,
        None,
        is_direct=is_direct,
        file_name=media.name,
        file_data=base64.b64encode(media.data).decode('ascii'),
    )

    return _parse_upload(res, media, file_type)


async def _upload_by_parts(
    api: QQGroupAPI,
    openid: str,
    media: MediaFile,
    file_type: int,
    is_direct: bool,
    trust_env: bool,
    part_timeout: float,
):
    prepare = await api.upload_prepare(
        openid,
        file_type,
        media.size,
        media.name,
        hashlib.md5(media.data).hexdigest(),
        hashlib.sha1(media.data).hexdigest(),
        hashlib.md5(media.data[:MD5_10M_SIZE]).hexdigest(),
        is_direct=is_direct,
    )

    body = _body_of(prepare)
    upload_id = body.get('upload_id')
    parts = body.get('parts') or []

    if not upload_id or not parts:
        code, message = _parse_error(prepare, body)
        log.warning(
            'media upload fail (upload_prepare) name=%s bytes=%s code=%s message=%s',
            media.name,
            media.size,
            code or '-',
            message or '-',
        )
        return UploadResult(file_type=file_type, code=code, message=message or 'upload_prepare failed')

    block_size = _to_int(body.get('block_size')) or INLINE_UPLOAD_LIMIT
    offset = 0

    for part in sorted(parts, key=lambda item: _to_int(item.get('index'))):
        index = _to_int(part.get('index'))
        presigned = part.get('presigned_url') or part.get('url')
        chunk = media.data[offset : offset + (_to_int(part.get('block_size')) or block_size)]
        offset += len(chunk)

        if not presigned or not chunk:
            log.warning('media upload fail (invalid part) name=%s index=%s', media.name, index)
            return UploadResult(file_type=file_type, message=f'invalid part {index}')

        if not await _put_part(presigned, chunk, trust_env, part_timeout):
            log.warning('media upload fail (part put) name=%s index=%s bytes=%s', media.name, index, len(chunk))
            return UploadResult(file_type=file_type, message=f'part {index} put failed')

        finish = await api.upload_part_finish(
            openid,
            upload_id,
            index,
            block_size=len(chunk),
            md5=hashlib.md5(chunk).hexdigest(),
            is_direct=is_direct,
        )

        finish_body = _body_of(finish)
        if _to_int(finish_body.get('code'), 0) != 0 or finish_body.get('err_code'):
            code, message = _parse_error(finish, finish_body)
            log.warning(
                'media upload fail (part finish) name=%s index=%s code=%s message=%s',
                media.name,
                index,
                code or '-',
                message or '-',
            )
            return UploadResult(file_type=file_type, code=code, message=message)

    res = await api.upload_file(
        openid,
        file_type,
        None,
        is_direct=is_direct,
        file_name=media.name,
        upload_id=upload_id,
    )

    return _parse_upload(res, media, file_type)


async def _put_part(url: str, chunk: bytes, trust_env: bool, timeout: float, retry: int = 1) -> bool:
    for attempt in range(retry + 1):
        try:
            async with aiohttp.ClientSession(
                trust_env=trust_env,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as session:
                async with session.put(url, data=chunk) as response:
                    if response.status in (200, 201, 204):
                        return True
                    log.warning(
                        'media part put fail status=%s bytes=%s attempt=%s',
                        response.status,
                        len(chunk),
                        attempt + 1,
                    )
        except Exception as e:
            log.warning('media part put fail reason=%s: %s attempt=%s', type(e).__name__, e, attempt + 1)

        if attempt < retry:
            await asyncio.sleep(1)

    return False


async def _read_limited(response: aiohttp.ClientResponse, max_bytes: int) -> Optional[bytes]:
    """按块读取并限制总大小，超限返回 None（避免把 200MB 的内容读进内存）。"""
    if response.content_length and response.content_length > max_bytes:
        return None

    chunks: List[bytes] = []
    total = 0

    async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
        total += len(chunk)
        if total > max_bytes:
            return None
        chunks.append(chunk)

    return b''.join(chunks)


def _resolve_mime(content_type: str, data: bytes) -> str:
    mime = (content_type or '').split(';')[0].strip().lower()

    if mime in GENERIC_MIMES:
        return sniff_image_mime(data)

    return mime


def _body_of(response) -> dict:
    body = getattr(response, 'json', None)

    return body if isinstance(body, dict) else {}


def _parse_upload(response, media: MediaFile, file_type: int) -> UploadResult:
    body = _body_of(response)

    if body.get('file_info'):
        log.debug(f'media upload success name={media.name} bytes={media.size} ttl={body.get("ttl", "-")}')
        return UploadResult(file_info=body['file_info'], file_type=file_type)

    code, message = _parse_error(response, body)
    log.warning(
        'media upload fail name=%s bytes=%s file_type=%s code=%s message=%s',
        media.name,
        media.size,
        file_type,
        code or '-',
        message or '-',
    )

    return UploadResult(file_type=file_type, code=code, message=message)


def _parse_error(response, body: dict) -> Tuple[Optional[int], str]:
    """取 QQ 返回的业务错误码与描述，取不到时退回响应原文 / 传输层异常。"""
    if body:
        code = body.get('code', body.get('err_code'))
        message = body.get('message') or body.get('msg') or body.get('err_msg') or ''

        return _to_int(code, None), str(message)

    error = getattr(response, 'error', None)
    if error:
        return None, f'{type(error).__name__}: {error}'

    text = getattr(response, 'text', '') or ''

    return None, text[:200]


def _to_int(value, default: Optional[int] = 0) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
