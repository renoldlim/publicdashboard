import streamlit as st
import pandas as pd
from pathlib import Path
import datetime

import gspread
from google.oauth2.service_account import Credentials

# --------------------------
# 0. PAGE CONFIG & STYLE
# --------------------------
st.set_page_config(
    page_title="Direktori Layanan FPL",
    page_icon="📚",
    layout="wide",
)

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
# 1. KONFIG & DATA UTAMA
# --------------------------
DATA_PATH = Path(__file__).parent / "fpl database.csv"

# ID Google Sheet untuk usulan koreksi (set di Streamlit secrets)
SUGGEST_SHEET_ID = st.secrets.get("SUGGEST_SHEET_ID", None)
SUGGEST_SHEET_NAME = "Koreksi"  # nama tab di Google Sheet


# ---------- Google Sheets client ----------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_gsheet_client():
    """Inisialisasi client gspread dari secrets Streamlit."""
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


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

    # mapping layanan ke kategori pendek
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
def load_suggestions_from_sheet():
    """Baca semua usulan koreksi dari Google Sheet (tab Koreksi)."""
    if not SUGGEST_SHEET_ID:
        return None

    client = get_gsheet_client()
    sh = client.open_by_key(SUGGEST_SHEET_ID)
    ws = sh.worksheet(SUGGEST_SHEET_NAME)
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(
            columns=["timestamp", "organisasi", "pengaju", "kontak", "kolom", "usulan"]
        )
    return pd.DataFrame(records)


df = load_data()
suggestions_df = load_suggestions_from_sheet()

# --------------------------
# 2. HEADER + LOGO
# --------------------------
logo_col, title_col = st.columns([1, 4])

with logo_col:
    logo_path = Path(__file__).parent / "fpl_logo.png"
    if logo_path.exists():
        st.image(logo_path, width=90)
    else:
        st.markdown("📚")  # fallback emoji

with title_col:
    st.markdown("### Direktori Layanan FPL")
    st.markdown(
        "Direktori lembaga layanan yang bekerja untuk pemenuhan hak dan "
        "perlindungan korban kekerasan berbasis perempuan."
    )

st.divider()

# --------------------------
# 3. TABS
# --------------------------
tab_dir, tab_about, tab_help = st.tabs(
    ["📊 DirektorI", "ℹ️ Tentang Direktori", "✏️ Panduan Koreksi & Admin"]
)

# --------------------------
# TAB 1: DIREKTORI (FILTER + TABEL + FORM KOREKSI)
# --------------------------
with tab_dir:
    st.subheader("📊 Direktori Layanan")

    # FILTER di kolom kiri
    fcol1, fcol2 = st.columns([1, 3])

    with fcol1:
        st.markdown("#### 🔍 Filter")
        name = st.text_input("Cari Nama Organisasi")
        addr = st.text_input("Cari Alamat / Daerah")

        all_categories = sorted({c for cats in df["kategori_layanan"] for c in cats})
        selected_categories = st.multiselect("Kategori Layanan", all_categories)

        if st.button("Reset filter"):
            name = ""
            addr = ""
            selected_categories = []
            st.experimental_rerun()

    # FILTERING
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

    st.markdown("#### ✏️ Ajukan Koreksi Data")

    st.markdown(
        "Jika Anda pengelola lembaga dan menemukan data yang tidak tepat, "
        "silakan ajukan koreksi melalui form berikut."
    )

    with st.form("suggest_form"):
        org_name = st.selectbox(
            "Pilih lembaga yang ingin dikoreksi",
            sorted(df["Nama Organisasi"].dropna().unique()),
        )
        pengaju = st.text_input("Nama Anda")
        kontak = st.text_input("Kontak (email / WA)")
        kolom = st.multiselect(
            "Bagian yang ingin diubah",
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
            height=150,
        )

        submitted = st.form_submit_button("Kirim Usulan Koreksi")

        if submitted:
            if not usulan.strip():
                st.warning("Mohon isi data koreksi terlebih dahulu.")
            elif not SUGGEST_SHEET_ID:
                st.error(
                    "Google Sheet untuk koreksi belum dikonfigurasi. "
                    "Silakan hubungi admin."
                )
            else:
                try:
                    client = get_gsheet_client()
                    sh = client.open_by_key(SUGGEST_SHEET_ID)
                    # pastikan tab 'Koreksi' sudah ada
                    try:
                        ws = sh.worksheet(SUGGEST_SHEET_NAME)
                    except gspread.WorksheetNotFound:
                        ws = sh.add_worksheet(
                            title=SUGGEST_SHEET_NAME, rows=1000, cols=10
                        )
                        ws.append_row(
                            ["timestamp", "organisasi", "pengaju",
                             "kontak", "kolom", "usulan"]
                        )

                    new_row = [
                        datetime.datetime.utcnow().isoformat(),
                        org_name,
                        pengaju,
                        kontak,
                        "; ".join(kolom) if kolom else "",
                        usulan.strip(),
                    ]
                    ws.append_row(new_row)
                    load_suggestions_from_sheet.clear()  # refresh cache
                    st.success(
                        "Terima kasih, usulan koreksi Anda sudah tercatat. "
                        "Tim akan memverifikasi sebelum mengubah data utama."
                    )
                except Exception as e:
                    st.error(f"Gagal menyimpan ke Google Sheet: {e}")

