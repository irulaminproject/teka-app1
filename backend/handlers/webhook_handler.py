# handlers/webhook_handler.py
from services.notifier import kirim_notifikasi_order
from services.supabase_db import supabase

def handle_supabase_webhook(bot, payload):
    """
    Fungsi ini dipanggil otomatis setiap ada data masuk di Supabase.
    Nggak peduli ordernya dari Web App atau mana pun.
    """
    order_id = payload.get('id')
    order_data = payload  # Data lengkap dari tabel orders
    
    print(f"📦 Order masuk dari Web App! ID: {order_id}")
    
    # LANGSUNG PANGGIL NOTIFIER SAKTI KITA
    kirim_notifikasi_order(bot, order_id, order_data)