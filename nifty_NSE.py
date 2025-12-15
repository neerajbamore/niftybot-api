import os
import time
import requests
import pyotp
from datetime import datetime
from SmartApi import SmartConnect

# ================== ENV ==================
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

BOT_TOKEN = os.getenv("NIFTY_NSE_BOT")   # 👈 tumhara new bot token
CHAT_ID = os.getenv("CHAT_ID")

# ================== TELEGRAM ==================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        }, timeout=5)
    except:
        pass

# ================== ANGEL LOGIN ==================
def angel_login():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj = SmartConnect(api_key=API_KEY)
    obj.generateSession(CLIENT_ID, PASSWORD, totp)
    return obj

# ================== INSTRUMENT MASTER ==================
def load_instruments():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    return requests.get(url).json()

# ================== TOKENS ==================
def get_nifty_spot_token(instruments):
    for i in instruments:
        if i["name"] == "NIFTY" and i["symbol"] == "NIFTY" and i["exch_seg"] == "NSE":
            return i["token"]
    return None

def get_nifty_fut_token(instruments):
    futs = []
    for i in instruments:
        if (
            i["name"] == "NIFTY"
            and i["instrumenttype"] == "FUTIDX"
            and i["exch_seg"] == "NFO"
        ):
            futs.append(i)

    futs.sort(key=lambda x: datetime.strptime(x["expiry"], "%d%b%Y"))
    return futs[0]["symbol"], futs[0]["token"]

# ================== LTP ==================
def get_ltp(obj, exchange, symbol, token):
    data = obj.ltpData(exchange, symbol, token)
    return float(data["data"]["ltp"])

# ================== MARKET HOURS ==================
def market_open():
    now = datetime.now().time()
    return (
        now >= datetime.strptime("09:20", "%H:%M").time()
        and now <= datetime.strptime("15:25", "%H:%M").time()
    )

# ================== JOB ==================
def nifty_job():
    if not market_open():
        return

    try:
        obj = angel_login()
        instruments = load_instruments()

        # Spot
        spot_token = get_nifty_spot_token(instruments)
        spot = get_ltp(obj, "NSE", "NIFTY", spot_token)

        # Future (near expiry)
        fut_symbol, fut_token = get_nifty_fut_token(instruments)
        fut = get_ltp(obj, "NFO", fut_symbol, fut_token)

        premium = round(fut - spot, 2)

        msg = (
            "📊 NIFTY NSE LIVE\n\n"
            f"Spot : {spot}\n"
            f"Future : {fut}\n"
            f"Premium : {premium}"
        )

        send_telegram(msg)

    except Exception as e:
        send_telegram(f"❌ NIFTY NSE Error\n{e}")

# ================== START ==================
send_telegram("🚀 NIFTY NSE bot started")

INTERVAL_SECONDS = 138   # 2.3 minutes

while True:
    nifty_job()
    time.sleep(INTERVAL_SECONDS)