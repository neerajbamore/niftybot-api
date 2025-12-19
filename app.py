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

BOT_TOKEN = os.getenv("NIFTY_NSE_BOT")
CHAT_ID = os.getenv("CHAT_ID")

INTERVAL_SECONDS = 120  # 2 min test

# ========== TELEGRAM ==========
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ========== ANGEL LOGIN ==========
def angel_login():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj = SmartConnect(api_key=API_KEY)
    data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
    return obj, data

# ========== LOAD INSTRUMENTS ==========
def load_instruments():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    return requests.get(url, timeout=20).json()

# ========== TOKENS ==========
def get_nifty_spot_token(instruments):
    for i in instruments:
        if i["name"] == "NIFTY" and i["symbol"] == "NIFTY" and i["exch_seg"] == "NSE":
            return i["token"]
    raise Exception("NIFTY spot token not found")

def get_nifty_fut_token(instruments):
    futs = []
    for i in instruments:
        if i["name"] == "NIFTY" and i["instrumenttype"] == "FUTIDX":
            futs.append(i)

    futs.sort(key=lambda x: datetime.strptime(x["expiry"], "%d%b%Y"))
    return futs[0]["symbol"], futs[0]["token"]

# ========== LTP ==========
def get_ltp(obj, exch, sym, token):
    data = obj.ltpData(exch, sym, token)
    return float(data["data"]["ltp"])

# ========== MAIN ==========
def main():
    send_telegram("🧪 Angel DEBUG MODE STARTED")

    instruments = load_instruments()
    spot_token = get_nifty_spot_token(instruments)
    fut_symbol, fut_token = get_nifty_fut_token(instruments)

    while True:
        try:
            obj, session = angel_login()

            spot = get_ltp(obj, "NSE", "NIFTY", spot_token)
            fut = get_ltp(obj, "NFO", fut_symbol, fut_token)

            premium = round(fut - spot, 2)

            send_telegram(
                "🧪 ANGEL TEST\n\n"
                f"Spot   : {spot}\n"
                f"Future : {fut}\n"
                f"Premium: {premium}"
            )

        except Exception as e:
            send_telegram(f"❌ ANGEL ERROR\n{e}")

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()