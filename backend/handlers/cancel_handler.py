from telebot import types
from services.supabase_db import get_order_by_id, supabase

def register_cancel_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith('user_cancel_'))
    def handle_user_cancel(call):
        order_id = call.data.replace('user_cancel_', '').strip()
        u_id = call.from_user.id
        
        try:
            # 1. Tarik data order terbaru
            order = get_order_by_id(order_id)
            if not order:
                bot.answer_callback_query(call.id, "❌ Orderan tidak ditemukan!", show_alert=True)
                return

            # 2. Proteksi: Jika kurir sudah klik AMBIL (status bukan pending)
            if order.get('status') != 'pending':
                bot.answer_callback_query(call.id, "⚠️ Terlambat! Kurir sudah mengambil orderan Anda.", show_alert=True)
                # Hapus tombol di user biar gak diklik lagi
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                return

            # 3. Update Status ke Cancelled di Supabase
            supabase.table("orders").update({"status": "cancelled"}).eq("id", order_id).execute()

            # 4. Sinkronisasi UI: Edit pesan di Grup Kurir
            group_id = order.get('group_id')
            msg_id_grup = order.get('group_message_id')
            
            if group_id and msg_id_grup:
                try:
                    bot.edit_message_text(
                        f"❌ **ORDERAN DIBATALKAN PEMBELI**\nID: `{order_id[:8]}`",
                        chat_id=group_id,
                        message_id=msg_id_grup
                    )
                except Exception as e:
                    print(f"Gagal edit pesan grup: {e}")

            # 5. Sinkronisasi UI: Edit pesan di Chat User
            bot.edit_message_text(
                "❌ **PESANAN DIBATALKAN**\n\nBerhasil membatalkan pesanan. Anda bisa memesan kembali lewat menu utama.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "✅ Pesanan dibatalkan.")

        except Exception as e:
            print(f"🚨 Error di cancel_handler: {e}")
            bot.answer_callback_query(call.id, "❌ Terjadi kesalahan teknis.")