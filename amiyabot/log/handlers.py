import os
import sys
import logging

from typing import Optional
from concurrent_log_handler import ConcurrentRotatingFileHandler
from amiyabot.util import argv


LOG_FILE_SAVE_PATH = argv('log-file-save-path', str) or './log'
LOG_FILE_MAX_BYTES = argv('log-file-max-bytes', int) or (512 * 1024)
LOG_FILE_BACKUP_COUNT = argv('log-file-backup-count', int) or 10


class LogHandlers:
    debug_mode = argv('debug', bool)
    level = logging.DEBUG if debug_mode else logging.INFO
    formatter = logging.Formatter(f'%(asctime)s [%(name)9s][%(levelname)9s]%(message)s')
    stream_handler: Optional[logging.StreamHandler] = None

    @classmethod
    def get_stream_handler(cls):
        if not cls.stream_handler:
            cls.stream_handler = logging.StreamHandler(stream=sys.stdout)
            cls.stream_handler.setFormatter(cls.formatter)
            cls.stream_handler.setLevel(cls.level)

        return cls.stream_handler

    @classmethod
    def get_file_handler(cls, save_path: str, save_filename: str):
        file_handler = ConcurrentRotatingFileHandler(
            filename=os.path.join(save_path, f'{save_filename}.log'),
            encoding='utf-8',
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT,
        )
        file_handler.setFormatter(cls.formatter)
        file_handler.setLevel(cls.level)

        return file_handler
