import os
import time
import requests
import pyotp
from datetime import datetime
from SmartApi import SmartConnect

# ========== ENV ==========
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

BOT_TOKEN = os.getenv("NIFTY_NSE_BOT")   # same telegram bot
CHAT_ID = os.getenv("CHAT_ID")

INTERVAL_SECONDS = 138  # ~2.3 minutes

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

# ========== ANGEL LOGIN ==========
def angel_login():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj = SmartConnect(api_key=API_KEY)
    obj.generateSession(CLIENT_ID, PASSWORD, totp)
    return obj

# ========== INSTRUMENT MASTER ==========
def load_instruments():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    return requests.get(url, timeout=15).json()

# ========== TOKEN HELPERS ==========
def get_nifty_spot_token(instruments):
    for i in instruments:
        if (
            i.get("name") == "NIFTY"
            and i.get("symbol") == "NIFTY"
            and i.get("exch_seg") == "NSE"
        ):
            return i["token"]
    raise Exception("NIFTY spot token not found")

def get_nifty_fut_token(instruments):
    futs = []
    for i in instruments:
        if (
            i.get("name") == "NIFTY"
            and i.get("instrumenttype") == "FUTIDX"
            and i.get("exch_seg") == "NFO"
        ):
            futs.append(i)

    if not futs:
        raise Exception("No NIFTY futures found")

    futs.sort(key=lambda x: datetime.strptime(x["expiry"], "%d%b%Y"))
    return futs[0]["symbol"], futs[0]["token"]

# ========== LTP ==========
def get_ltp(obj, exchange, symbol, token):
    data = obj.ltpData(exchange, symbol, token)
    return float(data["data"]["ltp"])

# ========== MARKET HOURS ==========
def market_open():
    now = datetime.now().time()
    return (
        now >= datetime.strptime("09:15", "%H:%M").time()
        and now <= datetime.strptime("15:30", "%H:%M").time()
    )

# ========== MAIN ==========
def main():
    send_telegram("🚀 NIFTY Angel bot started (Spot + Future)")

    instruments = load_instruments()
    spot_token = get_nifty_spot_token(instruments)
    fut_symbol, fut_token = get_nifty_fut_token(instruments)

    while True:
        try:
            if market_open():
                obj = angel_login()

                spot = get_ltp(obj, "NSE", "NIFTY", spot_token)
                fut = get_ltp(obj, "NFO", fut_symbol, fut_token)
                premium = round(fut - spot, 2)

                msg = (
                    "📊 NIFTY LIVE (Angel)\n\n"
                    f"Spot   : {spot}\n"
                    f"Future : {fut}\n"
                    f"Premium: {premium}"
                )
                send_telegram(msg)

        except Exception as e:
            send_telegram(f"❌ Angel Error\n{e}")

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()