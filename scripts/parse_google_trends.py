import json
import pathlib
import pandas as pd
from datetime import datetime, timezone

def parse_trends_data(json_path, out_csv_path=None, out_meta_path=None):
    json_path = pathlib.Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    items = raw_data if isinstance(raw_data, list) else [raw_data]
    records = []
    keywords_found = []
    excluded_partial_count = 0
    
    geo_value = "not_specified"
    geo_source = "not_specified"
    sample_subregions = []

    for item in items:
        # 1. Deteksi Geo
        if "geo" in item and item["geo"]:
            geo_value = str(item["geo"])
            geo_source = "explicit_parameter"
        else:
            subregions = item.get("interestBySubregion", [])
            if subregions and isinstance(subregions, list):
                codes = [s.get("geoCode", "") for s in subregions if s.get("geoCode")]
                if codes:
                    sample_subregions = codes[:3]
                    if any(c.startswith("ID-") for c in codes):
                        geo_value = "ID"
                        geo_source = "inferred_from_subregion_codes"

        # 2. Parsing Keywords dari searchTerm / inputUrlOrTerm
        # Dukung multi-keyword (bisa list atau string dipisah koma)
        kw_list = []
        raw_term = item.get("searchTerm") or item.get("inputUrlOrTerm", "")
        if isinstance(raw_term, list):
            kw_list = [str(k).strip() for k in raw_term if str(k).strip()]
        elif isinstance(raw_term, str) and raw_term.strip():
            # Cek jika ada koma yang memisahkan keywords
            if "," in raw_term:
                kw_list = [k.strip() for k in raw_term.split(",") if k.strip()]
            else:
                kw_list = [raw_term.strip()]

        timeline = item.get("interestOverTime_timelineData", [])
        if not timeline:
            continue

        for pt in timeline:
            if pt.get("isPartial") is True:
                excluded_partial_count += 1
                continue

            # Wajib dari unix timestamp "time"
            ts = int(pt.get("time", 0))
            date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

            vals = pt.get("value", [])
            if not isinstance(vals, list):
                vals = [vals]

            # Verifikasi kesesuaian jumlah keyword dan value
            if len(kw_list) > 1 and len(vals) != len(kw_list):
                raise ValueError(
                    f"Jumlah keyword ({len(kw_list)}: {kw_list}) tidak sama dengan jumlah nilai ({len(vals)}: {vals}) pada time {date_str}!"
                )

            if len(kw_list) > 1:
                for q_idx, q_name in enumerate(kw_list):
                    if q_name not in keywords_found:
                        keywords_found.append(q_name)
                    records.append({
                        "date": date_str,
                        "keyword": q_name,
                        "interest": int(vals[q_idx]),
                        "geo": geo_value,
                        "source": "Apify Google Trends Scraper"
                    })
            else:
                q_name = kw_list[0] if kw_list else "unknown"
                if q_name not in keywords_found:
                    keywords_found.append(q_name)
                val = vals[0] if vals else 0
                records.append({
                    "date": date_str,
                    "keyword": q_name,
                    "interest": int(val),
                    "geo": geo_value,
                    "source": "Apify Google Trends Scraper"
                })

    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError("Dataframe hasil parsing kosong!")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["date", "keyword"]).reset_index(drop=True)

    # 3. Deteksi Granularity otomatis dari selisih hari
    unique_dates = pd.Series(df["date"].unique()).sort_values().reset_index(drop=True)
    if len(unique_dates) > 1:
        median_diff_days = (unique_dates.diff().dropna().dt.days).median()
        if median_diff_days <= 10:
            granularity = "weekly"
        elif median_diff_days >= 25:
            granularity = "monthly"
        else:
            granularity = f"custom_{int(median_diff_days)}d"
    else:
        granularity = "single_point"

    df["granularity"] = granularity
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    # Pastikan urutan kolom konsisten
    cols = ["date", "keyword", "interest", "geo", "source", "granularity"]
    df = df[cols]

    if out_csv_path:
        out_csv_path = pathlib.Path(out_csv_path)
        out_csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_csv_path, index=False)

    meta = {
        "status": "OFFICIAL_DATA_PARSED",
        "keywords": keywords_found,
        "geo": geo_value,
        "geo_source": geo_source,
        "sample_subregions": sample_subregions,
        "granularity": granularity,
        "timeframe": f"{df['date'].min()} to {df['date'].max()}",
        "total_observations": len(df),
        "excluded_partial_points": excluded_partial_count,
        "collection_timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

    if out_meta_path:
        out_meta_path = pathlib.Path(out_meta_path)
        out_meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    return df, meta

if __name__ == "__main__":
    ROOT = pathlib.Path(__file__).resolve().parents[1]
    DOWNLOADS = pathlib.Path.home() / "Downloads"
    OUT_CSV = ROOT / "data/raw/google_trends/google_trends_film_horor_indonesia_2025_2026.csv"
    OUT_META = ROOT / "data/raw/google_trends/google_trends_metadata.json"

    # Cari file scraper terbaru
    json_candidates = list(DOWNLOADS.glob("dataset_google-trends-scraper_*.json"))
    if not json_candidates:
        print("❌ Tidak ada file json Google Trends di Downloads.")
        exit(1)

    json_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    sel = json_candidates[0]
    print(f"📖 Memproses: {sel}")

    df, meta = parse_trends_data(sel, OUT_CSV, OUT_META)
    print(f"✅ Berhasil diparse: {len(df)} observasi.")
    print(f" - Granularity : {meta['granularity']}")
    print(f" - Geo         : {meta['geo']} ({meta['geo_source']})")
    print(f" - Parsial di-exclude: {meta['excluded_partial_points']}")
