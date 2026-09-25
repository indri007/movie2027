import pandas as pd
import pathlib
import sys

BASE = pathlib.Path(__file__).parent
DATA_DIR = BASE / "data"
NODEXL_DIR = DATA_DIR / "raw" / "nodexl"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = DATA_DIR / "outputs"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Cari file workbook NodeXL di data/raw/nodexl/
excel_files = list(NODEXL_DIR.glob("*.xlsx")) + list(NODEXL_DIR.glob("*.xls"))

if not excel_files:
    print(f"⚠️ Berkas NodeXL belum ditemukan di {NODEXL_DIR}/.")
    print("Salin berkas NodeXL_Instagram_Network.xlsx ke folder tersebut lalu jalankan kembali skrip ini.")
    sys.exit(0)

target_file = excel_files[0]
print(f"Menganalisis berkas NodeXL: {target_file.name}...\n")

# Buka seluruh sheet di dalam Excel
xl = pd.ExcelFile(target_file)
print("Lembar kerja (Sheets) yang ditemukan:", xl.sheet_names)

# 1. BACA EDGES
edges_df = pd.DataFrame()
for s in ["Edges", "Relationships", "Edge List"]:
    if s in xl.sheet_names:
        edges_df = pd.read_excel(target_file, sheet_name=s)
        break

# 2. BACA VERTICES
vertices_df = pd.DataFrame()
for s in ["Vertices", "Nodes", "Vertex List"]:
    if s in xl.sheet_names:
        vertices_df = pd.read_excel(target_file, sheet_name=s)
        break

# 3. BACA METRIK JARINGAN KESELURUHAN (Overall Metrics)
metrics_df = pd.DataFrame()
for s in ["Overall Metrics", "Network Metrics", "Metrics"]:
    if s in xl.sheet_names:
        metrics_df = pd.read_excel(target_file, sheet_name=s)
        break

print("\n=== RINGKASAN METRIK JARINGAN NODEXL ===")
if not metrics_df.empty:
    print(metrics_df.dropna(how="all").head(15).to_string())

num_edges = len(edges_df)
num_vertices = len(vertices_df)
print(f"\nTotal Hubungan (Edges): {num_edges}")
print(f"Total Entitas / Akun (Vertices): {num_vertices}")

# 4. IDENTIFIKASI TOP AKUN / KEYWORD DOMINAN
if not vertices_df.empty:
    v_cols = [c for c in vertices_df.columns if "vertex" in c.lower() or "node" in c.lower() or "user" in c.lower() or "label" in c.lower()]
    deg_cols = [c for c in vertices_df.columns if "degree" in c.lower() or "betweenness" in c.lower()]
    
    if v_cols:
        v_col = v_cols[0]
        deg_col = deg_cols[0] if deg_cols else None
        
        if deg_col:
            top_accounts = vertices_df.sort_values(deg_col, ascending=False).head(10)[[v_col, deg_col]]
            print(f"\nTop 10 Akun Paling Berpengaruh (Berdasarkan {deg_col}):")
            print(top_accounts.to_string(index=False))
            top_accounts.to_csv(OUTPUTS_DIR / "nodexl_top_influencers.csv", index=False)

# Simpan ringkasan bersih
if not edges_df.empty:
    edges_df.to_csv(PROCESSED_DIR / "nodexl_edges_cleaned.csv", index=False)
if not vertices_df.empty:
    vertices_df.to_csv(PROCESSED_DIR / "nodexl_vertices_cleaned.csv", index=False)

print(f"\n✅ Hasil pemrosesan NodeXL disimpan di {PROCESSED_DIR}/ dan {OUTPUTS_DIR}/")
