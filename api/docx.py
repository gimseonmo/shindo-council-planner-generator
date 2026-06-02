from __future__ import annotations

import json
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any

from app import make_docx


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
            title = str(data.get("title", "행사_기획서")).strip()[:120]
            plan = str(data.get("plan", "")).strip()
            if not plan:
                send_json(self, HTTPStatus.BAD_REQUEST, {"error": "기획서 내용이 없습니다."})
                return

            docx = make_docx(title, plan)
            filename = urllib.parse.quote(f"{title or '행사_기획서'}.docx")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(docx)))
            self.end_headers()
            self.wfile.write(docx)
        except json.JSONDecodeError:
            send_json(self, HTTPStatus.BAD_REQUEST, {"error": "요청 형식이 올바르지 않습니다."})
        except Exception as exc:
            send_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
