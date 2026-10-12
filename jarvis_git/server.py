"""Jarvis web UI server (stdlib only, no extra dependencies).

Serves ./web and issues short-lived LiveKit tokens at /token.
LiveKit secrets stay in .env on the server and never reach the browser.
Run:  python server.py   ->  http://127.0.0.1:8080
"""
import json, os, secrets
from datetime import timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from dotenv import load_dotenv
from livekit import api

load_dotenv()
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?")[0] != "/token":
            return super().do_GET()
        key, secret, url = (os.getenv(k) for k in ("LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL"))
        if not (key and secret and url):
            return self._json(500, {"error": "LIVEKIT_API_KEY, LIVEKIT_API_SECRET and LIVEKIT_URL must be set in .env"})
        room = "jarvis-" + secrets.token_hex(4)  # new room => agent worker is auto-dispatched
        token = (api.AccessToken(key, secret)
                 .with_identity("user-" + secrets.token_hex(3))
                 .with_ttl(timedelta(hours=1))
                 .with_grants(api.VideoGrants(room_join=True, room=room))
                 .to_jwt())
        self._json(200, {"url": url, "token": token, "room": room})

    def log_message(self, *a):  # keep console quiet
        pass


if __name__ == "__main__":
    port = int(os.getenv("JARVIS_UI_PORT", "8080"))
    print(f"Jarvis UI -> http://127.0.0.1:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