# --------------------------
# TAB 2: TENTANG DIREKTORI
# --------------------------
with tab_about:
    st.subheader("ℹ️ Tentang Direktori Layanan FPL")

    st.markdown(
        """
        Direktori ini dikembangkan untuk memudahkan:

        - Penyintas kekerasan dan pendamping mencari **lembaga layanan terdekat**
          yang relevan dengan kebutuhan mereka.
        - Jaringan FPL dan mitra melihat **peta layanan** berdasarkan jenis layanan,
          wilayah, dan profil lembaga.
        
        **Sumber data:**
        - Kompilasi lembaga anggota dan mitra FPL.
        - Informasi kontak, alamat, dan layanan berasal dari pengisian formulir
          dan proses verifikasi internal.
        
        Direktori ini akan diperbarui secara berkala berdasarkan:
        - Usulan koreksi dari lembaga layanan.
        - Hasil verifikasi lapangan dan koordinasi jaringan.
        """
    )

# --------------------------
# TAB 3: PANDUAN KOREKSI & ADMIN
# --------------------------
with tab_help:
    st.subheader("✏️ Panduan Koreksi Data")

    st.markdown(
        """
        **Bagi pengelola lembaga:**

        1. Buka tab **Direktori**.
        2. Cari lembaga Anda di tabel.
        3. Scroll ke bagian **Ajukan Koreksi Data**.
        4. Pilih nama lembaga, isi kontak, dan jelaskan koreksi yang diusulkan.
        5. Tim admin akan:
           - meninjau usulan,
           - menghubungi Anda jika perlu klarifikasi,
           - memperbarui direktori pada rilis berikutnya.
        """
    )

    st.markdown("---")
    st.subheader("📥 Panel Admin (Ringkasan Usulan Koreksi)")

    if not SUGGEST_SHEET_ID:
        st.warning(
            "Google Sheet untuk usulan koreksi belum dikonfigurasi "
            "(`SUGGEST_SHEET_ID` di Streamlit secrets)."
        )
    else:
        try:
            suggestions_df = load_suggestions_from_sheet()
            if suggestions_df is None or suggestions_df.empty:
                st.caption("Belum ada usulan koreksi yang tercatat.")
            else:
                st.caption(
                    "Daftar usulan koreksi dari lembaga. "
                    "Gunakan untuk proses verifikasi dan pembaruan data."
                )
                st.dataframe(
                    suggestions_df.sort_values("timestamp", ascending=False),
                    use_container_width=True,
                )
                csv_data = suggestions_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download usulan (CSV)",
                    data=csv_data,
                    file_name="koreksi_fpl.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.error(f"Gagal membaca Google Sheet: {e}")
