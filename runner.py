import threading
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Nifty Angel Bot Running")

def start_dummy_server():
    server = HTTPServer(("0.0.0.0", 10000), DummyHandler)
    server.serve_forever()

def run_bot():
    subprocess.call([sys.executable, "app.py"])

if __name__ == "__main__":
    threading.Thread(target=start_dummy_server, daemon=True).start()
    run_bot()