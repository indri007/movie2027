import pathlib
import json
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
import pymannkendall as mk

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRENDS_CSV = ROOT / "data/raw/google_trends/google_trends_film_horor_indonesia_2025_2026.csv"
MOVIES_CSV = ROOT / "data/processed/movies_clean.csv"

OUT_SUMMARY = ROOT / "data/processed/trends_horor_summary.json"
OUT_PEAKS = ROOT / "data/processed/trends_horor_peaks.csv"

OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)

df_trends = pd.read_csv(TRENDS_CSV)
df_trends["date"] = pd.to_datetime(df_trends["date"])
df_trends = df_trends.sort_values("date").reset_index(drop=True)

# 1. Rata-rata dan Median
mean_val = float(df_trends["interest"].mean())
median_val = float(df_trends["interest"].median())
min_val = int(df_trends["interest"].min())
max_val = int(df_trends["interest"].max())

# 2. Pola Bulanan (Rata-rata per Bulan)
df_trends["year_month"] = df_trends["date"].dt.strftime("%Y-%m")
monthly_grouped = df_trends.groupby("year_month")["interest"].agg(["count", "mean", "min", "max"]).round(2)
monthly_pattern = {}
for ym, row in monthly_grouped.iterrows():
    monthly_pattern[ym] = {
        "weeks_count": int(row["count"]),
        "mean_interest": float(row["mean"]),
        "min_interest": int(row["min"]),
        "max_interest": int(row["max"])
    }

# 3. 5 Minggu Puncak & Pengelompokan Periode Puncak Berurutan
top5_peaks = df_trends.sort_values(by=["interest", "date"], ascending=[False, True]).head(5)
top5_dates = sorted(top5_peaks["date"].tolist())

# Cek ketersediaan kolom tanggal rilis & bahasa di movies_clean.csv
df_movies = pd.read_csv(MOVIES_CSV, nrows=5)
available_cols = list(df_movies.columns)

has_release_date = "release_date" in available_cols or "tanggal_rilis" in available_cols
has_language = "language" in available_cols or "bahasa" in available_cols

movie_match_note = "not available"
if not has_release_date or not has_language:
    movie_match_note = (
        f"not available. Kolom yang tersedia di data/processed/movies_clean.csv: {available_cols}. "
        "Kolom spesifik tanggal rilis presisi mingguan dan bahasa tidak tersedia di skema dataset film saat ini."
    )

# Mengelompokkan minggu puncak berurutan (gap <= 7 hari) menjadi "Periode Puncak"
peak_periods = []
current_period = [top5_dates[0]]

for d in top5_dates[1:]:
    if (d - current_period[-1]).days <= 7:
        current_period.append(d)
    else:
        start_d = current_period[0].strftime("%Y-%m-%d")
        end_d = current_period[-1].strftime("%Y-%m-%d")
        peak_periods.append({
            "period": f"{start_d} s/d {end_d}" if start_d != end_d else start_d,
            "weeks_included": len(current_period),
            "max_interest_in_period": int(df_trends[df_trends["date"].isin(current_period)]["interest"].max())
        })
        current_period = [d]

if current_period:
    start_d = current_period[0].strftime("%Y-%m-%d")
    end_d = current_period[-1].strftime("%Y-%m-%d")
    peak_periods.append({
        "period": f"{start_d} s/d {end_d}" if start_d != end_d else start_d,
        "weeks_included": len(current_period),
        "max_interest_in_period": int(df_trends[df_trends["date"].isin(current_period)]["interest"].max())
    })

top5_peaks_records = []
for idx, r in top5_peaks.iterrows():
    top5_peaks_records.append({
        "rank": len(top5_peaks_records) + 1,
        "date": r["date"].strftime("%Y-%m-%d"),
        "interest": int(r["interest"]),
        "matched_film_releases": "not available"
    })

df_peaks = pd.DataFrame(top5_peaks_records)
df_peaks.to_csv(OUT_PEAKS, index=False)

# 4. Analisis Tren: OLS Biasa vs OLS Newey-West vs Mann-Kendall
x = np.arange(len(df_trends))
y = df_trends["interest"].values

# A. OLS Biasa (stats.linregress & sm.OLS)
X_const = sm.add_constant(x)
ols_model = sm.OLS(y, X_const).fit()

# B. OLS dengan Koreksi Heteroskedastisitas & Autokorelasi (Newey-West HAC, maxlags=4)
ols_nw = sm.OLS(y, X_const).fit(cov_type="HAC", cov_kwds={"maxlags": 4})

# C. Uji Non-parametrik Mann-Kendall
mk_result = mk.original_test(y)

