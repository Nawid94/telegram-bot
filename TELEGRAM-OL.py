from datetime import datetime
import requests
import os
import pytz
import pickle

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHAT_ID')  
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TEHRAN_TZ = pytz.timezone('Asia/Tehran')
TOKEN_FILE = "tokens.pkl"

def load_previous_time():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as file:
            tokens = pickle.load(file)
            if tokens:  # بررسی اینکه لیست خالی نباشد
                return tokens[-1]  # آخرین مقدار ذخیره‌شده را برمی‌گرداند
    return None

def save_current_time(current_time):
    tokens = []
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as file:
            tokens = pickle.load(file)
    tokens.append(current_time)
    with open(TOKEN_FILE, "wb") as file:
        pickle.dump(tokens, file)

def send_time_to_telegram():
    current_time = datetime.now(TEHRAN_TZ)
    current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    previous_time_str = load_previous_time()
    
    if previous_time_str:
        previous_time = datetime.strptime(previous_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TEHRAN_TZ)
        time_difference = current_time - previous_time
        message = f"Now in Tehran: {current_time_str}\nTime since last message: {time_difference}"
    else:
        message = f"Now in Tehran: {current_time_str}\nThis is the first recorded time."
    
    params = {'chat_id': TELEGRAM_CHANNEL_ID, 'text': message}
    response = requests.post(TELEGRAM_API_URL, params=params)
    
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Error sending message: {response.status_code}")
    
    save_current_time(current_time_str)

send_time_to_telegram()
