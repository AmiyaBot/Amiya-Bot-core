import json
import websockets
import dataclasses

from typing import Any, Callable, Optional
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
    session_id: Optional[str] = None
    last_s: Optional[int] = None
    reconnect_limit: int = 3
    connection: Optional[websockets.WebSocketClientProtocol] = None
    heartbeat_key: Optional[str] = None


@dataclass
class Payload:
    op: int
    id: Optional[str] = None
    d: Optional[Any] = None
    s: Optional[int] = None
    t: Optional[str] = None

    def to_json(self):
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False)
