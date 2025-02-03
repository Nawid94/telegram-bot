from datetime import datetime
import requests
import os
import pytz
import pickle

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHAT_ID')  
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TEHRAN_TZ = pytz.timezone('Asia/Tehran')
TOKEN_FILE = "bot_output.pkl"  

def send_to_telegram(message):
    params = {'chat_id': TELEGRAM_CHANNEL_ID, 'text': message}
    response = requests.post(TELEGRAM_API_URL, params=params)
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Error sending message: {response.status_code}")

def load_previous_time():
    if not os.path.exists(TOKEN_FILE):
        error_msg = "⚠️ Error: Previous output file not found!"
        print(error_msg)
        send_to_telegram(error_msg)  
        return None
    try:
        with open(TOKEN_FILE, "rb") as file:
            tokens = pickle.load(file)
            if tokens:
                return tokens[-1] 
    except Exception as e:
        error_msg = f"⚠️ Error loading previous time: {e}"
        print(error_msg)
        send_to_telegram(error_msg) 
    return None

def save_current_time(current_time):
    tokens = []
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as file:
                tokens = pickle.load(file)
        except Exception as e:
            error_msg = f"⚠️ Error reading previous tokens: {e}"
            print(error_msg)
            send_to_telegram(error_msg)  
    tokens.append(current_time)
    
    try:
        with open(TOKEN_FILE, "wb") as file:
            pickle.dump(tokens, file)
        print(f"✅ Saved new time: {current_time}")
    except Exception as e:
        error_msg = f"⚠️ Error saving time: {e}"
        print(error_msg)
        send_to_telegram(error_msg)  
def send_time_to_telegram():
    current_time = datetime.now(TEHRAN_TZ)
    current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    previous_time_str = load_previous_time()
    
    if previous_time_str:
        try:
            previous_time = datetime.strptime(previous_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TEHRAN_TZ)
            time_difference = current_time - previous_time
            message = f"🕰 Now: {current_time_str}\n⏳ Time since last message: {time_difference}"
        except Exception as e:
            message = f"🕰 Now: {current_time_str}\n⚠️ Error parsing previous time: {e}"
            send_to_telegram(f"⚠️ Error parsing previous time: {e}")  
    else:
        message = f"🕰 Now: {current_time_str}\n🚀 This is the first recorded time."

    send_to_telegram(message)
    save_current_time(current_time_str)

send_time_to_telegram()
