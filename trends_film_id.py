"""
trends_film_id.py — Riset minat film Indonesia 5 tahun terakhir dari Google Trends
==================================================================================
Jalankan di LAPTOP (Google Trends memblokir akses dari server cloud).

    pip install pytrends pandas statsmodels matplotlib openpyxl
    python trends_film_id.py fetch      # ambil data (±10–20 menit, bisa dilanjut kalau terputus)
    python trends_film_id.py analyze    # analisis + prediksi 2027 -> hasil/
    python trends_film_id.py demo       # uji alur analisis dengan data sintetis (tanpa internet)

Daftar kata kunci ada di keywords.csv — tambah/ubah sesuka Anda
(kolom: keyword, jenis[genre|platform|judul], genre, tahun_rilis, platform).

CATATAN METODE (tulis di bagian Metodologi paper):
- Google Trends memberi skor RELATIF 0–100 per permintaan, maks 5 kata kunci per permintaan.
  Agar antar-batch bisa dibandingkan, setiap batch memuat satu kata kunci JANGKAR ("bioskop")
  dan semua nilai diskalakan ulang: indeks = nilai / rata-rata jangkar di batch itu x 100.
- Rentang "today 5-y" menghasilkan data MINGGUAN, geo = ID (Indonesia), kategori 34 (Movies).
- Trends mengukur PERHATIAN/PENCARIAN, bukan jumlah penonton atau penjualan tiket.
"""

import sys
import time
import random
import pathlib
import warnings

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

BASE = pathlib.Path(__file__).parent
RAW = BASE / "raw_trends"
OUT = BASE / "hasil"
KW_FILE = BASE / "keywords.csv"

ANCHOR = "bioskop"
GEO = "ID"
TIMEFRAME = "today 5-y"
CATEGORY = 34          # Google Trends: Arts & Entertainment > Movies
BATCH = 4              # 4 kata kunci + 1 jangkar = 5 (batas Google Trends)


# ─────────────────────────────── FETCH ───────────────────────────────
def _safe(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name)[:60]


def fetch():
    from pytrends.request import TrendReq

    RAW.mkdir(exist_ok=True)
    kw = pd.read_csv(KW_FILE)
    terms = [k for k in kw["keyword"].tolist() if k.lower() != ANCHOR]
    batches = [terms[i:i + BATCH] for i in range(0, len(terms), BATCH)]

    py = TrendReq(hl="id-ID", tz=-420, timeout=(10, 30))

    for bi, batch in enumerate(batches, 1):
        f = RAW / f"iot_batch_{bi:02d}.csv"
        if f.exists():
            print(f"[{bi}/{len(batches)}] sudah ada, lewati: {batch}")
            continue
        for attempt in range(6):
            try:
                py.build_payload(batch + [ANCHOR], cat=CATEGORY, timeframe=TIMEFRAME, geo=GEO)
                df = py.interest_over_time()
                if df.empty:
                    raise RuntimeError("respon kosong")
                df.drop(columns=["isPartial"], errors="ignore").to_csv(f)
                print(f"[{bi}/{len(batches)}] OK: {batch}")
                break
            except Exception as e:
                wait = 30 * (2 ** attempt) + random.uniform(0, 10)
                print(f"[{bi}/{len(batches)}] gagal ({e}); coba lagi dalam {wait:.0f} dtk")
                time.sleep(wait)
        else:
            sys.exit(f"Berhenti di batch {bi}. Jalankan ulang nanti — batch yang sudah selesai tidak diulang.")
        time.sleep(random.uniform(8, 15))

    # Kueri terkait (top & rising) untuk kata kunci genre -> judul/tema yang sedang naik daun
    genres = kw.loc[kw["jenis"] == "genre", "keyword"].tolist()
    for g in genres:
        f = RAW / f"related_{_safe(g)}.csv"
        if f.exists():
            continue
        for attempt in range(6):
            try:
                py.build_payload([g], cat=CATEGORY, timeframe=TIMEFRAME, geo=GEO)
                rq = py.related_queries().get(g, {})
                parts = []
                for kind in ("top", "rising"):
                    d = rq.get(kind)
                    if d is not None and not d.empty:
                        parts.append(d.assign(tipe=kind, genre_keyword=g))
                (pd.concat(parts) if parts else pd.DataFrame()).to_csv(f, index=False)
                print(f"related OK: {g}")
                break
            except Exception as e:
                wait = 30 * (2 ** attempt)
                print(f"related gagal {g} ({e}); tunggu {wait} dtk")
                time.sleep(wait)
        time.sleep(random.uniform(8, 15))
    print("\nSelesai. Lanjut: python trends_film_id.py analyze")


