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

INTERVAL_SECONDS = 120   # 2 min for debug
DB_FILE = "oi_snapshot.db"

# ================== TELEGRAM ==================
def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)

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
            oi INTEGER
        )
    """)
    conn.commit()
    conn.close()

def load_prev():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT symbol, ltp, oi FROM snapshot")
    data = {r[0]: (r[1], r[2]) for r in c.fetchall()}
    conn.close()
    return data

def save_curr(rows):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for r in rows:
        c.execute("REPLACE INTO snapshot VALUES (?,?,?)", r)
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

# ================== OPTION FINDER ==================
def find_option(instruments, strike, opt_type):
    for i in instruments:
        if (
            i.get("name") == "NIFTY"
            and i.get("instrumenttype") == "OPTIDX"
            and int(float(i.get("strike", 0))) == strike
            and i.get("symbol", "").endswith(opt_type)
        ):
            return i["symbol"], i["token"]
    return None, None

# ================== LTP + OI ==================
def get_ltp_oi(obj, symbol, token):
    q = obj.getMarketData("LTP", {
        "exchangeTokens": {"NFO": [token]}
    })
    d = q["data"]["fetched"][0]
    return float(d["ltp"]), int(d["oi"])

# ================== MAIN ==================
def main():
    send_telegram("🚀 NIFTY OI BOT DEBUG MODE STARTED")
    init_db()

    instruments = load_instruments()
    prev = load_prev()

    while True:
        try:
            send_telegram("🧪 LOOP ENTERED")

            obj = angel_login()

            # -------- SPOT --------
            spot_token = next(
                i["token"] for i in instruments
                if i["symbol"] == "NIFTY" and i["exch_seg"] == "NSE"
            )
            spot = float(obj.ltpData("NSE", "NIFTY", spot_token)["data"]["ltp"])
            atm = atm_strike(spot)

            send_telegram(f"📍 SPOT OK\nSpot: {spot}\nATM: {atm}")

            strikes = build_strikes(atm)
            curr_rows = []

            ce_val = pe_val = ce_chg = pe_chg = 0

            for side in ["CE", "PE"]:
                for strike in strikes[side]:
                    sym, tok = find_option(instruments, strike, side)
                    if not tok:
                        send_telegram(f"⚠️ Missing {strike}{side}")
                        continue

                    ltp, oi = get_ltp_oi(obj, sym, tok)
                    curr_rows.append((sym, ltp, oi))

                    prev_ltp, prev_oi = prev.get(sym, (0, 0))
                    val = ltp * oi
                    dval = val - (prev_ltp * prev_oi)

                    if side == "CE":
                        ce_val += val
                        ce_chg += dval
                    else:
                        pe_val += val
                        pe_chg += dval

            save_curr(curr_rows)

            bias = "BULLISH 🔼" if pe_chg > ce_chg else "BEARISH 🔽"

            send_telegram(
                f"📊 OI DEBUG DATA\n\n"
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