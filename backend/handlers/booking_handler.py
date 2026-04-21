from telebot import types
from services.supabase_db import supabase

def register_booking_handlers(bot):
    @bot.message_handler(commands=['pesan'])
    def handle_order_baru(message):
        customer_id = message.from_user.id
        customer_name = message.from_user.first_name
        target_group = "-100xxxxxxxxxx" # <--- GANTI DENGAN ID GRUP KURIR BOSS

        try:
            # 1. Simpan Data ke Database (Status Pending)
            res = supabase.table("orders").insert({
                "customer_tg_id": customer_id,
                "customer_name": customer_name,
                "status": "pending",
                "total_price": 50000, # Contoh harga barang
                "delivery_fee": 10000 # Contoh ongkir
            }).execute()

            if not res.data: return
            order_id = res.data[0]['id']

            # 2. Kirim ke Grup Kurir & SIMPAN MESSAGE ID-NYA
            markup_grup = types.InlineKeyboardMarkup()
            markup_grup.add(types.InlineKeyboardButton("🛵 AMBIL ORDER", callback_data=f"ambil_{order_id}"))
            
            pesan_grup = f"📦 *ORDERAN BARU!*\nID: `{order_id[:8]}`\n👤 Pelanggan: {customer_name}"
            
            # Ini yang Boss cari: Simpan 'sent_msg' agar bisa diedit/hapus nanti
            sent_msg = bot.send_message(target_group, pesan_grup, parse_mode="Markdown", reply_markup=markup_grup)

            # 3. Update DB: Masukkan message_id grup tadi biar bisa dihapus kalau batal
            supabase.table("orders").update({
                "group_message_id": sent_msg.message_id,
                "group_id": str(target_group)
            }).eq("id", order_id).execute()

            # 4. KIRIM TOMBOL CANCEL KE USER (Langsung Muncul!)
            markup_user = types.InlineKeyboardMarkup()
            markup_user.add(types.InlineKeyboardButton("❌ BATALKAN PESANAN", callback_data=f"user_cancel_{order_id}"))

            bot.send_message(
                customer_id, 
                "✅ *Pesanan Berhasil Dibuat!*\n\nSedang mencarikan kurir terdekat. Mohon ditunggu...",
                parse_mode="Markdown",
                reply_markup=markup_user
            )

        except Exception as e:
            print(f"🚨 Error Booking: {e}")
            bot.send_message(customer_id, "❌ Gagal membuat pesanan.")