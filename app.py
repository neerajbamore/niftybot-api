import os
import time
import pyotp
import requests
from smartapi import SmartConnect

# ---------- ENV ----------
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ---------- TELEGRAM ----------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ---------- ANGEL LOGIN ----------
def angel_login():
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        obj = SmartConnect(api_key=API_KEY)
        obj.generateSession(CLIENT_ID, PASSWORD, totp)
        send_telegram("✅ Angel login successful")
        return obj
    except Exception as e:
        send_telegram(f"❌ Angel login failed\n{e}")
        return None

# ---------- TEST JOB ----------
def job():
    obj = angel_login()
    if not obj:
        return

    send_telegram("📡 Angel API connected. Ready for data fetch.")

send_telegram("🚀 NiftyBot Angel login test started")
job()

while True:
    time.sleep(60)