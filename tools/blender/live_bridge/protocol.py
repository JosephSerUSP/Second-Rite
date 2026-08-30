"""Wire-level helpers shared by the Blender server and ordinary Python client."""

from __future__ import annotations

import json
import math
import time

MAX_MESSAGE_BYTES = 1024 * 1024
PROTOCOL_VERSION = 1


class ProtocolError(ValueError):
    pass


def encode_message(value: dict) -> bytes:
    payload = json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message exceeds 1 MiB limit")
    return payload + b"\n"


def decode_message(line: bytes) -> dict:
    if len(line) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message exceeds 1 MiB limit")
    try:
        value = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ProtocolError("message must be a JSON object")
    return value


def validate_request(value: dict) -> tuple[object, str, dict, str, float]:
    unknown = set(value) - {"id", "version", "method", "params", "token", "timestamp"}
    if unknown:
        raise ProtocolError(f"unknown request fields: {', '.join(sorted(unknown))}")
    request_id = value.get("id")
    method = value.get("method")
    params = value.get("params", {})
    token = value.get("token")
    timestamp = value.get("timestamp")
    version = value.get("version", PROTOCOL_VERSION)
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version {version!r}")
    if request_id is None or isinstance(request_id, (dict, list, bool)):
        raise ProtocolError("request.id must be a string or number")
    if isinstance(request_id, float) and not math.isfinite(request_id):
        raise ProtocolError("request.id must be finite")
    if not isinstance(method, str) or not method:
        raise ProtocolError("request.method must be a non-empty string")
    if not isinstance(params, dict):
        raise ProtocolError("request.params must be an object")
    if not isinstance(token, str) or not token:
        raise ProtocolError("request.token is required")
    if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool) or not math.isfinite(timestamp):
        raise ProtocolError("request.timestamp must be a finite Unix timestamp")
    if abs(time.time() - float(timestamp)) > 300:
        raise ProtocolError("request.timestamp is outside the five-minute acceptance window")
    return request_id, method, params, token, float(timestamp)
