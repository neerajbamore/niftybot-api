import time
import requests
import schedule
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }
    requests.post(url, data=data)

def job():
    send_telegram("✅ NiftyBot is LIVE (test message)")

schedule.every(3).minutes.do(job)

send_telegram("🚀 NiftyBot started successfully")

while True:
    schedule.run_pending()
    time.sleep(1)