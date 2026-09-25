import sys
import time
import random
import pathlib
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

BASE = pathlib.Path(__file__).parent
DATA_DIR = BASE / "data"
RAW_TRENDS = DATA_DIR / "raw" / "google_trends"
PROCESSED = DATA_DIR / "processed"
OUTPUTS = DATA_DIR / "outputs"
KW_FILE = BASE / "keywords.csv"

# Target 5 keywords utama:
# 1 baseline: 'film indonesia'
# 4 genre: 'film horor indonesia', 'film komedi indonesia', 'film drama indonesia', 'film animasi indonesia'
TIMEFRAME = "all"      # 2004 - sekarang (cakupan historis maksimal Google Trends)
GEO = "ID"             # Indonesia
CATEGORY = 34          # Arts & Entertainment > Movies

def fetch():
    from pytrends.request import TrendReq

    RAW_TRENDS.mkdir(parents=True, exist_ok=True)
    if not KW_FILE.exists():
        sys.exit(f"File {KW_FILE} tidak ditemukan!")

    kw_df = pd.read_csv(KW_FILE)
    keywords = kw_df["keyword"].tolist()

    print(f"Target kata kunci ({len(keywords)}): {keywords}")
    print(f"Parameter: Geo={GEO}, Category={CATEGORY}, Timeframe={TIMEFRAME}")

    py = TrendReq(hl="id-ID", tz=-420, timeout=(15, 45))

    # Google Trends memperbolehkan maksimal 5 kata kunci dalam 1 payload perbandingan langsung.
    # Karena tepat 5 kata kunci, kita bisa menariknya sekaligus dalam 1 request langsung terstandardisasi!
    out_file = RAW_TRENDS / "trends_5_genres_2004_2026.csv"

    for attempt in range(6):
        try:
            print(f"Mengambil data Google Trends (Percobaan {attempt + 1}/6)...")
            py.build_payload(keywords, cat=CATEGORY, timeframe=TIMEFRAME, geo=GEO)
            df = py.interest_over_time()

            if df.empty:
                raise RuntimeError("Respon dari Google Trends kosong.")

            df = df.drop(columns=["isPartial"], errors="ignore")
            df.to_csv(out_file)
            print(f"✅ Berhasil mengunduh tren minat bulanan! Disimpan di: {out_file}")
            break
        except Exception as e:
            wait = 20 * (2 ** attempt) + random.uniform(2, 6)
            print(f"Gagal mengambil data ({e}). Menunggu {wait:.1f} detik sebelum mencoba lagi...")
            time.sleep(wait)
    else:
        print("❌ Gagal mengunduh setelah 6 percobaan (kemungkinan rate limit Google 429).")
        print("Silakan jalankan kembali perintah ini setelah beberapa saat.")
        sys.exit(1)

    # Ambil related queries untuk masing-masing genre
    print("\nMengambil kueri terkait (rising/top) untuk tiap genre...")
    for kw in keywords:
        safe_name = "".join(c if c.isalnum() else "_" for c in kw)[:50]
        rel_file = RAW_TRENDS / f"related_{safe_name}.csv"
        if rel_file.exists():
            continue
        try:
            py.build_payload([kw], cat=CATEGORY, timeframe=TIMEFRAME, geo=GEO)
            rq = py.related_queries().get(kw, {})
            parts = []
            for kind in ("top", "rising"):
                d = rq.get(kind)
                if d is not None and not d.empty:
                    parts.append(d.assign(tipe=kind, keyword=kw))
            if parts:
                pd.concat(parts).to_csv(rel_file, index=False)
                print(f"  -> Kueri terkait tersimpan: {kw}")
            time.sleep(random.uniform(3, 7))
        except Exception as err:
            print(f"  -> Lewati related query {kw}: {err}")

    print("\nProses pengambilan Google Trends selesai!")


