import json
import websockets
import dataclasses

from typing import Any, Callable
from dataclasses import dataclass


@dataclass
class GateWay:
    url: str
    shards: int
    session_start_limit: dict


@dataclass
class ConnectionHandler:
    private: bool
    gateway: GateWay
    message_handler: Callable


@dataclass
class ShardsRecord:
    shards_index: int
    session_id: str = None
    last_s: int = None
    reconnect_limit: int = 3
    connection: websockets.WebSocketClientProtocol = None
    heartbeat_key: str = None


@dataclass
class Payload:
    op: int
    id: str = None
    d: Any = None
    s: int = None
    t: str = None

    def to_json(self):
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False)
