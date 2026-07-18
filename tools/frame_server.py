"""Dev helper: accepts POSTed canvas data-URLs, saves sequential JPEG frames."""
import base64
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

os.makedirs("results/frames", exist_ok=True)
counter = 0


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        global counter
        data = self.rfile.read(int(self.headers["Content-Length"])).decode()
        with open(f"results/frames/frame_{counter:03d}.jpg", "wb") as f:
            f.write(base64.b64decode(data.split(",", 1)[1]))
        counter += 1
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(str(counter).encode())

    def log_message(self, *a):
        pass


print("frame server on 8124", flush=True)
HTTPServer(("127.0.0.1", 8124), H).serve_forever()
