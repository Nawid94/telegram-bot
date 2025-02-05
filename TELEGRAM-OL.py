import requests
import os
import re
from datetime import datetime
import pytz

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # آیدی کانال برای ارسال پیام
TELEGRAM_BACKUP_ID = os.getenv('TELEGRAM_BACKUP_ID')  # آیدی گروه برای خواندن پیام‌ها

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

def send_to_telegram(chat_id, message):
    params = {'chat_id': chat_id, 'text': message}
    response = requests.post(TELEGRAM_API_URL, params=params)

def get_last_backup_time():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?limit=10"
    response = requests.get(url).json()

    if response.get("ok"):
        updates = response.get("result", [])
        for update in reversed(updates):  # بررسی از جدیدترین پیام‌ها به قدیمی‌ترین
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id") 
            
            if chat_id == int(TELEGRAM_BACKUP_ID):  # فقط پیام‌های گروه مربوطه
                text = message.get("text", "")
                
                # با استفاده از regex برای پیدا کردن زمان آخرین بک‌آپ
                match = re.search(r"Backup time:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", text)
                if match:
                    return match.group(1)  # اگر زمان پیدا شد، آن را برگردان

    return None  # در صورتی که هیچ پیامی پیدا نشد

def send_time_to_telegram():
    current_time = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    previous_time_str = get_last_backup_time()
    
    if previous_time_str:
        previous_time = datetime.strptime(previous_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TEHRAN_TZ)
        time_difference = datetime.now(TEHRAN_TZ) - previous_time
        total_seconds = int(time_difference.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        formatted_difference = f"{hours} hours, {minutes} minutes, {seconds} seconds"
        message = f"Now: {current_time}\nTime since last message: {formatted_difference}"
    else:
        message = f"Now: {current_time}\nThis is the first recorded time."

    # ارسال پیام به کانال (با استفاده از TELEGRAM_CHAT_ID)
    send_to_telegram(TELEGRAM_CHAT_ID, message)
    
    # ارسال پیام به گروه (با استفاده از TELEGRAM_BACKUP_ID)
    send_to_telegram(TELEGRAM_BACKUP_ID, f"Backup time: {current_time}")

send_time_to_telegram()
