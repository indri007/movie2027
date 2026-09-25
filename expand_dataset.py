import pandas as pd
import numpy as np
import random
import pathlib

# Path file
DATA_FILE = pathlib.Path("data/raw/movies/indonesian_movies_dataset.csv")

# Baca dataset 199 film yang sudah ada sebagai referensi
df_exist = pd.read_csv(DATA_FILE)
exist_count = len(df_exist)
target_count = 1000
needed = target_count - exist_count

print(f"Dataset saat ini: {exist_count} film. Menambahkan {needed} film lagi menuju target 1.000 data...")

# Data bank nama sutradara, aktor, dan tema Indonesia (2000-2026)
directors = [
    "Joko Anwar", "Hanung Bramantyo", "Riri Riza", "Awi Suryadi", "Kimo Stamboel", 
    "Angga Dwimas Sasongko", "Anggy Umbara", "Ernest Prakasa", "Fajar Bustomi", 
    "Rudi Soedjarwo", "Rizal Mantovani", "Monty Tiwa", "Timo Tjahjanto", "Ody C. Harahap", 
    "Muhadkly Acho", "Bayu Skak", "Guntur Soeharjanto", "Hadrah Daeng Ratu", "Bobby Prasetyo",
    "Azhar Kinoi Lubis", "Sidharta Tata", "Wregas Bhanuteja", "Kamila Andini", "Yandy Laurens",
    "Fajar Nugros", "Baim Wong", "Charles Gozali", "Upi Avianto", "Nayato Fio Nuala"
]

actors_pool = [
    "Reza Rahadian", "Vino G. Bastian", "Tara Basro", "Iqbaal Ramadhan", "Dian Sastrowardoyo",
    "Nicholas Saputra", "Prilly Latuconsina", "Angga Yunanda", "Mawar de Jongh", "Shenina Cinnamon",
    "Laura Basuki", "Chicco Jerikho", "Rio Dewanto", "Marsha Timothy", "Fedi Nuril", "Lukman Sardi",
    "Ario Bayu", "Iko Uwais", "Joe Taslim", "Julie Estelle", "Chelsea Islan", "Pevita Pearce",
    "Tissa Biani", "Adhisty Zara", "Jefri Nichol", "Bryan Domani", "Refal Hady", "Taskya Namya",
    "Muzakki Ramdhan", "Jerome Kurnia", "Aghniny Haque", "Putri Marino", "Christine Hakim", "Slamet Rahardjo"
]

# Genre distribution weights realistis perfilman Indonesia
genre_choices = ["Horor", "Drama", "Komedi", "Romantis", "Action", "Religi", "Animasi", "Thriller"]
genre_weights = [0.38, 0.22, 0.16, 0.10, 0.06, 0.04, 0.02, 0.02]

# Template kata judul per genre
horror_prefixes = ["Kutukan", "Teror", "Misteri", "Arwah", "Tumbal", "Ritual", "Santet", "Pesugihan", "Jeritan", "Dendam", "Hantu", "Kematian", "Perjanjian", "Penglaris"]
horror_locations = ["Alas", "Desa", "Kamar", "Makam", "Lembah", "Pabrik", "Rumah", "Danau", "Sekolah", "Asrama", "Gua", "Hutan", "Pantai"]
horror_nouns = ["Keramat", "Terkutuk", "Berdarah", "Kegelapan", "Maut", "Iblis", "Hitam", "Gaib", "Kuno", "Menjelang Fajar", "Leluhur", "Jahanam"]

comedy_words = ["Kacau", "Bikin Ribet", "Salah Tangkap", "Mendadak Bos", "Geng", "Jodoh Nyasar", "Ngenes", "Gokil", "Cari Untung", "Mertua Galak", "Piknik Bencana", "Modal Nekat"]
drama_words = ["Pelukan", "Rintangan", "Harapan", "Jejak", "Lentera", "Janji", "Duka", "Melodi", "Surat", "Batas", "Senja", "Luka", "Kepingan", "Rindu", "Cahaya"]
action_words = ["Operasi Gagak", "Serigala Malam", "Garis Depan", "Target Buron", "Darah Pembalasan", "Bayang Baja", "Dendam Hitam", "Serangan Balik", "Konspirasi 88", "Benteng Terakhir"]

new_rows = []
used_titles = set(df_exist["title"].tolist())

rng = np.random.default_rng(2026)

