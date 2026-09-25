from pathlib import Path
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

OUT_DIR = ROOT / "data/raw/google_trends"
OUT_DIR.mkdir(parents=True, exist_ok=True)

keywords = [
    "film Indonesia",
    "film horor Indonesia",
    "film komedi Indonesia",
    "film drama Indonesia",
    "film animasi Indonesia",
]

metadata = {
    "status": "PENDING_OFFICIAL_CSV_IMPORT",
    "keywords": keywords,
    "geo": "ID",
    "timeframe": "2000-01-01 2026-12-31",
    "search_type": "web",
    "category": "Movies if available in Google Trends interface",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_policy": (
        "Use official Google Trends exported CSV. "
        "Do not fabricate observations."
    ),
}

path = OUT_DIR / "google_trends_metadata.json"
path.write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"Metadata created: {path}")
print()
print("Google Trends data is intentionally NOT fabricated.")
print("Export the five keywords from Google Trends and import the official CSV.")
