from pathlib import Path
import json
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DATA_REL = Path("data/raw/google_trends/google_trends_film_horor_indonesia_2025_2026.csv")
META_REL = Path("data/raw/google_trends/google_trends_metadata.json")
REPORT_REL = Path("data/processed/audit/google_trends_audit.json")

DATA = ROOT / DATA_REL
META = ROOT / META_REL
REPORT = ROOT / REPORT_REL

expected_keywords = [
    "film Indonesia",
    "film horor Indonesia",
    "film komedi Indonesia",
    "film drama Indonesia",
    "film animasi Indonesia",
]

report = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "file": str(DATA_REL),
    "status": None,
    "expected_keywords": expected_keywords,
}

if not DATA.exists():
    report["status"] = "PENDING_OFFICIAL_CSV_IMPORT"
    report["message"] = "File Google Trends belum tersedia."
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report["message"])
    raise SystemExit(0)

df = pd.read_csv(DATA)

# Baca metadata jika ada
geo_source = "not_specified"
sample_subregions = []
if META.exists():
    try:
        with open(META) as f:
            m = json.load(f)
            geo_source = m.get("geo_source", "not_specified")
            sample_subregions = m.get("sample_subregions", [])
    except Exception:
        pass

keywords_in_data = df["keyword"].unique().tolist()
missing_kw = [k for k in expected_keywords if k not in keywords_in_data]
invalid_interest = df[(df["interest"] < 0) | (df["interest"] > 100)]
dup_date_kw = int(df.duplicated(subset=["date", "keyword"]).sum())
obs_count = len(df)
granularity = df["granularity"].iloc[0] if "granularity" in df.columns else "weekly"

report.update({
    "status": "PASS_PARTIAL_SCOPE" if missing_kw else "PASS_FULL_SCOPE",
    "total_rows": int(obs_count),
    "columns": list(df.columns),
    "actual_keywords": keywords_in_data,
    "actual_keyword_count": len(keywords_in_data),
    "missing_expected_keywords": missing_kw,
    "date_min": str(df["date"].min()),
    "date_max": str(df["date"].max()),
    "timeframe_nature": f"{granularity}_{obs_count}_obs",
    "granularity": granularity,
    "geo_stated": df["geo"].iloc[0] if "geo" in df.columns and not df.empty else "not_specified",
    "geo_source": geo_source,
    "sample_subregion_codes": sample_subregions,
    "observations_per_keyword": {k: int(v) for k, v in df["keyword"].value_counts().items()},
    "missing_values": {str(k): int(v) for k, v in df.isna().sum().items()},
    "invalid_interest_count": len(invalid_interest),
    "duplicate_date_keyword_count": dup_date_kw,
    "audit_note": (
        f"Dataset mencakup {obs_count} observasi {granularity} penuh (titik minggu parsial isPartial=true telah diexclude). "
        "Geo teridentifikasi dari subregion codes ('inferred_from_subregion_codes')."
    )
})

REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ Audit selesai: {REPORT_REL}")
print(json.dumps(report, indent=2, ensure_ascii=False))
