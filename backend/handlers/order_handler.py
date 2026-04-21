import os
import sys
from telebot import types

# --- FIX PYTHON PATH (Agar folder scripts & services terbaca) ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# --- IMPORT MODUL ---
try:
    from services.supabase_db import (
        get_order_by_id, 
        update_order_status, 
        can_take_order, 
        get_all_settings,
        get_payout_details,
        supabase
    )
    print("✅ [Order Handler] Berhasil memuat semua fungsi dari services")
except ImportError as e:
    print(f"🚨 [Order Handler] Gagal Import: {e}")

def register_order_handlers(bot):

    # --- 1. HANDLER: AMBIL PESANAN (CLAIM OLEH KURIR) ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith('ambil_'))
    def handle_claim_order(call):
        order_id = call.data.replace('ambil_', '').strip()
        driver_id = call.from_user.id
        driver_name = call.from_user.first_name
        group_id_asal = str(call.message.chat.id)

        try:
            # A. Cek Kelayakan Kurir
            allowed, hutang = can_take_order(driver_id)
            if not allowed:
                bot.answer_callback_query(call.id, f"⚠️ Setoran macet! Hutang: Rp {hutang:,}", show_alert=True)
                return

            # B. Tarik Data Order
            order = get_order_by_id(order_id)
            if not order:
                bot.answer_callback_query(call.id, "❌ Error: Pesanan tidak ditemukan.", show_alert=True)
                return
            
            # C. Proteksi: Cek jika sudah diambil kurir lain atau dibatalkan user
            if order.get('status') == 'taken':
                bot.answer_callback_query(call.id, "❌ Sudah diambil kurir lain.", show_alert=True)
                return
            
            if order.get('status') == 'cancelled':
                bot.answer_callback_query(call.id, "❌ Maaf, pesanan ini sudah dibatalkan oleh pembeli.", show_alert=True)
                try: bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                return

            # D. Hitung Rincian Keuangan (Logika Lengkap Boss)
            calc = get_payout_details(
                order.get('total_price'), 
                order.get('delivery_fee'), 
                order.get('app_fee')
            )

            # E. Link Maps
            s_lat, s_lng = order.get('store_latitude'), order.get('store_longitude')
            link_toko = f"https://www.google.com/maps?q={s_lat},{s_lng}" if s_lat else "Data lokasi tidak ada"
            
            d_lat, d_lng = order.get('dest_latitude'), order.get('dest_longitude')
            link_pembeli = f"https://www.google.com/maps?q={d_lat},{d_lng}" if d_lat else "Data lokasi tidak ada"

            # F. Update Status di Database
            supabase.table("orders").update({
                "status": "taken",
                "driver_tg_id": driver_id,
                "driver_name": driver_name,
                "group_id": group_id_asal
            }).eq("id", order_id).execute()

            # G. Update Tampilan di Grup (Hilangkan Tombol)
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"{call.message.text}\n\n✅ **DIAMBIL OLEH: {driver_name}**",
                    parse_mode="Markdown",
                    reply_markup=None
                )
            except: pass

            # H. Notifikasi ke Customer (Pembeli)
            customer_id = order.get('customer_tg_id')
            if customer_id:
                try:
                    notif_to_customer = (
                        "✅ *Kurir Ditemukan!*\n"
                        "Pesanan Anda sedang diproses.\n\n"
                        f"🛵 *KURIR:* {driver_name}\n"
                        "━━━━━━━━━━━━━━━━━━\n"
                        "Anda bisa langsung chat kurir melalui bot ini."
                    )
                    bot.send_message(customer_id, notif_to_customer, parse_mode="Markdown")
                except: pass

            # I. Kirim SURAT JALAN DIGITAL Lengkap ke Kurir
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ SELESAIKAN", callback_data=f"selesai_{order_id}"),
                types.InlineKeyboardButton("❌ BATAL", callback_data=f"confirm_batal_{order_id}")
            )

            detail_msg = (
                "📦 *SURAT JALAN DIGITAL*\n"
                f"ID: `{order_id[:8].upper()}`\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"👤 *PEMBELI:* {order.get('customer_name') or 'Pelanggan'}\n"
                f"🛍️ *HARGA BARANG:* Rp {calc['barang']:,}\n"
                f"🛵 *ONGKIR:* Rp {calc['ongkir']:,}\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"📱 *BIAYA APLIKASI:* Rp {calc['biaya_app']:,}\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💵 *TAGIH KE USER: Rp {calc['tagihan_user']:,}*\n"
                f"💰 *HASIL BERSIH: Rp {calc['hasil_kurir']:,}*\n\n"
                f"🏪 *LOKASI TOKO (JEMPUT):*\n{link_toko}\n\n"
                f"📍 *LOKASI USER (ANTAR):*\n{link_pembeli}\n\n"
                "🚩 _Klik tombol di bawah jika pesanan sudah sampai._"
            )
            
            bot.send_message(driver_id, detail_msg, parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id, "✅ Berhasil Mengambil Order!")

        except Exception as e:
            print(f"🚨 Error Claim Order: {e}")

    # --- 2. HANDLER: SELESAIKAN PESANAN ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith('selesai_'))
    def handle_finish_order(call):
        order_id = call.data.replace('selesai_', '').strip()
        try:
            supabase.table("orders").update({"status": "completed"}).eq("id", order_id).execute()
            order = get_order_by_id(order_id)
            customer_id = order.get('customer_tg_id')

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{call.message.text}\n\n🏁 **STATUS: SELESAI**",
                parse_mode="Markdown",
                reply_markup=None
            )
            bot.answer_callback_query(call.id, "✅ Pesanan Selesai!", show_alert=True)

            if customer_id:
                bot.send_message(customer_id, "🏁 *Pesanan Selesai!*\nTerima kasih telah memesan.", parse_mode="Markdown")
        except Exception as e:
            print(f"🚨 Error Finish Order: {e}")

    # --- 3. HANDLER: BATAL OLEH KURIR & LEMPAR BALIK KE GRUP ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_batal_'))
    def handle_cancel_order(call):
        order_id = call.data.replace('confirm_batal_', '').strip()
        
        try:
            update_order_status(order_id, 'pending')
            order = get_order_by_id(order_id)
            target_group = order.get('group_id')
            store_id = order.get('store_id')
            customer_tg_id = order.get('customer_tg_id')

            # Notif ke Pembeli (Bahwa driver cancel & kasih tombol batal user)
            if customer_tg_id:
                try:
                    markup_user = types.InlineKeyboardMarkup()
                    markup_user.add(types.InlineKeyboardButton("❌ BATALKAN PESANAN", callback_data=f"user_cancel_{order_id}"))
                    
                    notif_user = (
                        "⚠️ *Update Pesanan!*\n"
                        "Kurir sebelumnya membatalkan pengambilan pesanan Anda.\n\n"
                        "🔄 *Status:* Sedang mencarikan kurir pengganti...\n"
                        "Mohon tunggu sebentar ya, Kak. 🙏"
                    )
                    bot.send_message(customer_tg_id, notif_user, parse_mode="Markdown", reply_markup=markup_user)
                except: pass

            # Kirim Balik ke Grup Kurir
            if target_group:
                nama_toko = "Toko"
                if store_id:
                    res_store = supabase.table("stores").select("store_name").eq("id", store_id).single().execute()
                    if res_store.data:
                        nama_toko = res_store.data.get('store_name')

                harga_barang = order.get('total_price', 0)
                ongkir = order.get('delivery_fee', 0)
                jarak = order.get('distance_km', 0)
                total_bayar = harga_barang + ongkir

                s_lat, s_lng = order.get('store_latitude'), order.get('store_longitude')
                d_lat, d_lng = order.get('dest_latitude'), order.get('dest_longitude')
                link_toko = f"https://www.google.com/maps?q={s_lat},{s_lng}" if s_lat else "-"
                link_pembeli = f"https://www.google.com/maps?q={d_lat},{d_lng}" if d_lat else "-"

                markup_grup = types.InlineKeyboardMarkup()
                markup_grup.add(types.InlineKeyboardButton("🛵 AMBIL ORDER", callback_data=f"ambil_{order_id}"))
                
                pesan_grup = (
                    "🔄 *ORDERAN TERSEDIA KEMBALI*\n"
                    f"ID: `{order_id[:8].upper()}`\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"🏪 *Toko:* {nama_toko}\n"
                    f"📦 *Barang:* Rp{harga_barang:,}\n"
                    f"🛵 *Ongkir:* Rp{ongkir:,} (±{jarak} km)\n"
                    f"💰 *TOTAL BAYAR: Rp{total_bayar:,}*\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"🏬 *LOKASI TOKO:* {link_toko}\n"
                    f"📍 *LOKASI PEMBELI:* {link_pembeli}\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "⚠️ _Kurir sebelumnya membatalkan._"
                )
                bot.send_message(target_group, pesan_grup, parse_mode="Markdown", reply_markup=markup_grup)

            bot.answer_callback_query(call.id, "⚠️ Pesanan dilepas ke grup.", show_alert=True)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ *BATAL*\nSudah dilepas dan dikirim ulang ke grup.",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"🚨 ERROR BATAL KURIR: {e}")

    # --- 4. HANDLER: USER CANCEL (BATAL OLEH PEMBELI) ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith('user_cancel_'))
    def handle_user_cancel(call):
        order_id = call.data.replace('user_cancel_', '').strip()
        
        try:
            # Ambil data order terbaru
            order = get_order_by_id(order_id)
            if not order: return

            # JIKA SUDAH DIAMBIL KURIR, USER TIDAK BOLEH CANCEL
            if order.get('status') != 'pending':
                bot.answer_callback_query(call.id, "⚠️ Gagal! Pesanan sudah diproses kurir.", show_alert=True)
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                return

            # UPDATE DATABASE KE CANCELLED
            supabase.table("orders").update({"status": "cancelled"}).eq("id", order_id).execute()

            # --- LOGIKA HAPUS PESAN DI GRUP ---
            # Kita ambil group_id dan message_id yang tersimpan di DB
            group_id = order.get('group_id')
            msg_id_grup = order.get('group_message_id') # Pastikan kolom ini ada di DB

            if group_id and msg_id_grup:
                try:
                    bot.edit_message_text(
                        "❌ **PESANAN DIBATALKAN OLEH USER**",
                        chat_id=group_id,
                        message_id=msg_id_grup
                    )
                except:
                    pass # Abaikan jika gagal edit (misal pesan sudah dihapus manual)

            # Ubah tampilan di chat user
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ *PESANAN BERHASIL DIBATALKAN*",
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "✅ Berhasil membatalkan.")

        except Exception as e:
            print(f"🚨 ERROR USER CANCEL: {e}")