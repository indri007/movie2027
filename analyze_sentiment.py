import pandas as pd
from transformers import pipeline
import torch
import glob
import time

def process_sentiment(csv_file):
    print(f"Memuat model sentimen IndoBERT... (Ini mungkin memakan waktu untuk unduhan pertama)")
    
    # Gunakan GPU jika tersedia, jika tidak pakai CPU
    device = 0 if torch.cuda.is_available() else (0 if torch.backends.mps.is_available() else -1)
    
    # Menggunakan model bahasa Indonesia yang sudah di-fine-tune untuk sentimen
    sentiment_model = pipeline(
        "sentiment-analysis", 
        model="w11wo/indonesian-roberta-base-sentiment-classifier",
        device=device
    )
    
    print(f"Membaca file data: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # Hanya memproses komentar yang tidak kosong
    df = df.dropna(subset=['text'])
    
    # Batasi analisis jika data terlalu besar untuk percobaan pertama
    # Hapus baris di bawah ini jika ingin memproses semua 8000 komentar sekaligus
    # df = df.head(1000) 
    
    print(f"Mulai memproses {len(df)} komentar...")
    start_time = time.time()
    
    # Fungsi bantu untuk memproses teks panjang
    def get_sentiment(text):
        try:
            # Model BERT biasanya memiliki limit 512 token
            # Kita potong teks agar tidak melebihi batas tersebut
            short_text = str(text)[:500] 
            result = sentiment_model(short_text)[0]
            return result['label'], result['score']
        except Exception as e:
            return "ERROR", 0.0

    # Memproses dengan progress indicator
    labels = []
    scores = []
    
    for i, text in enumerate(df['text']):
        label, score = get_sentiment(text)
        labels.append(label)
        scores.append(score)
        
        if (i + 1) % 100 == 0:
            print(f"[{i + 1}/{len(df)}] komentar dianalisis...")

    df['sentiment_label'] = labels
    df['sentiment_score'] = scores
    
    # Menghitung agregat skor untuk film ini (sebagai fitur prediksi)
    # Anggap 'positive' = 1, 'neutral' = 0, 'negative' = -1
    def convert_to_numeric(label):
        if label.lower() == 'positive': return 1
        elif label.lower() == 'negative': return -1
        return 0
        
    df['sentiment_value'] = df['sentiment_label'].apply(convert_to_numeric)
    
    # Simpan hasil lengkap
    out_file = csv_file.replace('.csv', '_sentiment.csv')
    df.to_csv(out_file, index=False)
    
    # Cetak Kesimpulan
    print(f"\n✅ Selesai dalam {time.time() - start_time:.2f} detik!")
    print(f"Hasil disimpan di: {out_file}")
    
    print("\n--- RINGKASAN SENTIMEN TRAILER ---")
    print(df['sentiment_label'].value_counts(normalize=True).map('{:.1%}'.format))
    
    agregat = df['sentiment_value'].mean()
    print(f"Skor Sentimen Keseluruhan (-1 hingga 1): {agregat:.3f}")
    if agregat > 0.3:
        print("💡 Interpretasi: Publik sangat antusias / ulasan sangat positif!")
    elif agregat < -0.1:
        print("💡 Interpretasi: Banyak kritik atau respons negatif terhadap trailer.")
    else:
        print("💡 Interpretasi: Respons publik netral atau terbelah.")

if __name__ == "__main__":
    # Mencari file csv keluaran dari youtube scraper
    target_files = glob.glob("youtube_comments_*_no_api.csv")
    
    if not target_files:
        print("❌ File CSV komentar YouTube tidak ditemukan.")
        print("Pastikan Anda sudah menjalankan 'youtube_scraper_no_api.py' terlebih dahulu.")
    else:
        # Proses file pertama yang ditemukan
        process_sentiment(target_files[0])
