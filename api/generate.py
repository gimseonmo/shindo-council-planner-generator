from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any

from app import call_gemini


def read_json(request: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(request.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    return json.loads(request.rfile.read(length).decode("utf-8"))


def send_json(request: BaseHTTPRequestHandler, status: int, data: dict[str, Any]) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    request.send_response(status)
    request.send_header("Content-Type", "application/json; charset=utf-8")
    request.send_header("Content-Length", str(len(body)))
    request.end_headers()
    request.wfile.write(body)


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        try:
            data = read_json(self)
            event_name = str(data.get("eventName", "")).strip()
            event_intro = str(data.get("eventIntro", "")).strip()
            if not event_name or not event_intro:
                send_json(self, HTTPStatus.BAD_REQUEST, {"error": "행사 이름과 소개를 입력해주세요."})
                return
            if len(event_name) > 80 or len(event_intro) > 4000:
                send_json(self, HTTPStatus.BAD_REQUEST, {"error": "입력 내용이 너무 깁니다."})
                return

            plan, key_slot = call_gemini(event_name, event_intro)
            send_json(self, HTTPStatus.OK, {"plan": plan, "keySlot": key_slot})
        except json.JSONDecodeError:
            send_json(self, HTTPStatus.BAD_REQUEST, {"error": "요청 형식이 올바르지 않습니다."})
        except Exception as exc:
            send_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
