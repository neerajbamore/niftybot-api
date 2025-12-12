from flask import Flask, jsonify
import os, requests
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        return r.ok, r.text
    except Exception as e:
        return False, str(e)

# INDIA PROXY API (Cloudflare bypass)
OC_URL = "https://nseindia-api.vercel.app/option-chain?symbol=NIFTY"
FUT_URL = "https://nseindia-api.vercel.app/future?symbol=NIFTY"


@app.route("/send")
def send_report():

    # Fetch Proxy OC
    try:
        oc = requests.get(OC_URL, timeout=10).json()
    except:
        return jsonify({"ok": False, "error": "OC fetch failed"}), 500

    if "records" not in oc:
        return jsonify({"ok": False, "error": "OC JSON invalid"}), 500

    records = oc["records"]
    spot = records.get("underlyingValue", 0)
    rows = records.get("data", [])

    # Separate CE PE
    ce = [x for x in rows if "CE" in x]
    pe = [x for x in rows if "PE" in x]

    strikes = sorted({x["strikePrice"] for x in ce})
    atm = min(strikes, key=lambda x: abs(x - spot))

    # Helper
    def pick(side_list, side):
        itm = [x for x in side_list if (x["strikePrice"] < atm if side=="CE" else x["strikePrice"] > atm)]
        itm_pick = itm[-1] if itm else None
        atm_pick = next((x for x in side_list if x["strikePrice"] == atm), None)
        otm = [x for x in side_list if (x["strikePrice"] > atm if side=="CE" else x["strikePrice"] < atm)]
        otm_pick = otm[:3] if side=="CE" else otm[-3:]
        return itm_pick, atm_pick, otm_pick

    ce_itm, ce_atm, ce_otm = pick(ce, "CE")
    pe_itm, pe_atm, pe_otm = pick(pe, "PE")

    def fmt(tag, row, type_):
        if not row:
            return f"{tag}: NA\n"
        d = row[type_]
        ltp = d.get("lastPrice", 0)
        oi = d.get("openInterest", 0)
        coi = d.get("changeinOpenInterest", 0)
        return (
            f"{tag} {row['strikePrice']}\n"
            f" LTP: {ltp} | OI: {oi} | LTP×OI: {ltp*oi}\n"
            f" COI: {coi} | LTP×COI: {ltp*coi}\n"
        )

    # Fetch FUTURE
    try:
        fut = requests.get(FUT_URL, timeout=10).json()
    except:
        fut = {}

    fut_msg = "\n📘 FUTURE\n"
    try:
        f = fut["data"][0]
        fut_msg += (
            f" Price: {f.get('lastPrice')}\n"
            f" Change: {f.get('change')}\n"
            f" OI: {f.get('openInterest')}\n"
            f" Volume: {f.get('totalTradedVolume')}\n"
        )
    except:
        fut_msg += " NA\n"

    # FINAL MESSAGE
    text = (
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

    ok, resp = send_telegram(text)
    return jsonify({"ok": ok, "response": resp, "message_sent": text})


@app.route("/")
def home():
    return "Nifty Bot Running (Proxy Mode)!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))