# ───────────────────────────── COMBINE ─────────────────────────────
def load_combined() -> pd.DataFrame:
    """Gabungkan semua batch dan skalakan ulang terhadap jangkar."""
    frames = []
    for f in sorted(RAW.glob("iot_batch_*.csv")):
        df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        a = df[ANCHOR].mean()
        if a == 0:
            print(f"PERINGATAN: jangkar = 0 di {f.name}, batch dilewati")
            continue
        frames.append(df.drop(columns=[ANCHOR]) / a * 100)
    if not frames:
        sys.exit("Tidak ada data di raw_trends/. Jalankan 'fetch' atau 'demo' dulu.")
    out = pd.concat(frames, axis=1)
    return out.loc[:, ~out.columns.duplicated()]


# ───────────────────────────── ANALYZE ─────────────────────────────
def analyze():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    OUT.mkdir(exist_ok=True)
    kw = pd.read_csv(KW_FILE)
    data = load_combined()
    data.to_csv(OUT / "01_indeks_mingguan_gabungan.csv")

    meta = kw.set_index("keyword")
    genre_cols = [k for k in kw.loc[kw.jenis == "genre", "keyword"] if k in data]
    plat_cols = [k for k in kw.loc[kw.jenis == "platform", "keyword"] if k in data]
    title_cols = [k for k in kw.loc[kw.jenis == "judul", "keyword"] if k in data]

    # 1) Minat genre per tahun
    yearly = data[genre_cols].groupby(data.index.year).mean().round(1)
    share = (yearly.div(yearly.sum(axis=1), axis=0) * 100).round(1)

    # 2) Bioskop vs Netflix
    plat_yearly = data[plat_cols].groupby(data.index.year).mean().round(1) if plat_cols else pd.DataFrame()

    # 3) Judul: puncak minat
    rows = []
    for t in title_cols:
        s = data[t]
        rows.append({
            "judul": t,
            "genre": meta.at[t, "genre"],
            "tahun_rilis": meta.at[t, "tahun_rilis"],
            "platform": meta.at[t, "platform"],
            "puncak_indeks": round(s.max(), 1),
            "minggu_puncak": s.idxmax().date(),
            "total_minat_52mg_sejak_puncak": round(s.loc[s.idxmax():].head(52).sum(), 1),
        })
    titles = pd.DataFrame(rows).sort_values("puncak_indeks", ascending=False)
    genre_from_titles = (titles.groupby("genre")["total_minat_52mg_sejak_puncak"]
                         .agg(["count", "mean"]).round(1)
                         .rename(columns={"count": "jumlah_judul", "mean": "rata2_minat"})
                         .sort_values("rata2_minat", ascending=False)) if not titles.empty else pd.DataFrame()

    # 4) Musiman: bulan dengan minat tertinggi per genre
    monthly = data[genre_cols].groupby(data.index.month).mean().round(1)
    monthly.index.name = "bulan"

    # 5) Prediksi 2027 + backtest jujur (tahan 52 minggu terakhir)
    fc_rows, fc_series = [], {}
    horizon_end = pd.Timestamp("2027-12-31")
    for g in genre_cols:
        s = data[g].asfreq("W-SUN", method="ffill").clip(lower=0.01)
        # backtest
        train, test = s.iloc[:-52], s.iloc[-52:]
        try:
            m_bt = ExponentialSmoothing(train, trend="add", damped_trend=True,
                                        seasonal="mul", seasonal_periods=52).fit()
            pred = m_bt.forecast(52)
            naive = train.iloc[-52:].values  # seasonal naive
            mape_model = float(np.mean(np.abs((test.values - pred.values) / test.values)) * 100)
            mape_naive = float(np.mean(np.abs((test.values - naive) / test.values)) * 100)
        except Exception:
            mape_model = mape_naive = np.nan
        # model penuh
        steps = int((horizon_end - s.index[-1]).days // 7) + 1
        m = ExponentialSmoothing(s, trend="add", damped_trend=True,
                                 seasonal="mul", seasonal_periods=52).fit()
        f = m.forecast(steps)
        fc_series[g] = f
        last12 = s.iloc[-52:].mean()
        y2027 = f[f.index.year == 2027].mean()
        fc_rows.append({
            "genre_keyword": g,
            "rata2_12bln_terakhir": round(last12, 1),
            "prediksi_rata2_2027": round(y2027, 1),
            "perubahan_%": round((y2027 / last12 - 1) * 100, 1),
            "MAPE_backtest_model_%": round(mape_model, 1),
            "MAPE_backtest_naive_%": round(mape_naive, 1),
            "model_lebih_baik_dari_naive": bool(mape_model < mape_naive) if not np.isnan(mape_model) else None,
        })
    forecast = pd.DataFrame(fc_rows).sort_values("prediksi_rata2_2027", ascending=False)

    # 6) Kueri terkait (rising) — judul/tema yang sedang naik
    rel = [pd.read_csv(f) for f in RAW.glob("related_*.csv") if f.stat().st_size > 5]
    related = pd.concat(rel, ignore_index=True) if rel else pd.DataFrame()

    # ── Simpan Excel
    with pd.ExcelWriter(OUT / "hasil_trends_film_indonesia.xlsx") as xw:
        yearly.to_excel(xw, sheet_name="genre_per_tahun")
        share.to_excel(xw, sheet_name="pangsa_genre_%")
        monthly.to_excel(xw, sheet_name="musiman_bulan")
        if not plat_yearly.empty:
            plat_yearly.to_excel(xw, sheet_name="bioskop_vs_netflix")
        titles.to_excel(xw, sheet_name="judul_puncak", index=False)
        if not genre_from_titles.empty:
            genre_from_titles.to_excel(xw, sheet_name="genre_dari_judul")
        forecast.to_excel(xw, sheet_name="prediksi_2027", index=False)
        if not related.empty:
            related.to_excel(xw, sheet_name="kueri_terkait", index=False)
        data.to_excel(xw, sheet_name="data_mingguan")

    # ── Grafik
    fig, ax = plt.subplots(figsize=(11, 5))
    data[genre_cols].rolling(4).mean().plot(ax=ax, lw=1.4)
    ax.set_title("Minat pencarian genre film di Indonesia (rata-rata bergerak 4 minggu)")
    ax.set_ylabel(f"Indeks (rata-rata '{ANCHOR}' = 100)"); ax.set_xlabel("")
    fig.tight_layout(); fig.savefig(OUT / "g1_tren_genre.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    for g in genre_cols:
        hist = data[g].rolling(4).mean()
        line, = ax.plot(hist.index, hist.values, lw=1.2, label=g)
        ax.plot(fc_series[g].index, fc_series[g].values, ls="--", lw=1.2, color=line.get_color())
    ax.axvline(data.index[-1], color="grey", lw=0.8)
    ax.set_title("Prediksi minat genre hingga akhir 2027 (garis putus-putus = prediksi)")
    ax.legend(fontsize=8, ncol=4); fig.tight_layout()
    fig.savefig(OUT / "g2_prediksi_2027.png", dpi=160); plt.close(fig)

    if plat_cols:
        fig, ax = plt.subplots(figsize=(11, 4))
        data[plat_cols].rolling(4).mean().plot(ax=ax)
        ax.set_title("Minat pencarian: bioskop vs Netflix"); fig.tight_layout()
        fig.savefig(OUT / "g3_bioskop_vs_netflix.png", dpi=160); plt.close(fig)

    if not titles.empty:
        fig, ax = plt.subplots(figsize=(9, 6))
        t = titles.sort_values("total_minat_52mg_sejak_puncak")
        ax.barh(t["judul"] + " (" + t["tahun_rilis"].astype("Int64").astype(str) + ")",
                t["total_minat_52mg_sejak_puncak"])
        ax.set_title("Total minat 52 minggu sejak puncak, per judul"); fig.tight_layout()
        fig.savefig(OUT / "g4_judul.png", dpi=160); plt.close(fig)

    print("\n=== Minat genre per tahun ===\n", yearly)
    print("\n=== Prediksi 2027 ===\n", forecast.to_string(index=False))
    print(f"\nSemua hasil tersimpan di: {OUT}/")


# ─────────────────────────────── DEMO ───────────────────────────────
def demo():
    """Buat data sintetis berbentuk sama seperti keluaran pytrends, untuk uji alur."""
    RAW.mkdir(exist_ok=True)
    for f in RAW.glob("*"):
        f.unlink()
    rng = np.random.default_rng(7)
    kw = pd.read_csv(KW_FILE)
    idx = pd.date_range(end="2026-09-20", periods=261, freq="W-SUN")
    terms = [k for k in kw["keyword"] if k.lower() != ANCHOR]
    for bi, i in enumerate(range(0, len(terms), BATCH), 1):
        batch = terms[i:i + BATCH]
        df = pd.DataFrame(index=idx)
        df.index.name = "date"
        season = 1 + 0.3 * np.sin(2 * np.pi * idx.isocalendar().week.values / 52)
        for k in batch + [ANCHOR]:
            row = kw[kw.keyword == k]
            if not row.empty and row.iloc[0]["jenis"] == "judul":
                peak = rng.integers(20, 250)
                v = np.exp(-0.5 * ((np.arange(261) - peak) / 4) ** 2) * rng.uniform(40, 100)
            else:
                v = rng.uniform(20, 60) * season * np.linspace(0.8, 1.2, 261) + rng.normal(0, 3, 261)
            df[k] = np.clip(v, 0, None).round()
        scale = 100 / df.values.max()
        (df * scale).round().to_csv(RAW / f"iot_batch_{bi:02d}.csv")
    pd.DataFrame({"query": ["contoh judul"], "value": [100], "tipe": ["rising"],
                  "genre_keyword": ["film horor"]}).to_csv(RAW / "related_film_horor.csv", index=False)
    print("Data demo dibuat.")
    analyze()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    {"fetch": fetch, "analyze": analyze, "demo": demo}.get(cmd, lambda: print(__doc__))()