def analyze():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    RAW_TRENDS.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    trend_file = RAW_TRENDS / "trends_5_genres_2004_2026.csv"
    if not trend_file.exists():
        print(f"File {trend_file} belum ada. Jalankan 'python trends_film_id.py fetch' atau 'demo' dulu.")
        return

    df = pd.read_csv(trend_file, parse_dates=["date"]).set_index("date")
    print(f"Memproses data dari {df.index.min().strftime('%Y-%m')} s/d {df.index.max().strftime('%Y-%m')}...")

    # Simpan dataset bulanan bersih ke data/processed/
    df.to_csv(PROCESSED / "trends_genres_processed.csv")

    # 1. Rata-rata tahunan
    yearly = df.groupby(df.index.year).mean().round(2)
    yearly.to_csv(PROCESSED / "trends_yearly_summary.csv")

    # 2. Forecasting 2027 menggunakan Holt-Winters
    forecast_results = []
    fig, ax = plt.subplots(figsize=(12, 6))

    horizon_end = pd.Timestamp("2027-12-31")

    for col in df.columns:
        s = df[col].asfreq("MS", method="ffill").clip(lower=0.01)
        steps = int((horizon_end.year - s.index[-1].year) * 12 + (horizon_end.month - s.index[-1].month))
        
        try:
            m = ExponentialSmoothing(s, trend="add", seasonal="add", seasonal_periods=12).fit()
            f = m.forecast(steps)
        except Exception:
            # Fallback jika dekomposisi musiman gagal
            m = ExponentialSmoothing(s, trend="add").fit()
            f = m.forecast(steps)

        hist_mean = s.iloc[-12:].mean()
        pred_2027_mean = f[f.index.year == 2027].mean()
        pct_change = ((pred_2027_mean / hist_mean) - 1) * 100

        forecast_results.append({
            "keyword": col,
            "rerata_12_bulan_terakhir": round(hist_mean, 2),
            "proyeksi_rerata_2027": round(pred_2027_mean, 2),
            "pertumbuhan_%": round(pct_change, 2)
        })

        line, = ax.plot(s.index, s.values, lw=1.2, label=col)
        ax.plot(f.index, f.values, ls="--", lw=1.5, color=line.get_color())

    ax.axvline(df.index[-1], color="gray", linestyle=":", label="Mulai Prediksi")
    ax.set_title("Tren Minat Pencarian Film Indonesia (2004–2026) & Proyeksi 2027")
    ax.set_ylabel("Skor Indeks Relatif (0–100)")
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout()
    chart_path = OUTPUTS / "grafik_tren_dan_forecasting_2027.png"
    fig.savefig(chart_path, dpi=180)
    plt.close(fig)

    fc_df = pd.DataFrame(forecast_results).sort_values("proyeksi_rerata_2027", ascending=False)
    fc_df.to_csv(OUTPUTS / "proyeksi_genre_2027.csv", index=False)

    print("\n=== HASIL PROYEKSI TREN GENRE FILM 2027 ===")
    print(fc_df.to_string(index=False))
    print(f"\n✅ Grafik disimpan di: {chart_path}")
    print(f"✅ File hasil disimpan di folder {OUTPUTS}/")


def demo():
    """Membuat data historis sintetis 2004-2026 untuk menguji alur analisis & visualisasi tanpa perlu internet."""
    RAW_TRENDS.mkdir(parents=True, exist_ok=True)
    idx = pd.date_range(start="2004-01-01", end="2026-06-01", freq="MS")
    n = len(idx)
    rng = np.random.default_rng(42)

    data = {
        "date": idx,
        "film indonesia": np.clip(np.linspace(15, 65, n) + rng.normal(0, 5, n), 5, 100).round(),
        "film horor indonesia": np.clip(np.linspace(10, 85, n) + 10 * np.sin(np.linspace(0, 8*np.pi, n)) + rng.normal(0, 4, n), 2, 100).round(),
        "film komedi indonesia": np.clip(np.linspace(15, 45, n) + rng.normal(0, 4, n), 2, 80).round(),
        "film drama indonesia": np.clip(np.linspace(25, 40, n) + rng.normal(0, 3, n), 2, 80).round(),
        "film animasi indonesia": np.clip(np.linspace(5, 30, n) + rng.normal(0, 3, n), 1, 60).round(),
    }
    df = pd.DataFrame(data)
    df.to_csv(RAW_TRENDS / "trends_5_genres_2004_2026.csv", index=False)
    print("✅ Data simulasi 2004–2026 berhasil dibuat.")
    analyze()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    if cmd == "fetch":
        fetch()
    elif cmd == "demo":
        demo()
    else:
        analyze()
