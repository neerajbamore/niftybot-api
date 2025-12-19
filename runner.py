import threading
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================== DUMMY HTTP SERVER ==================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"NiftyBot is running")

def start_dummy_server():
    server = HTTPServer(("0.0.0.0", 10000), DummyHandler)
    server.serve_forever()

# ================== SCRIPT RUNNERS ==================
def run_app():
    subprocess.call([sys.executable, "app.py"])

def run_nifty():
    subprocess.call([sys.executable, "nifty_NSE.py"])

# ================== MAIN ==================
if __name__ == "__main__":
    # Start dummy server (for Render free plan)
    threading.Thread(target=start_dummy_server, daemon=True).start()

    # Start both scripts in parallel
    t1 = threading.Thread(target=run_app)
    t2 = threading.Thread(target=run_nifty)

    t1.start()
    t2.start()

    t1.join()
    t2.join()