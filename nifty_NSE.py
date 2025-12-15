import os
import time
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("NIFTY_NSE_BOT")
CHAT_ID = os.getenv("CHAT_ID")

INTERVAL_SECONDS = 138  # 2.3 minutes

# ---------- TELEGRAM ----------
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=5
        )
    except:
        pass

# ---------- NSE SESSION ----------
def get_nse_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com"
    })
    session.get("https://www.nseindia.com", timeout=5)
    return session

# ---------- FETCH NIFTY ----------
def get_nifty_spot():
    session = get_nse_session()
    url = "https://www.nseindia.com/api/allIndices"
    data = session.get(url, timeout=5).json()

    for idx in data["data"]:
        if idx["index"] == "NIFTY 50":
            return round(idx["last"], 2)
    return None

# ---------- MARKET HOURS ----------
def market_open():
    now = datetime.now().time()
    return (
        now >= datetime.strptime("09:15", "%H:%M").time()
        and now <= datetime.strptime("15:30", "%H:%M").time()
    )

# ---------- MAIN ----------
def main():
    send_telegram("🚀 NIFTY NSE (Direct) bot started")

    while True:
        try:
            if market_open():
                nifty = get_nifty_spot()
                if nifty:
                    send_telegram(
                        f"📊 NIFTY 50 (NSE)\n\nSpot : {nifty}"
                    )
        except Exception as e:
            send_telegram(f"❌ NSE Error\n{e}")

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()