import requests
import os
import re
from datetime import datetime
import pytz

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # کانال اصلی
TELEGRAM_BACKUP_ID = os.getenv("TELEGRAM_BACKUP_ID")  # گروه بکاپ

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

def send_to_telegram(chat_id, message):
    params = {'chat_id': chat_id, 'text': message}
    response = requests.post(TELEGRAM_API_URL, params=params)
    if response.status_code == 200:
        print("✅ Message sent successfully!")
    else:
        print(f"⚠️ Error sending message: {response.status_code}")

def get_last_backup_time():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?limit=5"
    response = requests.get(url).json()
    if response.get("ok"):
        updates = response.get("result", [])
        for update in reversed(updates):
            message = update.get("message", {}).get("text", "")
            match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", message)
            if match:
                return match.group(1)
    return None

def send_time_to_telegram():
    current_time = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    previous_time_str = get_last_backup_time()
    
    if previous_time_str:
        previous_time = datetime.strptime(previous_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TEHRAN_TZ)
        time_difference = datetime.now(TEHRAN_TZ) - previous_time
        message = f"🕰 Now: {current_time}\n⏳ Time since last message: {time_difference}"
    else:
        message = f"🕰 Now: {current_time}\n🚀 This is the first recorded time."

    send_to_telegram(TELEGRAM_CHAT_ID, message)
    
    send_to_telegram(TELEGRAM_BACKUP_ID, f"Backup time: {current_time}")

send_time_to_telegram()
