import streamlit as st
import pandas as pd
from pathlib import Path

# --------------------------
# CONFIG & CONSTANTS
# --------------------------
st.set_page_config(
    page_title="Direktori Layanan FPL",
    page_icon="📚",
    layout="wide",
)

DATA_PATH = Path(__file__).parent / "fpl database.csv"
FPL_LOGO_PATH = Path(__file__).parent / "fpl_logo.png"

# Ganti dengan URL Google Form kamu (versi embed)
# Contoh: "https://docs.google.com/forms/d/e/XXX/viewform?embedded=true"
GOOGLE_FORM_EMBED_URL = "https://docs.google.com/forms/d/XXXXX/viewform?embedded=true"

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    .sidebar-content {
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# LOAD & PREPARE DATA
# --------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, sep=";", engine="python")
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")],
                 errors="ignore")
    df = df.rename(columns={
        "Kontak Lembaga/\nKontak Layanan": "Kontak Lembaga/Layanan",
    })

    # list layanan mentah
    if "Layanan Yang Diberikan" in df.columns:
        layanan_raw = df["Layanan Yang Diberikan"].fillna("").str.replace("\n", ";")
        df["layanan_list"] = layanan_raw.apply(
            lambda x: [p.strip() for p in x.split(";") if p.strip()]
        )
    else:
        df["layanan_list"] = [[] for _ in range(len(df))]

    # mapping ke kategori
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

    df["kategori_layanan"] = df["layanan_list"].apply(
        lambda row: sorted({cat for s in row for cat in classify_service(s)})
    )

    return df


df = load_data()

# --------------------------
# HEADER + LOGO
# --------------------------
logo_col, title_col = st.columns([1, 4])

with logo_col:
    if FPL_LOGO_PATH.exists():
        st.image(FPL_LOGO_PATH, width=90)
    else:
        st.markdown("📚")

with title_col:
    st.markdown("### Direktori Layanan FPL")
    st.markdown(
        "Direktori lembaga layanan yang bekerja untuk pemenuhan hak dan "
        "perlindungan korban kekerasan berbasis perempuan."
    )

st.divider()

# --------------------------
# TABS
# --------------------------
tab_dir, tab_about, tab_koreksi = st.tabs(
    ["📊 Direktori", "ℹ️ Tentang", "✏️ Koreksi Data & Admin"]
)

# ==========================
# TAB 1: DIREKTORI
# ==========================
with tab_dir:
    st.subheader("📊 Direktori Layanan")

    fcol1, fcol2 = st.columns([1, 3])

    with fcol1:
        st.markdown("#### 🔍 Filter")
        name = st.text_input("Cari Nama Organisasi")
        addr = st.text_input("Cari Alamat / Daerah")

        all_categories = sorted({c for cats in df["kategori_layanan"] for c in cats})
        selected_categories = st.multiselect("Kategori Layanan", all_categories)

        if st.button("Reset filter"):
            st.experimental_rerun()

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

    total_count = len(df)
    filtered_count = len(filtered)

    with fcol2:
        st.markdown(f"Menampilkan **{filtered_count}** dari **{total_count}** lembaga")

        cols = [c for c in [
            "No",
            "Nama Organisasi",
            "Alamat Organisasi",
            "Kontak Lembaga/Layanan",
            "Email Lembaga",
            "Layanan Yang Diberikan",
            "kategori_layanan",
        ] if c in filtered.columns]

        show_df = filtered[cols].copy()
        for col in ["Alamat Organisasi", "Layanan Yang Diberikan"]:
            if col in show_df.columns:
                show_df[col] = show_df[col].fillna("").astype(str).str.slice(0, 140) + "…"

        st.dataframe(show_df, use_container_width=True)

# ==========================
# TAB 2: TENTANG
# ==========================
with tab_about:
    st.subheader("ℹ️ Tentang Direktori Layanan FPL")
    st.markdown(
        """
        Direktori ini disusun untuk membantu:

        - Penyintas kekerasan dan pendamping menemukan **lembaga layanan yang relevan dan terdekat**.
        - Jaringan FPL dan mitra melihat **peta layanan** berdasarkan jenis layanan dan wilayah.
        
        **Sumber data:**
        - Kompilasi lembaga anggota dan mitra Forum Pengada Layanan (FPL).
        - Informasi dikumpulkan melalui formulir dan proses verifikasi internal.
        
        Direktori akan diperbarui secara berkala berdasarkan:
        - Usulan koreksi dari lembaga.
        - Hasil verifikasi lapangan dan koordinasi jaringan.
        """
    )

# ==========================
# TAB 3: KOREKSI DATA & ADMIN
# ==========================
with tab_koreksi:
    st.subheader("✏️ Ajukan Koreksi Data Lembaga")

    st.markdown(
        """
        Jika Anda **pengelola lembaga** dan menemukan data yang tidak sesuai,
        silakan mengisi formulir koreksi di bawah ini.
        
        Usulan Anda akan otomatis tercatat di Google Sheets (Responses),
        lalu ditinjau oleh tim sebelum data utama di direktori diubah.
        """
    )

    if GOOGLE_FORM_EMBED_URL.startswith("https://docs.google.com"):
        st.components.v1.iframe(
            GOOGLE_FORM_EMBED_URL,
            height=700,
        )
    else:
        st.warning("Google Form belum dikonfigurasi. Hubungi admin untuk menambahkan URL.")

    st.markdown("---")
    st.subheader("📥 Panduan untuk Admin")

    st.markdown(
        """
        1. Buka Google Sheet yang terhubung dengan Google Form *Koreksi Data*.
        2. Tinjau setiap respon:
           - cocokkan dengan data di direktori,
           - klarifikasi ke lembaga jika perlu.
        3. Jika disetujui:
           - update file `fpl database.csv` di komputer Anda,
           - commit & push ke GitHub (`publicdashboard` repo),
           - dashboard akan otomatis menggunakan data terbaru.
        """
    )
