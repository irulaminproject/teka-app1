import math

def calculate_delivery_fee(lat_toko, lon_toko, lat_dest, lon_dest, settings):
    """
    Menghitung Ongkir & Jarak secara dinamis berdasarkan settings.
    """
    # 1. Rumus Haversine (Hitung Jarak)
    R = 6371
    dlat = math.radians(float(lat_dest) - float(lat_toko))
    dlon = math.radians(float(lon_dest) - float(lon_toko))
    
    a = math.sin(dlat / 2)**2 + \
        math.cos(math.radians(float(lat_toko))) * math.cos(math.radians(float(lat_dest))) * \
        math.sin(dlon / 2)**2
        
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    jarak = R * c
    
    # 2. Ambil Harga dari Settings (Data dari Poin 1)
    jarak_min = float(settings.get('jarak_minimal', 2))
    ongkir_dasar = int(settings.get('ongkir_dasar', 5000))
    tarif_per_km = int(settings.get('ongkir_per_km', 2500))
    
    # 3. Logika Perhitungan
    if jarak <= jarak_min:
        ongkir_raw = ongkir_dasar
    else:
        kelebihan_jarak = jarak - jarak_min
        ongkir_raw = ongkir_dasar + (kelebihan_jarak * tarif_per_km)
    
    # Bulatkan ke 500 terdekat
    delivery_fee = int(math.ceil(ongkir_raw / 500.0) * 500.0)
    
    # App Fee (10% dari ongkir, maksimal 2500)
    app_fee = min(int(delivery_fee * 0.10), 2500)
    
    return delivery_fee, app_fee, round(jarak, 2)

def get_payout_details(total_price, delivery_fee, app_fee):
    """Merinci apa yang harus dibayar user dan apa yang diterima kurir"""
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