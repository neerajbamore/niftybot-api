import os
import time
import requests
import pyotp
from datetime import datetime
from SmartApi import SmartConnect

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

BOT_TOKEN = os.getenv("BOT_TOKEN")   # dusra telegram bot
CHAT_ID = os.getenv("CHAT_ID")

# ---------- TELEGRAM ----------
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

# ---------- ANGEL LOGIN ----------
def angel_login():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj = SmartConnect(api_key=API_KEY)
    obj.generateSession(CLIENT_ID, PASSWORD, totp)
    return obj

# ---------- MARKET HOURS ----------
def market_open():
    now = datetime.now().time()
    return (
        now >= datetime.strptime("09:20", "%H:%M").time()
        and now <= datetime.strptime("15:25", "%H:%M").time()
    )

# ---------- MAIN ----------
def main():
    send_telegram("🤖 Angel API worker started")

    while True:
        try:
            if market_open():
                obj = angel_login()
                # future me yahin FUT / OI / options ka code aayega
                send_telegram("📡 Angel API connected (placeholder)")
        except Exception as e:
            send_telegram(f"❌ Angel Error\n{e}")

        time.sleep(300)

if __name__ == "__main__":
    main()