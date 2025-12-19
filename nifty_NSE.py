import os
import time
import requests
from datetime import datetime

# ========== TELEGRAM ENV ==========
BOT_TOKEN = os.getenv("NIFTY_NSE_BOT")
CHAT_ID = os.getenv("CHAT_ID")

INTERVAL_SECONDS = 180  # 3 minutes (test)

# ========== TELEGRAM ==========
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)

# ========== NSE SESSION ==========
def get_nse_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com",
        "Connection": "keep-alive"
    })
    # First hit to set cookies
    session.get("https://www.nseindia.com", timeout=10)
    return session

# ========== FETCH NIFTY ==========
def get_nifty_spot():
    session = get_nse_session()
    url = "https://www.nseindia.com/api/allIndices"

    r = session.get(url, timeout=10)

    if r.status_code != 200:
        raise Exception(f"NSE HTTP {r.status_code}")

    data = r.json()

    for idx in data.get("data", []):
        if idx.get("index") == "NIFTY 50":
            return round(idx.get("last", 0), 2)

    raise Exception("NIFTY 50 not found in NSE response")

# ========== MAIN ==========
def main():
    send_telegram("🧪 NSE TEST MODE STARTED")

    while True:
        try:
            nifty = get_nifty_spot()
            send_telegram(
                f"🧪 NSE TEST\n"
                f"Time : {datetime.now().strftime('%H:%M:%S')}\n"
                f"NIFTY 50 : {nifty}"
            )
        except Exception as e:
            send_telegram(
                f"❌ NSE TEST ERROR\n"
                f"Time : {datetime.now().strftime('%H:%M:%S')}\n"
                f"{e}"
            )

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()