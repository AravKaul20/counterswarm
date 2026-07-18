"""Dev helper: accepts POSTed canvas data-URLs and writes JPEGs (for docs)."""
import base64
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers["Content-Length"])
        data = self.rfile.read(n).decode()
        b64 = data.split(",", 1)[1]
        out = sys.argv[1] if len(sys.argv) > 1 else "snap.jpg"
        with open(out, "wb") as f:
            f.write(base64.b64decode(b64))
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"ok")
        print(f"wrote {out} ({n} bytes)", flush=True)

    def log_message(self, *a):
        pass


HTTPServer(("127.0.0.1", 8124), H).serve_forever()
