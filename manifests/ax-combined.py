#!/usr/bin/env python3
"""Receiver for AX task results + static file server for git dumb HTTP.

POST /<name>  -> writes JSON body to data/<name>-<ts>.json  (unchanged)
GET /<path>   -> serves files from ~/ax-sentinel/files      (like :18081)
Listens on 0.0.0.0:18080 so the sandbox needs only ONE allowed destination.
"""
import http.server, json, datetime, os, sys, socketserver

DATA = os.path.expanduser("~/ax-test/data")
os.makedirs(DATA, exist_ok=True)
LOG = os.path.expanduser("~/ax-test/listener.log")
FILES = os.path.expanduser("~/ax-sentinel/files")


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FILES, **kw)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        name = self.path.strip("/") or "result"
        name = "".join(c for c in name if c.isalnum() or c in "-_")
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(DATA, f"{name}-{ts}.json")
        try:
            parsed = json.loads(body)
            with open(path, "w") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=1)
        except Exception:
            with open(path + ".raw", "wb") as f:
                f.write(body)
        with open(LOG, "a") as f:
            f.write(f"{ts} POST {self.path} -> {path} ({n}B)\n")
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok":true}')

    def log_message(self, format, *args):
        pass


class TSrv(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with TSrv(("0.0.0.0", 18080), H) as srv:
        with open(LOG, "a") as f:
            f.write(f"{datetime.datetime.now().isoformat()} combined listener started pid={os.getpid()} files={FILES}\n")
        srv.serve_forever()
