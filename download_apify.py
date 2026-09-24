import requests
import pandas as pd

# URL Metadata Run Apify Anda (Ganti tulisan YOUR_APIFY_TOKEN dengan token asli Anda)
RUN_URL = "https://api.apify.com/v2/actor-runs/BC34u0WcwILQMywhf?token=YOUR_APIFY_TOKEN"

print("Mencari ID Dataset Apify...")
res = requests.get(RUN_URL)
res.raise_for_status()

dataset_id = res.json()['data']['defaultDatasetId']
print(f"Dataset ID ditemukan: {dataset_id}")

# Mengunduh data CSV
# Mengambil token dari RUN_URL
token = RUN_URL.split("token=")[1]
csv_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=csv&token={token}"
print("Mengunduh data CSV...")
df = pd.read_csv(csv_url)

df.to_csv("apify_dataset.csv", index=False)
print(f"Sukses! {len(df)} baris data berhasil disimpan di 'apify_dataset.csv'")
