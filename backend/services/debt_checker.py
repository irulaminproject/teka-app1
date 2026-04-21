import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Inisialisasi mandiri untuk script
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def can_take_order(driver_id):
    """
    Fungsi untuk mengecek apakah driver punya hutang menumpuk.
    Misal: Limit hutang setoran adalah Rp 200.000
    """
    try:
        # Contoh logika: Hitung total ongkir yang statusnya 'completed' tapi belum 'settled'
        res = supabase.table("orders").select("total_price").eq("driver_tg_id", driver_id).eq("status", "completed").eq("is_settled", False).execute()
        
        total_hutang = sum(item['total_price'] for item in res.data)
        limit = 200000 
        
        if total_hutang > limit:
            return False, total_hutang
        return True, total_hutang
    except:
        return True, 0 # Jika error, bebaskan dulu biar operasional jalan