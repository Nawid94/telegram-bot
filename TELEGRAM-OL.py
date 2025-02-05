import requests
import os
import redis
from datetime import datetime
import pytz

# دریافت مقادیر متغیرهای محیطی
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_USERNAME = os.getenv('REDIS_USERNAME')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# چاپ مقادیر متغیرهای محیطی برای بررسی
print(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN}")
print(f"TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")
print(f"REDIS_HOST: {REDIS_HOST}")
print(f"REDIS_PORT: {REDIS_PORT}")
print(f"REDIS_USERNAME: {REDIS_USERNAME}")
print(f"REDIS_PASSWORD: {REDIS_PASSWORD}")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    username=REDIS_USERNAME,
    password=REDIS_PASSWORD,
    decode_responses=True
)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

def send_to_telegram(chat_id, message):
    params = {'chat_id': chat_id, 'text': message}
    requests.post(TELEGRAM_API_URL, params=params)

def get_last_backup_time():
    return redis_client.get("last_backup_time")

def save_backup_time(timestamp):
    redis_client.set("last_backup_time", timestamp)

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

    send_to_telegram(TELEGRAM_CHAT_ID, message)
    save_backup_time(current_time)

send_time_to_telegram()
