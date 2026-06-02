from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from app import FORM_TEMPLATE, configured_keys


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        page = FORM_TEMPLATE.replace("__CONFIGURED_KEYS__", str(len(configured_keys()))).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)
