from datetime import datetime
import requests
import os
import pytz

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHAT_ID')  
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

def send_time_to_telegram():
    current_time = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    message = f"Now in Tehran: {current_time}"
    params = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': message
    }
    response = requests.post(TELEGRAM_API_URL, params=params)
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Error sending message: {response.status_code}")

send_time_to_telegram()
