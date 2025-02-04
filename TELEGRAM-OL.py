import requests
import os
import re
from datetime import datetime
import pytz

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TELEGRAM_HISTORY_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

def send_to_telegram(message):
    params = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    response = requests.post(TELEGRAM_API_URL, params=params)
    if response.status_code == 200:
        print("✅ Message sent successfully!")
    else:
        print(f"⚠️ Error sending message: {response.status_code}")

def get_last_message():
    try:
        response = requests.get(TELEGRAM_HISTORY_URL)
        if response.status_code == 200:
            data = response.json()
            messages = data.get("result", [])
            if messages:
                for message in reversed(messages):
                    if "message" in message and "text" in message["message"]:
                        return message["message"]["text"]
    except Exception as e:
        print(f"⚠️ Error getting last message: {e}")
    return None

def extract_previous_time(message):
    match = re.search(r"🕰 Now: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", message)
    return match.group(1) if match else None

def send_time_to_telegram():
    current_time = datetime.now(TEHRAN_TZ)
    current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

    previous_message = get_last_message()
    if previous_message:
        previous_time_str = extract_previous_time(previous_message)
        if previous_time_str:
            previous_time = datetime.strptime(previous_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TEHRAN_TZ)
            time_difference = current_time - previous_time
            message = f"🕰 Now: {current_time_str}\n⏳ Time since last message: {time_difference}"
        else:
            message = f"🕰 Now: {current_time_str}\n⚠️ Could not extract previous time!"
    else:
        message = f"🕰 Now: {current_time_str}\n🚀 This is the first recorded time."

    send_to_telegram(message)

send_time_to_telegram()
