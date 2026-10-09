#!/usr/bin/env python3
"""W22 quota-proxy (E3 night runner): drill quota-failover modelu A.

Slucha na :18090 (serv2). Zadanie:
  - model A (gemini-3.8-flash) -> ALWAYS 429 + Retry-After: 1 (RESOURCE_EXHAUSTED)
  - kazdy inny model -> forward na https://generativelanguage.googleapis.com
    (autoryzacja ?key= przechodzi w query stringu bez zmian)

Kazde zadanie logowane do ~/ax-test/quota-proxy.log jako "<code> <METHOD> <path>".
Gate W22 w night.py: log musi zawierac 429 (model A) ORAZ 200 (fallback).
"""
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

UPSTREAM = "https://generativelanguage.googleapis.com"
THROTTLED = {"gemini-3.8-flash"}  # model A drillu (W22)
LOG = "/home/hermes/ax-test/quota-proxy.log"


class H(BaseHTTPRequestHandler):

    def _log(self, code: int) -> None:
        path = self.path.split("?")[0]  # NIGDY nie loguj ?key=... (sekret!)
        with open(LOG, "a") as f:
            f.write(f"{code} {self.command} {path}\n")

    def _proxy(self) -> None:
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        model = ""
        if "/models/" in self.path:
            model = self.path.split("/models/")[-1].split(":")[0]
        if model in THROTTLED:
            self._log(429)
            payload = json.dumps({"error": {
                "code": 429, "status": "RESOURCE_EXHAUSTED",
                "message": "quota proxy (W22 drill): model A throttled"}}).encode()
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.send_header("Retry-After", "1")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        req = urllib.request.Request(UPSTREAM + self.path, data=body,
                                     headers={"Content-Type": "application/json"},
                                     method=self.command)
        try:
            r = urllib.request.urlopen(req, timeout=180)
            data, code = r.read(), r.status
        except urllib.error.HTTPError as e:
            data, code = e.read(), e.code
        self._log(code)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = _proxy
    do_POST = _proxy

    def log_message(self, format, *args):  # noqa: A002 — stdout cichy, log do pliku
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 18090), H).serve_forever()
