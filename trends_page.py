import streamlit as st
import pandas as pd
import pathlib
import json

ROOT = pathlib.Path(__file__).resolve().parent

TRENDS_HOROR = ROOT / "data/raw/google_trends/google_trends_film_horor_indonesia_2025_2026.csv"
AUDIT_FILE = ROOT / "data/processed/audit/google_trends_audit.json"
SUMMARY_FILE = ROOT / "data/processed/trends_horor_summary.json"
PEAKS_FILE = ROOT / "data/processed/trends_horor_peaks.csv"

def render_trends():
    st.header("📈 Google Trends - Riset Minat Film Indonesia")
    st.caption("Data resmi Google Trends dari hasil scraper Apify (52 Minggu Penuh)")

    if TRENDS_HOROR.exists():
        df_horor = pd.read_csv(TRENDS_HOROR)
        
        kw_name = df_horor['keyword'].iloc[0] if not df_horor.empty else 'film horor Indonesia'
        geo_name = df_horor['geo'].iloc[0] if not df_horor.empty else 'ID'
        granularity = df_horor['granularity'].iloc[0] if 'granularity' in df_horor.columns else 'weekly'
        
        st.subheader(f"Tren Minat '{kw_name}' ({len(df_horor)} Minggu)")
        st.caption(f"Periode riil: {df_horor['date'].min()} s/d {df_horor['date'].max()} | Granularitas: {granularity} | Geo: {geo_name} (inferred_from_subregion_codes)")
        
        chart_df = df_horor.set_index("date")[["interest"]]
        st.line_chart(chart_df)
        
        # Tampilkan ringkasan analisis deskriptif & uji statistik
        if SUMMARY_FILE.exists():
            st.divider()
            st.subheader("📊 Analisis Deskriptif & Pengujian Tren")
            with open(SUMMARY_FILE) as f:
                sum_data = json.load(f)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Rata-rata", f"{sum_data.get('mean_interest', 0)}")
            c2.metric("Median", f"{sum_data.get('median_interest', 0)}")
            c3.metric("Rentang Min - Max", f"{sum_data.get('min_interest', 0)} - {sum_data.get('max_interest', 0)}")
            
            # Perbandingan Model Tren
            tc = sum_data.get("trend_comparison", {})
            st.markdown("#### 🔬 Perbandingan Uji Tren Statistik")
            
            comparison_rows = []
            if "ols_standard" in tc:
                o = tc["ols_standard"]
                comparison_rows.append({"Metode": "OLS Standar", "Slope": o["slope"], "Std. Error": o["std_error"], "p-value": o["p_value"], "Keterangan": "Signifikan Turun (p < 0.05)" if o["p_value"] < 0.05 else "Tidak Signifikan"})
            if "ols_newey_west_hac_lag4" in tc:
                nw = tc["ols_newey_west_hac_lag4"]
                comparison_rows.append({"Metode": "OLS Newey-West (HAC lag=4)", "Slope": nw["slope"], "Std. Error": nw["std_error"], "p-value": nw["p_value"], "Keterangan": "Robust terhadap Autokorelasi"})
            if "mann_kendall_test" in tc:
                mk = tc["mann_kendall_test"]
                comparison_rows.append({"Metode": "Mann-Kendall (Non-parametrik)", "Slope": mk["sen_slope"], "Std. Error": "-", "p-value": mk["p_value"], "Keterangan": f"Tren: {mk['trend'].capitalize()}"})
                
            st.table(pd.DataFrame(comparison_rows))

            # Catatan Kehati-hatian Metodologi
            st.warning(sum_data.get("methodological_caution", ""))

            # Periode Puncak Berurutan
            st.markdown("#### 🏔️ Periode Puncak Pencarian")
            periods = sum_data.get("peak_periods_clustered", [])
            if periods:
                st.dataframe(pd.DataFrame(periods), use_container_width=True)

            # Pola Bulanan
            st.markdown("#### 📅 Pola Rata-rata Minat Bulanan")
            mp = sum_data.get("monthly_pattern", {})
            if mp:
                mp_series = pd.Series({k: v["mean_interest"] for k, v in mp.items()})
                st.bar_chart(mp_series)

        with st.expander("Lihat Tabel Data Mentah CSV"):
            st.dataframe(df_horor, use_container_width=True)
    else:
        st.info("File `google_trends_film_horor_indonesia_2025_2026.csv` belum tersedia.")

    st.divider()
    st.subheader("🔍 Status Audit Google Trends")
    if AUDIT_FILE.exists():
        with open(AUDIT_FILE) as f:
            audit_data = json.load(f)
        st.json(audit_data)
    else:
        st.caption("Laporan audit belum dibuat.")
