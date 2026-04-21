import telebot
from telebot import types

def kirim_notifikasi_order(bot, order_id, order_data):
    # ID Telegram Boss (Ambil dari identitas profesional Boss)
    MY_ID = 5692298748 
    
    print(f"--- DEBUG KERAS ---")
    print(f"Mencoba paksa kirim ke: {MY_ID}")

    invoice_text = (
        f"🚨 *ORDER MASUK (TEST)*\n"
        f"🆔 ID: `{str(order_id)[:8].upper()}`\n"
        f"💰 Total: Rp {order_data.get('total_price', 0):,}\n"
        f"📌 Sumber: Web App Boss Irul"
    )

    try:
        # Tombol interaktif
        mk = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("❌ BATALKAN", callback_data=f"user_cancel_{order_id}")
        )
        
        # Kirim langsung tanpa syarat
        bot.send_message(MY_ID, invoice_text, parse_mode="Markdown", reply_markup=mk)
        print(f"✅ BERHASIL: Invoice terkirim ke HP Boss.")
    except Exception as e:
        print(f"🚨 GAGAL TOTAL: {e}")