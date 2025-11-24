import streamlit as st
import pandas as pd
from pathlib import Path
import datetime

# --------------------------
# 0. PAGE CONFIG & STYLE
# --------------------------
st.set_page_config(
    page_title="Direktori Layanan FPL",
    page_icon="📚",
    layout="wide",
)

# Sedikit CSS untuk merapikan tampilan
st.markdown(
    """
    <style>
    /* Hilangkan padding atas */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    /* Card look untuk sidebar filter */
    .sidebar-content {
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# 1. LOAD & PREPARE THE DATA
# --------------------------
DATA_PATH = Path(__file__).parent / "fpl database.csv"
SUGGEST_PATH = Path(__file__).parent / "edit_suggestions.csv"


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

    # fungsi mapping layanan ke kategori pendek
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


@st.cache_data
def load_suggestions():
    if SUGGEST_PATH.exists():
        return pd.read_csv(SUGGEST_PATH)
    else:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "organisasi",
                "pengaju",
                "kontak",
                "kolom",
                "usulan",
            ]
        )


df = load_data()
suggestions_df = load_suggestions()

# --------------------------
# 2. HEADER
# --------------------------
left_col, right_col = st.columns([1, 3])

with left_col:
    st.image(
        "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
        width=70,
    )
with right_col:
    st.markdown("### 📚 Direktori Layanan FPL")
    st.markdown(
        "Filter lembaga layanan berbasis perempuan & korban kekerasan "
        "berdasarkan **nama**, **alamat**, dan **kategori layanan**."
    )

st.divider()

# --------------------------
# 3. FILTER SIDEBAR
# --------------------------
st.sidebar.markdown("## 🔍 Filter")

name = st.sidebar.text_input("Cari Nama Organisasi")
addr = st.sidebar.text_input("Cari Alamat / Daerah")

all_categories = sorted({c for cats in df["kategori_layanan"] for c in cats})
selected_categories = st.sidebar.multiselect("Kategori Layanan", all_categories)

if st.sidebar.button("Reset filter"):
    # cara simple: kasih instruksi user tekan Rerun
    st.sidebar.info("Silakan refresh halaman untuk reset penuh.")
    name = ""
    addr = ""
    selected_categories = []

# --------------------------
# 4. FILTER DATAFRAME
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

# --------------------------
# 5. MAIN TABLE
# --------------------------
total_count = len(df)
filtered_count = len(filtered)

st.markdown(
    f"**Menampilkan {filtered_count} dari {total_count} lembaga**"
)

cols = [c for c in [
    "No",
    "Nama Organisasi",
    "Alamat Organisasi",
    "Kontak Lembaga/Layanan",
    "Email Lembaga",
  
    "kategori_layanan",
] if c in filtered.columns]

# sedikit pemendek teks panjang
show_df = filtered[cols].copy()
for col in ["Alamat Organisasi", "Layanan Yang Diberikan"]:
    if col in show_df.columns:
        show_df[col] = show_df[col].fillna("").astype(str).str.slice(0, 140) + "…"

st.dataframe(show_df, use_container_width=True)

# --------------------------
# 6. FORM USULAN KOREKSI
# --------------------------
st.markdown("### ✏️ Ajukan Koreksi Data Lembaga")

st.markdown(
    "Jika Anda pengelola lembaga dan menemukan data yang tidak tepat, "
    "silakan kirim koreksi melalui form di bawah. Tim FPL akan meninjau "
    "dan memperbarui direktori secara berkala."
)

with st.form("suggest_form"):
    org_name = st.selectbox(
        "Pilih lembaga yang ingin dikoreksi",
        sorted(df["Nama Organisasi"].dropna().unique()),
    )
    pengaju = st.text_input("Nama Anda")
    kontak = st.text_input("Kontak (email / WA)")
    kolom = st.multiselect(
        "Bagian yang ingin diubah (boleh lebih dari satu)",
        [
            "Alamat Organisasi",
            "Kontak Lembaga/Layanan",
            "Email Lembaga",
            "Layanan Yang Diberikan",
            "Profil Organisasi",
            "Lainnya",
        ],
    )
    usulan = st.text_area(
        "Tuliskan data baru / koreksi yang diusulkan",
        help="Contoh: Alamat baru lengkap, nomor kontak yang aktif, atau deskripsi layanan yang diperbarui.",
        height=150,
    )

    submitted = st.form_submit_button("Kirim Usulan Koreksi")

    if submitted:
        if not usulan.strip():
            st.warning("Mohon isi data koreksi terlebih dahulu.")
        else:
            new_row = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "organisasi": org_name,
                "pengaju": pengaju,
                "kontak": kontak,
                "kolom": "; ".join(kolom) if kolom else "",
                "usulan": usulan.strip(),
            }
            suggestions_df = pd.concat(
                [suggestions_df, pd.DataFrame([new_row])],
                ignore_index=True,
            )
            suggestions_df.to_csv(SUGGEST_PATH, index=False)
            st.success(
                "Terima kasih, usulan koreksi Anda sudah tercatat. "
                "Tim akan memverifikasi sebelum mengubah data utama."
            )

# --------------------------
# 7. PANEL ADMIN: LIHAT & DOWNLOAD USULAN
# --------------------------
with st.expander("📥 Daftar Usulan Koreksi (untuk admin)"):
    if len(suggestions_df) == 0:
        st.caption("Belum ada usulan koreksi yang tercatat.")
    else:
        st.caption("Gunakan tombol download di bawah untuk review & approval offline.")
        st.dataframe(
            suggestions_df.sort_values("timestamp", ascending=False),
            use_container_width=True,
        )
        csv_data = suggestions_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download semua usulan (CSV)",
            data=csv_data,
            file_name="edit_suggestions.csv",
            mime="text/csv",
        )
