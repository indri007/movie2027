import json
import random
import pathlib
import pandas as pd
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "data/raw/google_trends/google_trends_film_horor_indonesia_2025_2026.csv"
DOWNLOADS = pathlib.Path.home() / "Downloads"

json_files = list(DOWNLOADS.glob("dataset_google-trends-scraper_*.json"))
json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
JSON_FILE = json_files[0]

df = pd.read_csv(CSV_FILE)
with open(JSON_FILE) as f:
    raw = json.load(f)[0]

timeline = raw["interestOverTime_timelineData"]
time_map = {
    datetime.fromtimestamp(int(p["time"]), tz=timezone.utc).strftime("%Y-%m-%d"): p["value"][0]
    for p in timeline
}

random.seed(42)
sample_dates = random.sample(list(df["date"]), 3)

print("=== HASIL VERIFIKASI MANUAL 3 BARIS ACAK ===")
print(f"{'Tanggal':<12} | {'Keyword':<22} | {'Nilai CSV':<10} | {'Nilai JSON':<12} | {'Status'}")
print("-" * 75)
for d in sorted(sample_dates):
    csv_val = df[df["date"] == d]["interest"].iloc[0]
    json_val = time_map.get(d)
    status = "COCOK (PASS)" if csv_val == json_val else "BEDA (FAIL)"
    print(f"{d:<12} | {'film horor Indonesia':<22} | {csv_val:<10} | {json_val:<12} | {status}")