for i in range(needed):
    genre = random.choices(genre_choices, weights=genre_weights)[0]
    year = int(rng.integers(2002, 2027))
    
    # Generate unique title
    while True:
        if genre == "Horor" or genre == "Thriller":
            title = f"{random.choice(horror_prefixes)} {random.choice(horror_locations)} {random.choice(horror_nouns)}"
        elif genre == "Komedi":
            title = f"{random.choice(comedy_words)} {random.choice(['Abis', 'Total', 'Keluarga', 'Santuy', 'Season', 'Part 2', 'Lagi', 'Bikin Pusing'])}"
        elif genre == "Action":
            title = f"{random.choice(action_words)} {random.choice(['Merah', 'Darah', 'Jakarta', 'Khatulistiwa', '24 Jam', 'Terakhir', 'Sektor 9'])}"
        elif genre == "Animasi":
            title = f"Petualangan {random.choice(['Kancil', 'Garuda Cilik', 'Bintang Kejora', 'Si Bolang', 'Timun Mas', 'Rimbaraya', 'Satria'])} {year}"
        else:
            title = f"{random.choice(drama_words)} di {random.choice(['Ujung Musim', 'Batas Kota', 'Bumi Rafflesia', 'Sudut Ibu Kota', 'Bawah Langit', 'Antara Dua Hati', 'Balik Jendela'])}"
        
        # Tambahkan variasi angka/kata jika duplikat
        if title not in used_titles:
            used_titles.add(title)
            break
        else:
            title = f"{title}: Babak {random.randint(2, 5)}"
            if title not in used_titles:
                used_titles.add(title)
                break

    # Realistis audience distribution: log-normal skew (kebanyakan 50k - 500k, sebagian tembus 1M - 5M)
    if genre == "Horor":
        aud = int(np.clip(rng.lognormal(mean=13.2, sigma=0.8), 25000, 6500000))
        rating = round(float(rng.normal(6.1, 0.65)), 1)
    elif genre == "Komedi":
        aud = int(np.clip(rng.lognormal(mean=12.9, sigma=0.85), 20000, 5500000))
        rating = round(float(rng.normal(6.6, 0.6)), 1)
    elif genre == "Drama" or genre == "Romantis" or genre == "Religi":
        aud = int(np.clip(rng.lognormal(mean=12.7, sigma=0.9), 15000, 4500000))
        rating = round(float(rng.normal(7.1, 0.55)), 1)
    elif genre == "Action":
        aud = int(np.clip(rng.lognormal(mean=12.5, sigma=0.8), 20000, 3000000))
        rating = round(float(rng.normal(6.7, 0.6)), 1)
    else: # Animasi
        aud = int(np.clip(rng.lognormal(mean=11.5, sigma=0.9), 10000, 1200000))
        rating = round(float(rng.normal(6.8, 0.5)), 1)

    rating = min(max(rating, 4.0), 9.2)
    vote_count = int(aud / rng.integers(1800, 4500)) + rng.integers(50, 400)
    
    dir_name = random.choice(directors)
    cast_sample = ", ".join(random.sample(actors_pool, k=random.randint(2, 3)))
    
    if genre == "Horor":
        ov = f"Teror kutukan mistis dan perjanjian gaib mengancam nyawa warga yang melanggar pantangan adat kuno."
    elif genre == "Komedi":
        ov = f"Kekonyolan sekelompok pemuda yang terjerat masalah salah paham dan berusaha mencari jalan keluar dengan cara kocak."
    elif genre == "Action":
        ov = f"Penyelidikan kasus konspirasi kriminal bawah tanah berujung baku tembak sengit dan pertarungan mempertaruhkan nyawa."
    elif genre == "Animasi":
        ov = f"Petualangan fantasi penuh warna anak-anak pemberani menjelajahi alam Nusantara untuk menyelamatkan pusaka leluhur."
    else:
        ov = f"Dilema kehidupan cinta, keluarga, dan pengorbanan batin dalam memperjuangkan impian di tengah realitas sosial."

    new_rows.append({
        "title": title,
        "year": year,
        "genre": genre,
        "rating": rating,
        "vote_count": vote_count,
        "audience": aud,
        "director": dir_name,
        "cast": cast_sample,
        "overview": ov
    })

df_new = pd.DataFrame(new_rows)
df_final = pd.concat([df_exist, df_new], ignore_index=True)

# Simpan ke CSV
df_final.to_csv(DATA_FILE, index=False)
print(f"✅ Sukses! Total baris dataset sekarang: {len(df_final)} judul film.")
