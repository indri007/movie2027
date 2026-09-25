from pathlib import Path
import json
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/processed/movies_master.csv"
OUTPUT = ROOT / "data/processed/movies_clean.csv"
REPORT = ROOT / "data/processed/audit/cleaning_report.json"

df = pd.read_csv(SOURCE)

original_rows = len(df)
original_columns = list(df.columns)

numeric_columns = [
    "year",
    "rating",
    "vote_count",
    "audience",
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

string_columns = [
    "title",
    "genre",
    "director",
    "cast",
    "overview",
]

for col in string_columns:
    if col in df.columns:
        df[col] = df[col].astype("string").str.strip()

if "genre" in df.columns:
    df["genre"] = (
        df["genre"]
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

duplicate_title_year = int(
    df.duplicated(subset=["title", "year"]).sum()
)

# Conservative cleaning:
# do not delete rows solely because rating/audience/etc. are missing.
df = df.drop_duplicates(
    subset=["title", "year"],
    keep="first"
).reset_index(drop=True)

report = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "source": str(SOURCE),
    "output": str(OUTPUT),
    "original_rows": int(original_rows),
    "clean_rows": int(len(df)),
    "rows_removed": int(original_rows - len(df)),
    "duplicate_title_year_found": duplicate_title_year,
    "columns": original_columns,
    "missing_values_after_cleaning": {
        str(k): int(v) for k, v in df.isna().sum().items()
    },
    "note": (
        "No values were fabricated or imputed. "
        "Rows were not removed because rating/audience/etc. were missing."
    ),
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(OUTPUT, index=False)
REPORT.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"Original rows : {original_rows:,}")
print(f"Clean rows    : {len(df):,}")
print(f"Removed       : {original_rows - len(df):,}")
print(f"Output        : {OUTPUT}")
print(f"Report        : {REPORT}")
