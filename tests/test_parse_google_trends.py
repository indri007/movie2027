from pathlib import Path
import pandas as pd
import pytest
from scripts.parse_google_trends import parse_trends_data

@pytest.fixture
def fixture_path():
    root = Path(__file__).resolve().parents[1]
    return root / "tests/fixtures/multi_keyword_monthly_TEST_FIXTURE.json"

@pytest.fixture
def tmp_output_paths(tmp_path):
    csv_out = tmp_path / "test_trends.csv"
    meta_out = tmp_path / "test_meta.json"
    return csv_out, meta_out

def test_multi_keyword_monthly_and_is_partial(fixture_path, tmp_output_paths):
    csv_out, meta_out = tmp_output_paths
    df, meta = parse_trends_data(fixture_path, csv_out, meta_out)

    # 1. Verifikasi Multi-Keyword (3 keywords)
    expected_keywords = ["film komedi Indonesia", "film drama Indonesia", "film animasi Indonesia"]
    assert len(meta["keywords"]) == 3
    assert meta["keywords"] == expected_keywords

    # 2. Verifikasi isPartial (titik ke-4 dengan isPartial=true harus diexclude)
    # 3 titik waktu valid * 3 keyword = 9 baris data
    assert len(df) == 9
    assert meta["excluded_partial_points"] == 1

    # 3. Verifikasi Granularity
    assert meta["granularity"] == "monthly"
    assert (df["granularity"] == "monthly").all()

    # 4. Verifikasi Kolom Wajib
    expected_cols = ["date", "keyword", "interest", "geo", "source", "granularity"]
    assert list(df.columns) == expected_cols

    # 5. Verifikasi Nilai Tertentu
    row_jan_komedi = df[(df["date"] == "2004-01-01") & (df["keyword"] == "film komedi Indonesia")]
    assert len(row_jan_komedi) == 1
    assert row_jan_komedi["interest"].iloc[0] == 12

    # 6. Verifikasi Geo Eksplisit
    assert meta["geo"] == "ID"
    assert meta["geo_source"] == "explicit_parameter"
