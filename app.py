# app.py
# WORKING NSE JSON API VERSION (NO SCRAPING)
# 100% works on Render / Railway / Termux

from flask import Flask, jsonify
import os, requests, time
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# NSE headers (required or NSE blocks request)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
}

session = requests.Session()

def nse_json(url):
    """Fetch JSON safely from NSE API"""
    for _ in range(3):
        try:
            r = session.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return r.json()
        except:
            time.sleep(1)
    return None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        return r.ok
    except:
        return False


@app.route("/send")
def send_report():

    # 1) OPTION CHAIN JSON
    oc_url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    oc = nse_json(oc_url)

    if not oc or "records" not in oc:
        return jsonify({"ok": False, "error": "OC JSON failed"}), 500

    records = oc["records"]
    spot = records.get("underlyingValue", 0)
    data = records.get("data", [])

    # Separate CE and PE
    ce = [x for x in data if "CE" in x]
    pe = [x for x in data if "PE" in x]

    # Pick ATM strike
    strikes = sorted({x["strikePrice"] for x in ce})
    atm = min(strikes, key=lambda x: abs(x - spot))

    # Helper to pick strikes
    def pick(side_list, side):
        itm = [x for x in side_list if (x["strikePrice"] < atm if side=="CE" else x["strikePrice"] > atm)]
        itm_pick = itm[-1] if itm else None

        atm_pick = next((x for x in side_list if x["strikePrice"] == atm), None)

        otm = [x for x in side_list if (x["strikePrice"] > atm if side=="CE" else x["strikePrice"] < atm)]
        otm_pick = otm[:3] if side=="CE" else otm[-3:]

        return itm_pick, atm_pick, otm_pick

    ce_itm, ce_atm, ce_otm = pick(ce, "CE")
    pe_itm, pe_atm, pe_otm = pick(pe, "PE")

    # Format strike output
    def fmt(tag, row, type_):
        if not row: 
            return f"{tag}: NA\n"
        d = row[type_]
        ltp = d.get("lastPrice", 0)
        oi = d.get("openInterest", 0)
        coi = d.get("changeinOpenInterest", 0)
        return (f"{tag} {row['strikePrice']}\n"
                f" LTP: {ltp} | OI: {oi} | LTP×OI: {ltp*oi}\n"
                f" COI: {coi} | LTP×COI: {ltp*coi}\n")

    # 2) FUTURES JSON
    fut_url = "https://www.nseindia.com/api/quote-derivative?symbol=NIFTY"
    fut = nse_json(fut_url)
    fut_msg = ""

    try:
        fut_data = fut["stocks"][0]["marketDeptOrderBook"]["tradeInfo"]
        last = fut_data["lastPrice"]
        change = fut_data["change"]
        volume = fut_data["totalTradedVolume"]
        oi = fut_data["openInterest"]
        fut_msg = (
            f"\n📘 FUTURES\n"
            f" Price: {last}\n"
            f" Change: {change}\n"
            f" Volume: {volume}\n"
            f" OI: {oi}\n"
        )
    except:
        fut_msg = "\n📘 FUTURES: NA\n"

    # FINAL MESSAGE
    msg = (
        f"📌 NIFTY REPORT\n"
        f"Spot: {spot}\nATM: {atm}\nTime: {datetime.now()}\n\n"

        f"--- CALLS ---\n"
        + fmt("ITM", ce_itm, "CE")
        + fmt("ATM", ce_atm, "CE")
        + "".join([fmt(f"OTM{i+1}", o, "CE") for i, o in enumerate(ce_otm)])

        + "\n--- PUTS ---\n"
        + fmt("ITM", pe_itm, "PE")
        + fmt("ATM", pe_atm, "PE")
        + "".join([fmt(f"OTM{i+1}", o, "PE") for i, o in enumerate(pe_otm)])

        + fut_msg
    )

    ok = send_telegram(msg)

    return jsonify({"ok": ok, "message_sent": msg})


@app.route("/")
def home():
    return "Nifty Bot Running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))