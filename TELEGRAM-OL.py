import requests
from datetime import datetime
import time

TELEGRAM_BOT_TOKEN = '7700864547:AAEfIV3T2C1fkQ8t1P5kpLyF8EuooCTVy68'
TELEGRAM_CHANNEL_ID = -1002379220152  # آیدی عددی کانال خصوصی
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def send_time_to_telegram():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"زمان فعلی: {current_time}"
    params = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': message
    }
    response = requests.post(TELEGRAM_API_URL, params=params)
    if response.status_code == 200:
        print("ok")
    else:
        print(f"error: {response.status_code}")


send_time_to_telegram()