trend_comparison = {
    "ols_standard": {
        "slope": round(float(ols_model.params[1]), 4),
        "intercept": round(float(ols_model.params[0]), 2),
        "std_error": round(float(ols_model.bse[1]), 4),
        "t_stat": round(float(ols_model.tvalues[1]), 3),
        "p_value": round(float(ols_model.pvalues[1]), 6),
        "r_squared": round(float(ols_model.rsquared), 4)
    },
    "ols_newey_west_hac_lag4": {
        "slope": round(float(ols_nw.params[1]), 4),
        "intercept": round(float(ols_nw.params[0]), 2),
        "std_error": round(float(ols_nw.bse[1]), 4),
        "t_stat": round(float(ols_nw.tvalues[1]), 3),
        "p_value": round(float(ols_nw.pvalues[1]), 6),
        "r_squared": round(float(ols_nw.rsquared), 4)
    },
    "mann_kendall_test": {
        "trend": mk_result.trend,
        "h": bool(mk_result.h),
        "p_value": round(float(mk_result.p), 6),
        "z_stat": round(float(mk_result.z), 3),
        "tau": round(float(mk_result.Tau), 4),
        "sen_slope": round(float(mk_result.slope), 4)
    }
}

caution_interpretation = (
    "CATATAN INTERPRETASI HATI-HATI (METHODOLOGICAL LIMITATION): "
    "Meskipun model OLS standar, OLS Newey-West (HAC lag=4), dan uji non-parametrik Mann-Kendall "
    f"sama-sama mengindikasikan penurunan signifikan (slope: {ols_model.params[1]:.4f}, MK p={mk_result.p:.5f}), "
    "rentang waktu 52 minggu (1 tahun) SECARA METODOLOGIS TIDAK CUKUP untuk memisahkan antara tren sekuler jangka panjang "
    "dan fluktuasi musiman tahunan (seasonal variation). Penurunan di paruh kedua dapat merefleksikan fase pasca-liburan "
    "atau pergeseran kalender rilis film horor nasional, bukan pelemahan minat permanen."
)

summary = {
    "keyword": "film horor Indonesia",
    "total_weeks": len(df_trends),
    "date_range": f"{df_trends['date'].min().strftime('%Y-%m-%d')} s/d {df_trends['date'].max().strftime('%Y-%m-%d')}",
    "mean_interest": round(mean_val, 2),
    "median_interest": round(median_val, 2),
    "min_interest": min_val,
    "max_interest": max_val,
    "monthly_pattern": monthly_pattern,
    "top_5_peaks": top5_peaks_records,
    "peak_periods_clustered": peak_periods,
    "trend_comparison": trend_comparison,
    "methodological_caution": caution_interpretation,
    "movie_cross_reference_status": movie_match_note
}

with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("=" * 75)
print("HASIL ANALISIS DESKRIPTIF & UJI TREN (DATA HOROR 52 MINGGU)")
print("=" * 75)
print(f"Rata-rata: {mean_val:.2f} | Median: {median_val:.2f} | Min: {min_val} | Max: {max_val}\n")

print("POLA BULANAN (Rata-rata Minat per Bulan):")
for k, v in monthly_pattern.items():
    print(f" - {k}: {v['mean_interest']:.2f} (n={v['weeks_count']} minggu, range: {v['min_interest']}-{v['max_interest']})")

print("\nPERIODE PUNCAK (Kelompok Minggu Berurutan):")
for p in peak_periods:
    print(f" - Periode {p['period']} ({p['weeks_included']} minggu) -> Nilai Puncak: {p['max_interest_in_period']}")

print("\nPERBANDINGAN UJI TREN STATISTIK:")
print(f"{'Metode':<25} | {'Slope':<10} | {'Std.Err':<10} | {'p-value':<12} | {'Interpretasi'}")
print("-" * 75)
print(f"{'OLS Biasa':<25} | {ols_model.params[1]:<10.4f} | {ols_model.bse[1]:<10.4f} | {ols_model.pvalues[1]:<12.6f} | {'Signifikan Turun' if ols_model.pvalues[1] < 0.05 else 'Tidak Signifikan'}")
print(f"{'OLS Newey-West (lag=4)':<25} | {ols_nw.params[1]:<10.4f} | {ols_nw.bse[1]:<10.4f} | {ols_nw.pvalues[1]:<12.6f} | {'Signifikan Turun (Robust)' if ols_nw.pvalues[1] < 0.05 else 'Tidak Signifikan'}")
print(f"{'Mann-Kendall (Sen Slope)':<25} | {mk_result.slope:<10.4f} | {'-':<10} | {mk_result.p:<12.6f} | {mk_result.trend.capitalize()}")

print(f"\n{caution_interpretation}\n")
print(f"✅ Ringkasan tersimpan di: {OUT_SUMMARY}")
