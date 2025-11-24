import streamlit as st
import pandas as pd
from pathlib import Path

# --------------------------
# 1. LOAD & PREPARE THE DATA
# --------------------------
DATA_PATH = Path(__file__).parent / "fpl database.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, sep=";", engine="python")
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")],
                 errors="ignore")
    df = df.rename(columns={
        "Kontak Lembaga/\nKontak Layanan": "Kontak Lembaga/Layanan",
    })

    # siapkan list layanan mentah
    if "Layanan Yang Diberikan" in df.columns:
        layanan_raw = df["Layanan Yang Diberikan"].fillna("").str.replace("\n", ";")
        df["layanan_list"] = layanan_raw.apply(
            lambda x: [p.strip() for p in x.split(";") if p.strip()]
        )
    else:
        df["layanan_list"] = [[] for _ in range(len(df))]

    # fungsi mapping layanan ke kategori
    def classify_service(s: str):
        s_low = s.lower()
        cats = set()

        if "evakuasi" in s_low:
            cats.add("Evakuasi")
        if any(k in s_low for k in ["konseling", "psikolog", "support group", "trauma", "dukungan sebaya"]):
            cats.add("Konseling & Psikologis")
        if any(k in s_low for k in ["hukum", "litigasi", "non litigasi", "bantuan hukum"]):
            cats.add("Hukum / Litigasi")
        if any(k in s_low for k in ["medis", "faskes", "dokter", "uptd ppa"]):
            cats.add("Medis")
        if any(k in s_low for k in ["reintegrasi", "penjemputan", "jenasah", "jenazah"]):
            cats.add("Reintegrasi & Repatriasi")
        if any(k in s_low for k in ["rujuk", "rujukan", "pengaduan"]):
            cats.add("Rujukan & Pengaduan")
        if "rumah aman" in s_low or "shelter" in s_low:
            cats.add("Shelter / Rumah Aman")
        if "ekonomi" in s_low:
            cats.add("Pemberdayaan Ekonomi")
        if any(k in s_low for k in ["pelatihan", "keterampilan", "training"]):
            cats.add("Pelatihan & Keterampilan")
        if "spiritu" in s_low:
            cats.add("Pendampingan Spiritual")
        if any(k in s_low for k in ["disabilitas", "jbi"]):
            cats.add("Disabilitas")
        if not cats:
            cats.add("Lainnya")
        return cats

    # kategori_layanan = list kategori pendek per baris
    df["kategori_layanan"] = df["layanan_list"].apply(
        lambda row: sorted({cat for s in row for cat in classify_service(s)})
    )

    return df

df = load_data()

# --------------------------
# 2. STREAMLIT LAYOUT & UI
# --------------------------
st.set_page_config(page_title="FPL Database", layout="wide")

st.title("📚 Direktori Layanan FPL")
st.caption("Filter lembaga berdasarkan nama, alamat, dan kategori layanan.")

# Sidebar filters
st.sidebar.header("Filter")

name = st.sidebar.text_input("Cari Nama Organisasi")
addr = st.sidebar.text_input("Cari Alamat / Daerah")

all_categories = sorted({c for cats in df["kategori_layanan"] for c in cats})
selected_categories = st.sidebar.multiselect("Kategori Layanan", all_categories)

# --------------------------
# 3. FILTER DATA
# --------------------------
filtered = df.copy()

if name:
    filtered = filtered[filtered["Nama Organisasi"].fillna("")
                        .str.contains(name, case=False, na=False)]

if addr and "Alamat Organisasi" in filtered.columns:
    filtered = filtered[filtered["Alamat Organisasi"].fillna("")
                        .str.contains(addr, case=False, na=False)]

if selected_categories:
    def has_cat(lst):
        return any(c in lst for c in selected_categories)
    filtered = filtered[filtered["kategori_layanan"].apply(has_cat)]

st.write(f"Menampilkan **{len(filtered)}** dari **{len(df)}** lembaga")

cols = [c for c in [
    "No",
    "Nama Organisasi",
    "Alamat Organisasi",
    "Kontak Lembaga/Layanan",
    "Email Lembaga",
    "Layanan Yang Diberikan",
    "kategori_layanan",
] if c in filtered.columns]

st.dataframe(filtered[cols], use_container_width=True)
