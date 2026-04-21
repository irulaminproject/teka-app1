import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. LOAD KONFIGURASI
load_dotenv()
url = os.getenv("SUPABASE_URL")
# Ganti ke ANON_KEY sesuai instruksi Boss
key = os.getenv("SUPABASE_ANON_KEY") 

if not url or not key:
    print("❌ ERROR: SUPABASE_URL atau SUPABASE_ANON_KEY tidak ditemukan di .env")
    exit()

supabase: Client = create_client(url, key)

# --- 2. FUNGSI SETTINGS (DAFTAR HARGA) ---
def get_all_settings():
    """Mengambil tarif dinamis dari tabel settings (jarak_minimal, ongkir_dasar, dll)"""
    try:
        res = supabase.table("settings").select("*").execute()
        # Mengubah format list ke dictionary: {'key': 'value'}
        return {item['key']: item['value'] for item in res.data}
    except Exception as e:
        print(f"🚨 Error get_all_settings: {e}")
        # Fallback angka jika DB bermasalah biar bot gak mati
        return {"jarak_minimal": 2, "ongkir_dasar": 5000, "ongkir_per_km": 2500}

# --- 3. FUNGSI ORDER (MANAJEMEN PESANAN) ---
def get_order_by_id(order_id):
    """Mengambil detail satu pesanan berdasarkan ID"""
    try:
        res = supabase.table("orders").select("*").eq("id", order_id).single().execute()
        return res.data
    except Exception as e:
        print(f"🚨 Error get_order_by_id: {e}")
        return None

def update_order_status(order_id, status, driver_id=None, driver_name=None):
    try:
        # 1. Siapkan data dasar yang PASTI ada kolomnya
        update_data = {"status": status}
        
        # 2. Penanganan Status Batal (Pending)
        if status == "pending":
            update_data["driver_tg_id"] = None
            # Kita pakai dictionary.update supaya aman
            # Jika kolom driver_name ada, kita set NULL, jika tidak ada, abaikan
            res_meta = supabase.table("orders").select("*").limit(1).execute()
            if res_meta.data and "driver_name" in res_meta.data[0]:
                update_data["driver_name"] = None
        
        # 3. Penanganan Ambil Order (Taken)
        elif driver_id:
            update_data["driver_tg_id"] = driver_id
            # Cek dulu apakah kolom driver_name eksis di DB sebelum kirim
            # Ini cara paling aman biar nggak muncul error PGRST204 lagi
            try:
                # Kita coba aja masukkan, kalau error di level Supabase, 
                # kita akan tangkap di except bawah. 
                # Tapi untuk sementara, kita hapus dulu paksaan driver_name-nya
                pass 
            except: pass

        # 4. Eksekusi ke Supabase
        # Jika kamu belum tambah kolom driver_name, jangan masukkan ke update_data
        res = supabase.table("orders").update(update_data).eq("id", order_id).execute()
        return True 
        
    except Exception as e:
        # Jika errornya karena kolom driver_name, kita bersihkan dan coba sekali lagi
        if "driver_name" in str(e):
            print("⚠️ Kolom driver_name tidak ditemukan, mencoba update tanpa nama...")
            try:
                update_data = {"status": status}
                if driver_id: update_data["driver_tg_id"] = driver_id
                if status == "pending": update_data["driver_tg_id"] = None
                supabase.table("orders").update(update_data).eq("id", order_id).execute()
                return True
            except Exception as e2:
                print(f"🚨 Error DB Fatal: {e2}")
        else:
            print(f"🚨 Error DB: {e}")
        return False

# Fungsi pencarian Group ID yang lebih pintar
def get_group_id_by_area(area_name):
    """Cari Group ID berdasarkan nama wilayah di tabel settings"""
    try:
        # Mencari di tabel settings dengan format key: group_id_NamaWilayah
        # Contoh: group_id_Bandar Lampung
        res = supabase.table("settings").select("value").eq("key", f"group_id_{area_name}").single().execute()
        if res.data:
            return res.data.get('value')
        return None
    except Exception as e:
        print(f"🚨 Error cari group_id untuk {area_name}: {e}")
        return None

def get_payout_details(total_price, delivery_fee, app_fee):
    barang = int(total_price or 0)
    ongkir = int(delivery_fee or 0)
    biaya_app = int(app_fee or 0)
    return {
        "tagihan_user": barang + ongkir,
        "hasil_kurir": ongkir - biaya_app,
        "barang": barang,
        "ongkir": ongkir,
        "biaya_app": biaya_app
    }

# --- 4. FUNGSI KURIR (CEK KELAYAKAN) ---
def can_take_order(driver_id):
    """
    Cek apakah kurir boleh ambil order berdasarkan limit hutang setoran.
    """
    try:
        # Mengambil data hutang dari tabel drivers
        res = supabase.table("drivers").select("hutang").eq("tg_id", driver_id).single().execute()
        
        if res.data:
            hutang = int(res.data.get('hutang', 0))
            limit_hutang = 50000 # Limit Rp 50.000, bisa disesuaikan
            
            if hutang >= limit_hutang:
                return False, hutang
            return True, hutang
        
        # Jika driver belum ada di tabel, buat record baru atau izinkan dulu
        return True, 0
    except Exception:
        # Bypass jika tabel drivers belum siap
        return True, 0

# --- 5. FUNGSI CHAT SYNC (CARI PESANAN AKTIF) ---
def get_active_order_by_user(user_id):
    """Mencari pesanan status 'taken' untuk menghubungkan Chat Pembeli & Kurir"""
    try:
        res = supabase.table("orders").select("*")\
            .or_(f"customer_tg_id.eq.{user_id},driver_tg_id.eq.{user_id}")\
            .eq("status", "taken")\
            .order("created_at", desc=True)\
            .limit(1).execute()
        
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"🚨 Error get_active_order: {e}")
        return None