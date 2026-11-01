"""JSON 响应的 ETag / Cache-Control 辅助：If-None-Match 命中时返回 304。"""
from __future__ import annotations

import hashlib
import json

from fastapi import Request, Response


def encode_payload(payload) -> tuple[bytes, str]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return body, '"' + hashlib.md5(body, usedforsecurity=False).hexdigest() + '"'


def _etag_matches(header: str | None, etag: str) -> bool:
    if not header:
        return False
    candidates = [part.strip() for part in header.split(",")]
    return "*" in candidates or any(c.removeprefix("W/") == etag for c in candidates)


def cached_json_response(request: Request, body: bytes, etag: str,
                         cache_control: str = "public, max-age=60") -> Response:
    headers = {"ETag": etag, "Cache-Control": cache_control}
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)
