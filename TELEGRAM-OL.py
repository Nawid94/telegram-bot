import logging
import datetime
import os
from telegram import Bot

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def send_time():
    now = datetime.datetime.now().strftime("%H:%M:%S")
    message = f"⏰ Current Time: {now}"
    
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)
    print("✅ Time sent successfully!")

if __name__ == "__main__":
    asyncio.run(send_time())
