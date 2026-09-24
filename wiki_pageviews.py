import requests
import pandas as pd

# Menyamarkan request agar terlihat seperti aplikasi riset resmi
H = {"User-Agent": "riset-film-id (indri.cs2026@ids.ac.id)"}

def pageviews(judul_wiki, lang="id", start="20210901", end="20260924"):
    """
    Mengambil data jumlah kunjungan halaman harian dari Wikipedia API.
    Aman dari pemblokiran (dibandingkan Google Trends) dan memberikan angka mutlak.
    """
    print(f"Mengambil data Wikipedia untuk: {judul_wiki}...")
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"{lang}.wikipedia/all-access/user/{judul_wiki}/daily/{start}/{end}")
    
    r = requests.get(url, headers=H, timeout=30)
    
    # Jika halaman tidak ditemukan (misal judul salah), kembalikan DataFrame kosong
    if r.status_code == 404:
        print(f"  [404] Halaman '{judul_wiki}' tidak ditemukan.")
        return pd.DataFrame()
        
    r.raise_for_status()
    
    df = pd.DataFrame(r.json()["items"])[["timestamp", "views"]]
    df = df.assign(film=judul_wiki)
    return df

if __name__ == "__main__":
    # Daftar judul Wikipedia (pastikan format spasi diganti dengan underscore '_')
    # Contoh: 'Jumbo (film)', 'KKN di Desa Penari', 'Agak Laen'
    daftar_film = ["Agak_Laen", "Jumbo_(film)", "KKN_di_Desa_Penari"]
    
    hasil = []
    for judul in daftar_film:
        df_film = pageviews(judul)
        if not df_film.empty:
            hasil.append(df_film)
    
    if hasil:
        df_gabungan = pd.concat(hasil, ignore_index=True)
        # Ubah format timestamp YYYYMMDD00 menjadi datetime
        df_gabungan['timestamp'] = pd.to_datetime(df_gabungan['timestamp'].str[:8], format="%Y%m%d")
        
        output_file = "wiki_pageviews.csv"
        df_gabungan.to_csv(output_file, index=False)
        print(f"\nSukses! Data pageviews berhasil disimpan ke '{output_file}'")
    else:
        print("\nTidak ada data yang berhasil diambil.")
