import threading
import subprocess
import sys

def run_app():
    subprocess.call([sys.executable, "app.py"])

def run_nifty():
    subprocess.call([sys.executable, "nifty_NSE.py"])

t1 = threading.Thread(target=run_app)
t2 = threading.Thread(target=run_nifty)

t1.start()
t2.start()

t1.join()
t2.join()