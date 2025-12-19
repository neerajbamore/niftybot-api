import os
import time
import math
import sqlite3
import requests
import pyotp
from datetime import datetime
from SmartApi import SmartConnect

# ================== ENV ==================
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

BOT_TOKEN = os.getenv("NIFTY_NSE_BOT")
CHAT_ID = os.getenv("CHAT_ID")

INTERVAL_SECONDS = 138  # ~2.3 min
DB_FILE = "oi_snapshot.db"

# ================== TELEGRAM ==================
def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

# ================== ANGEL LOGIN ==================
def angel_login():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj = SmartConnect(api_key=API_KEY)
    obj.generateSession(CLIENT_ID, PASSWORD, totp)
    return obj

# ================== DB ==================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS snapshot (
            symbol TEXT PRIMARY KEY,
            ltp REAL,
            oi INTEGER,
            volume INTEGER
        )
    """)
    conn.commit()
    conn.close()

def load_prev():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT symbol, ltp, oi, volume FROM snapshot")
    data = {r[0]: r[1:] for r in c.fetchall()}
    conn.close()
    return data

def save_curr(rows):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for r in rows:
        c.execute("REPLACE INTO snapshot VALUES (?,?,?,?)", r)
    conn.commit()
    conn.close()

# ================== INSTRUMENT MASTER ==================
def load_instruments():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    return requests.get(url, timeout=20).json()

# ================== STRIKES ==================
def atm_strike(spot):
    return int(round(spot / 50) * 50)

def build_strikes(atm):
    return {
        "CE": [atm-50, atm, atm+50, atm+100, atm+150],
        "PE": [atm+50, atm, atm-50, atm-100, atm-150]
    }

# ================== OPTION SYMBOL ==================
def find_option(instruments, strike, opt_type):
    for i in instruments:
        if (
            i["name"] == "NIFTY"
            and i["instrumenttype"] == "OPTIDX"
            and int(float(i["strike"])) == strike
            and i["symbol"].endswith(opt_type)
        ):
            return i["symbol"], i["token"]
    return None, None

# ================== LTP / QUOTE ==================
def get_quote(obj, exch, symbol, token):
    q = obj.getMarketData("LTP", {
        "exchangeTokens": {exch: [token]}
    })
    d = q["data"]["fetched"][0]
    return float(d["ltp"]), int(d["oi"]), int(d["tradeVolume"])

# ================== MARKET HOURS ==================
def market_open():
    t = datetime.now().time()
    return t >= datetime.strptime("09:15", "%H:%M").time() and \
           t <= datetime.strptime("15:30", "%H:%M").time()

# ================== MAIN ==================
def main():
    send_telegram("🚀 NIFTY OPTIONS OI BOT STARTED")
    init_db()

    instruments = load_instruments()
    prev = load_prev()

    while True:
        try:
            if not market_open():
                time.sleep(INTERVAL_SECONDS)
                continue

            obj = angel_login()

            # -------- Spot --------
            spot_token = next(i["token"] for i in instruments if i["symbol"]=="NIFTY" and i["exch_seg"]=="NSE")
            spot = float(obj.ltpData("NSE","NIFTY",spot_token)["data"]["ltp"])

            atm = atm_strike(spot)
            strikes = build_strikes(atm)

            curr_rows = []
            ce_val = pe_val = ce_chg = pe_chg = 0

            for side in ["CE","PE"]:
                for strike in strikes[side]:
                    sym, tok = find_option(instruments, strike, side)
                    if not tok:
                        continue

                    ltp, oi, vol = get_quote(obj,"NFO",sym,tok)
                    curr_rows.append((sym,ltp,oi,vol))

                    prev_ltp, prev_oi, prev_vol = prev.get(sym,(0,0,0))

                    val = ltp * oi
                    prev_val = prev_ltp * prev_oi
                    d_val = val - prev_val

                    if side=="CE":
                        ce_val += val
                        ce_chg += d_val
                    else:
                        pe_val += val
                        pe_chg += d_val

            save_curr(curr_rows)

            bias = "BULLISH 🔼" if pe_chg > ce_chg else "BEARISH 🔽"

            send_telegram(
                f"📊 NIFTY OI UPDATE\n\n"
                f"ATM : {atm}\n\n"
                f"CALL LTP×OI : {round(ce_val/1e7,2)} Cr\n"
                f"ΔCALL       : {round(ce_chg/1e7,2)} Cr\n\n"
                f"PUT  LTP×OI : {round(pe_val/1e7,2)} Cr\n"
                f"ΔPUT        : {round(pe_chg/1e7,2)} Cr\n\n"
                f"SHIFT : {bias}"
            )

        except Exception as e:
            send_telegram(f"❌ OI ERROR\n{e}")

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()