import os
import time
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")   # agar dusra bot hai
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    if not BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=5
        )
    except:
        pass

def main():
    send_telegram("🤖 app.py worker started")

    while True:
        now = datetime.now().strftime("%H:%M:%S")
        # sirf heartbeat, future me yahin dusra logic ayega
        print(f"[app.py] running @ {now}")
        time.sleep(300)   # 5 min

if __name__ == "__main__":
    main()