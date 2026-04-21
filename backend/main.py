import os
import sys

# Tambahkan baris ini di paling atas main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import telebot
from dotenv import load_dotenv
from handlers.order_handler import register_order_handlers
from handlers.chat_handler import register_chat_handlers
from handlers.booking_handler import register_booking_handlers

# 1. KONFIGURASI
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN tidak ditemukan!")
    exit()

bot = telebot.TeleBot(TOKEN)

# 2. REGISTER HANDLERS (Memanggil fungsi dari file terpisah)
register_order_handlers(bot)
register_chat_handlers(bot)

print("✅ Semua Modul Berhasil Dimuat!")
print("🚀 TEKA-App Modular Online!")

# 3. RUN
if __name__ == "__main__":
    bot.infinity_polling()