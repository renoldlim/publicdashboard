import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import datetime
import math

# ============================================================
# 0. CONFIG
# ============================================================
st.set_page_config(
    page_title="Direktori Layanan 129",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
FPL_CSV = BASE_DIR / "fpl database.csv"
UPTD_XLSX = BASE_DIR / "Data UPTD PPA_2025 (1).xlsx"
SUGGEST_PATH = BASE_DIR / "edit_suggestions.csv"
FPL_LOGO_PATH = BASE_DIR / "fpl_logo.png"  # opsional, abaikan jika belum ada file


# ============================================================
# 1. HELPER FUNCTIONS & STYLES
# ============================================================
def inject_css():
    st.markdown(
        """
        <style>
            .main-container {
                padding-top: 1.5rem;
                padding-bottom: 2.5rem;
            }
            .sidebar-content {
                padding-top: 1rem;
            }
            .stTabs [data-baseweb="tab-panel"] {
                padding-top: 1rem;
            }
            .org-card {
                padding: 0.9rem 1.1rem;
                margin-bottom: 0.9rem;
                border-radius: 0.9rem;
                border: 1px solid #e5e7eb;
                background-color: #ffffff;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }
            .org-name {
                font-weight: 600;
                font-size: 1rem;
                color: #111827;
                margin-bottom: 0.15rem;
            }
            .org-address {
                font-size: 0.90rem;
                color: #374151;
                margin-bottom: 0.35rem;
            }
            .org-meta {
                font-size: 0.85rem;
                color: #4b5563;
                margin-bottom: 0.1rem;
            }
            .org-meta span.label {
                font-weight: 600;
                color: #111827;
            }
            .badge {
                display: inline-flex;
                align-items: center;
                gap: 0.25rem;
                padding: 0.15rem 0.5rem;
                border-radius: 999px;
                font-size: 0.75rem;
                font-weight: 600;
                border: 1px solid rgba(37, 99, 235, 0.2);
                color: #1d4ed8;
                background-color: #eff6ff;
                white-space: nowrap;
            }
            .tag {
                display: inline-block;
                margin: 0.12rem 0.18rem 0.12rem 0;
                padding: 0.12rem 0.48rem;
                border-radius: 999px;
                background-color: #f3f4f6;
                color: #374151;
                font-size: 0.78rem;
            }
            .tag.kategori {
                background-color: #ecfeff;
                color: #0f766e;
            }
            .tag.source {
                background-color: #eef2ff;
                color: #3730a3;
            }
            .tag.small {
                font-size: 0.72rem;
                padding: 0.08rem 0.4rem;
            }
            .detail-box {
                padding: 0.9rem 1rem;
                margin-top: 0.4rem;
                border-radius: 0.75rem;
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
            }
            .detail-title {
                font-weight: 600;
                margin-bottom: 0.25rem;
            }
            .section-label {
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                font-weight: 600;
                color: #6b7280;
            }
            .small-link {
                font-size: 0.8rem;
                color: #2563eb !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()


def safe_str(x) -> str:
    if pd.isna(x):
        return ""
    return str(x)


# ============================================================
# 2. KATEGORI LAYANAN & EKSTRAK
# ============================================================
KATEGORI_DEFS = {
    "Evakuasi": ["evakuasi"],
    "Hukum / Litigasi": ["hukum", "litigasi", "bantuan hukum", "pendampingan hukum"],
    "Konseling & Psikologis": [
        "konseling",
        "psikolog",
        "psikososial",
        "support group",
        "trauma",
    ],
    "Medis": ["medis", "kesehatan", "rumah sakit", "puskesmas"],
    "Pelatihan & Keterampilan": ["pelatihan", "keterampilan", "kursus", "training"],
    "Pemberdayaan Ekonomi": ["ekonomi", "usaha", "penguatan ekonomi"],
    "Pendampingan Spiritual": ["spiritual", "rohani", "keagamaan"],
    "Reintegrasi & Repatriasi": ["reintegrasi", "repatriasi", "pemulangan", "jenazah"],
    "Rujukan & Pengaduan": ["rujukan", "pengaduan", "hotline", "call center"],
    "Shelter / Rumah Aman": ["shelter", "rumah aman"],
    "Disabilitas": ["disabilitas", "jbi"],
    "Lainnya": [],
}


def _extract_kategori(text: str) -> list[str]:
    text_l = (text or "").lower()
    hasil = set()
    for kat, keywords in KATEGORI_DEFS.items():
        if not keywords:
            continue
        for kw in keywords:
            if kw in text_l:
                hasil.add(kat)
                break
    if not hasil:
        hasil.add("Lainnya")
    return sorted(hasil)


# ============================================================
# 3. LOAD DATA FPL & UPTD
# ============================================================
def _read_excel_safe(path: Path, sheet_name: str):
    """Coba baca Excel; kalau gagal (engine, dll.) → None, dengan warning."""
    if not path.exists():
        return None
    try:
        return pd.read_excel(
            path,
            sheet_name=sheet_name,
            header=None,
            engine="openpyxl",
        )
    except ImportError:
        st.warning(
            "Package 'openpyxl' belum terpasang di environment. "
            f"Sheet '{sheet_name}' dari '{path.name}' tidak dapat dibaca."
        )
        return None
    except Exception as e:
        st.warning(
            f"Gagal membaca sheet '{sheet_name}' dari '{path.name}': {e}. "
            "Data UPTD akan dilewati."
        )
        return None


def load_fpl() -> pd.DataFrame:
    if not FPL_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(FPL_CSV, sep=";", engine="python")

    if "Kontak Lembaga/\nKontak Layanan" in df.columns:
        df = df.rename(
            columns={"Kontak Lembaga/\nKontak Layanan": "Kontak Lembaga/Layanan"}
        )

    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")], errors="ignore")

    df["Sumber Data"] = "Jaringan FPL"
    df["Latitude"] = np.nan
    df["Longitude"] = np.nan

    for col in [
        "Nama Organisasi",
        "Alamat Organisasi",
        "Kontak Lembaga/Layanan",
        "Email Lembaga",
        "Profil Organisasi",
        "Layanan Yang Diberikan",
        "Provinsi",
        "Kab/Kota",
    ]:
        if col not in df.columns:
            df[col] = ""

    return df[
        [
            "Nama Organisasi",
            "Alamat Organisasi",
            "Kontak Lembaga/Layanan",
            "Email Lembaga",
            "Profil Organisasi",
            "Layanan Yang Diberikan",
            "Sumber Data",
            "Latitude",
            "Longitude",
            "Provinsi",
            "Kab/Kota",
        ]
    ]


def load_uptd_prov() -> pd.DataFrame:
    raw = _read_excel_safe(UPTD_XLSX, sheet_name="UPTD PPA Provinsi")
    if raw is None:
        return pd.DataFrame()

    df = raw.iloc[3:].copy()
    df = df.rename(
        columns={
            0: "NO",
            1: "PROVINSI",
            3: "ALAMAT_KANTOR",
            4: "TELP_KANTOR",
            5: "HOTLINE",
        }
    )
    df = df[df["PROVINSI"].notna()]

    prov_clean = (
        df["PROVINSI"]
        .astype(str)
        .str.replace(r"^PROVINSI\s+", "", regex=True)
        .str.title()
    )

    out = pd.DataFrame()
    out["Nama Organisasi"] = "UPTD PPA " + prov_clean
    out["Alamat Organisasi"] = df["ALAMAT_KANTOR"]
    out["Kontak Lembaga/Layanan"] = df["HOTLINE"].replace({0: np.nan}).fillna(
        df["TELP_KANTOR"]
    )
    out["Email Lembaga"] = ""
    out["Profil Organisasi"] = "UPTD PPA tingkat provinsi di Provinsi " + prov_clean
    out["Layanan Yang Diberikan"] = (
        "Layanan pengaduan; konseling psikologis; pendampingan hukum; rujukan layanan."
    )
    out["Sumber Data"] = "UPTD PPA Provinsi"
    out["Provinsi"] = prov_clean
    out["Kab/Kota"] = ""
    out["Latitude"] = np.nan
    out["Longitude"] = np.nan

    return out


def load_uptd_kabkota() -> pd.DataFrame:
    raw = _read_excel_safe(UPTD_XLSX, sheet_name="UPTD PPA Kabkota")
    if raw is None:
        return pd.DataFrame()

    df = raw.iloc[4:].copy()
    df = df.rename(
        columns={
            0: "NO",
            1: "PROVINSI",
            2: "KABKOTA",
            4: "ALAMAT_KANTOR",
            5: "TELP_KANTOR",
            6: "HOTLINE",
        }
    )

    df = df[df["KABKOTA"].notna()]
    df = df[df["KABKOTA"] != "(4)"]  # buang baris header nyasar

    prov_clean = (
        df["PROVINSI"]
        .astype(str)
        .str.replace(r"^Provinsi\s+", "", regex=True)
        .str.title()
    )
    kab_clean = df["KABKOTA"].astype(str).str.title()

    out = pd.DataFrame()
    out["Nama Organisasi"] = "UPTD PPA " + kab_clean + " (" + prov_clean + ")"
    out["Alamat Organisasi"] = df["ALAMAT_KANTOR"]
    out["Kontak Lembaga/Layanan"] = df["HOTLINE"].fillna(df["TELP_KANTOR"])
    out["Email Lembaga"] = ""
    out["Profil Organisasi"] = (
        "UPTD PPA tingkat kabupaten/kota di " + kab_clean + ", Provinsi " + prov_clean
    )
    out["Layanan Yang Diberikan"] = (
        "Layanan pengaduan; konseling psikologis; pendampingan hukum; rujukan layanan."
    )
    out["Sumber Data"] = "UPTD PPA Kab/Kota"
    out["Provinsi"] = prov_clean
    out["Kab/Kota"] = kab_clean
    out["Latitude"] = np.nan
    out["Longitude"] = np.nan

    return out


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """Gabungkan FPL + UPTD PPA Provinsi + UPTD PPA Kab/Kota, plus kategori layanan."""
    fpl = load_fpl()
    uptd_prov = load_uptd_prov()
    uptd_kab = load_uptd_kabkota()

    df = pd.concat([fpl, uptd_prov, uptd_kab], ignore_index=True, sort=False)

    raw_text = (
        df.get("Layanan Yang Diberikan", "")
        .fillna("")
        .astype(str)
        .str.replace("\n", " ")
    )

    df["layanan_list"] = raw_text.apply(
        lambda t: [p.strip() for p in t.split(";") if p.strip()]
    )
    df["kategori_layanan"] = raw_text.apply(_extract_kategori)

    for col in [
        "Nama Organisasi",
        "Alamat Organisasi",
        "Kontak Lembaga/Layanan",
        "Email Lembaga",
        "Profil Organisasi",
        "Sumber Data",
        "Latitude",
        "Longitude",
    ]:
        if col not in df.columns:
            df[col] = ""

    return df


@st.cache_data(show_spinner=False)
def build_lokasi_uptd_fpl(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bentuk rekap per provinsi/kabupaten/kota:
    - berapa lembaga berjenis UPTD PPA (berdasarkan kolom 'Sumber Data')
    - berapa lembaga jaringan FPL
    - kategori lokasi: 'UPTD & FPL', 'Hanya UPTD', 'Hanya FPL'
    """

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "Provinsi",
                "Kab/Kota",
                "jml_lembaga",
                "jml_uptd",
                "jml_fpl",
                "Kategori Lokasi",
            ]
        )

    data = df.copy()

    # Pastikan kolom lokasi ada
    for col in ["Provinsi", "Kab/Kota"]:
        if col not in data.columns:
            data[col] = ""

    data["Provinsi_norm"] = data["Provinsi"].astype(str).str.strip().str.title()
    data["KabKota_norm"] = data["Kab/Kota"].astype(str).str.strip().str.title()

    # Hanya ambil baris yang punya nama kab/kota
    loc = data[data["KabKota_norm"] != ""].copy()

    loc["is_uptd"] = loc["Sumber Data"].astype(str).str.contains(
        "UPTD", case=False, na=False
    )
    loc["is_fpl"] = loc["Sumber Data"].astype(str).str.contains(
        "FPL", case=False, na=False
    )

    if "Nama Organisasi" in loc.columns:
        count_col = "Nama Organisasi"
    else:
        count_col = loc.columns[0]

    agg = (
        loc.groupby(["Provinsi_norm", "KabKota_norm"], dropna=False)
        .agg(
            jml_lembaga=(count_col, "count"),
            jml_uptd=("is_uptd", "sum"),
            jml_fpl=("is_fpl", "sum"),
        )
        .reset_index()
    )

    agg["has_uptd"] = agg["jml_uptd"] > 0
    agg["has_fpl"] = agg["jml_fpl"] > 0

    conditions = [
        agg["has_uptd"] & agg["has_fpl"],
        agg["has_uptd"] & ~agg["has_fpl"],
        ~agg["has_uptd"] & agg["has_fpl"],
    ]
    choices = ["UPTD & FPL", "Hanya UPTD", "Hanya FPL"]

    agg["Kategori Lokasi"] = np.select(
        conditions, choices, default="Belum terpetakan"
    )

    agg = agg.rename(
        columns={"Provinsi_norm": "Provinsi", "KabKota_norm": "Kab/Kota"}
    )

    return agg


# ============================================================
# 4. SUGGESTIONS (KOREKSI DATA) – LOCAL CSV ONLY
# ============================================================
def load_suggestions() -> pd.DataFrame:
    required_cols = [
        "id",
        "timestamp",
        "organisasi",
        "pengaju",
        "kontak",
        "kolom",
        "usulan",
        "catatan_internal",
        "status",
    ]
    if not SUGGEST_PATH.exists():
        return pd.DataFrame(columns=required_cols)

    try:
        df = pd.read_csv(SUGGEST_PATH)
    except Exception:
        return pd.DataFrame(columns=required_cols)

    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    df = df[required_cols]
    if df["id"].isna().all():
        df["id"] = range(1, len(df) + 1)
    return df


def save_suggestions(df_sug: pd.DataFrame):
    df_sug.to_csv(SUGGEST_PATH, index=False)


# ============================================================
# 5. INIT STATE & LOAD DF
# ============================================================
df = load_data()
lokasi_uptd_fpl = build_lokasi_uptd_fpl(df)

if "page" not in st.session_state:
    st.session_state["page"] = 1
if "koreksi_target_org" not in st.session_state:
    st.session_state["koreksi_target_org"] = None
if "koreksi_hint" not in st.session_state:
    st.session_state["koreksi_hint"] = None
if "show_detail" not in st.session_state:
    st.session_state["show_detail"] = False
if "detail_org" not in st.session_state:
    st.session_state["detail_org"] = None

# ============================================================
# 6. HEADER
# ============================================================
logo_col, title_col = st.columns([1, 4])
with logo_col:
    if FPL_LOGO_PATH.exists():
        st.image(FPL_LOGO_PATH, width=250)
    else:
        st.markdown("📊")

with title_col:
    st.markdown(
        "<h2 style='margin-bottom:4px;'>Direktori Layanan 129</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Direktori lembaga layanan yang bekerja untuk pemenuhan hak dan "
        "perlindungan korban kekerasan berbasis perempuan dan anak, "
        "terhubung dengan layanan *hotline* SAPA 129."
    )

st.divider()

# ============================================================
# 7. TABS
# ============================================================
tab_dir, tab_sanding, tab_koreksi, tab_admin, tab_about = st.tabs(
    ["📊 Direktori", "🔁 Sandingkan Lokasi", "✏️ Koreksi Data", "🗂️ Admin", "ℹ️ Tentang"]
)

# ============================================================
# TAB: DIREKTORI
# ============================================================
with tab_dir:
    # Heading dengan anchor dan ikon link sederhana
    st.markdown(
        """
        <h3 id="direktori-layanan" style="margin-bottom:0.75rem;">
          📊 Direktori Layanan
          <a href="#direktori-layanan" style="text-decoration:none;">↪</a>
        </h3>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "Cari lembaga layanan yang bekerja mendukung pemenuhan hak dan "
        "perlindungan korban kekerasan berbasis perempuan dan anak."
    )

    # ---------- FILTER ----------
    fcol1, fcol2 = st.columns([3, 2])
    with fcol1:
        name = st.text_input("Cari Nama Organisasi", "")
        addr = st.text_input("Cari Alamat / Daerah", "")

    with fcol2:
        # Pilih kategori layanan (multi select)
        all_categories = sorted(KATEGORI_DEFS.keys())
        selected_categories = st.multiselect(
            "Filter kategori layanan (opsional)", all_categories
        )

    filtered = df.copy()

    if name:
        filtered = filtered[
            filtered["Nama Organisasi"]
            .fillna("")
            .str.contains(name, case=False, na=False)
        ]
    if addr:
        filtered = filtered[
            filtered["Alamat Organisasi"]
            .fillna("")
            .str.contains(addr, case=False, na=False)
        ]

    if selected_categories:

        def has_cat(lst):
            return any(c in lst for c in selected_categories)

        filtered = filtered[filtered["kategori_layanan"].apply(has_cat)]

    total_count = len(df)
    filtered_count = len(filtered)

    st.caption(f"Menampilkan {filtered_count} dari {total_count} lembaga")

    # ---------- PAGINATION ----------
    page_size = 10
    total_pages = max(1, math.ceil(max(filtered_count, 1) / page_size))

    if st.session_state["page"] > total_pages:
        st.session_state["page"] = total_pages
    if st.session_state["page"] < 1:
        st.session_state["page"] = 1

    with fcol1:
        if filtered_count > 0:
            st.markdown("#### Halaman")
            prev_col, mid_col, next_col = st.columns([1, 2, 1])
            with prev_col:
                if st.button("◀", disabled=st.session_state["page"] <= 1):
                    st.session_state["page"] -= 1
            with mid_col:
                st.markdown(
                    f"<div style='text-align:center; margin-top:0.35rem;'>"
                    f"Halaman {st.session_state['page']} dari {total_pages}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with next_col:
                if st.button("▶", disabled=st.session_state["page"] >= total_pages):
                    st.session_state["page"] += 1

    start_idx = (st.session_state["page"] - 1) * page_size
    end_idx = start_idx + page_size
    page_df = filtered.iloc[start_idx:end_idx].copy()

    # ---------- LISTING CARD ----------
    if filtered_count == 0:
        st.info("Belum ada lembaga yang cocok dengan filter pencarian.")
    else:
        for idx_row, row in page_df.iterrows():
            nama = safe_str(row.get("Nama Organisasi", ""))
            alamat = safe_str(row.get("Alamat Organisasi", ""))
            kontak = safe_str(row.get("Kontak Lembaga/Layanan", ""))
            email = safe_str(row.get("Email Lembaga", ""))
            sumber = safe_str(row.get("Sumber Data", ""))
            layanan_list = row.get("layanan_list", [])
            kategori_layanan = row.get("kategori_layanan", [])

            # Badge utama
            badge_html = ""
            if "UPTD" in sumber.upper():
                badge_html = (
                    "<span class='badge'>UPTD PPA "
                    "(data KemenPPPA)</span>"
                )
            elif "FPL" in sumber.upper():
                badge_html = (
                    "<span class='badge'>Jaringan FPL</span>"
                )

            # Tags kategori layanan
            tags_html = ""
            if isinstance(kategori_layanan, (list, tuple)):
                for kat in kategori_layanan:
                    tags_html += (
                        f"<span class='tag kategori'>{kat}</span>"
                    )

            if sumber:
                tags_html += (
                    f"<span class='tag source'>"
                    f"{sumber}</span>"
                )

            alamat_disp = alamat if alamat else "—"

            card_html = f"""
                <div class="org-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem;">
                        <div class="org-name">{nama}</div>
                        <div>{badge_html}</div>
                    </div>
                    <div class="org-address">{alamat_disp}</div>
                    <div class="org-meta">
                        <span class="label">Service Contact:</span>
                        {'-' if not kontak else kontak}
                    </div>
                    <div class="org-meta">
                        <span class="label">Service Email:</span>
                        {'-' if not email else email}
                    </div>
                    <div class="org-meta">
                        <span class="label">Service Categories:</span><br/>
                        {tags_html if tags_html else '<span class="tag">Not specified</span>'}
                    </div>
                </div>
                """
            st.markdown(card_html, unsafe_allow_html=True)

            bcol1, bcol2 = st.columns(2)

            # Tombol usulan koreksi → simpan target + pesan dengan link ke anchor form
            with bcol1:
                if st.button(
                    "✏️ Usulkan koreksi",
                    key=f"suggest_{start_idx + idx_row}",
                    use_container_width=True,
                ):
                    st.session_state["koreksi_target_org"] = nama
                    st.session_state[
                        "koreksi_hint"
                    ] = f"Saya ingin mengoreksi data lembaga: {nama}"
                    st.session_state["page"] = st.session_state["page"]
                    st.session_state["show_detail"] = False
                    st.session_state["detail_org"] = None
                    st.toast(
                        "Silakan buka tab **Koreksi Data** di atas "
                        "untuk melengkapi formulir koreksi.",
                        icon="✏️",
                    )

            # Tombol detail lembaga
            with bcol2:
                if st.button(
                    "ℹ️ Lihat detail lembaga",
                    key=f"detail_{start_idx + idx_row}",
                    use_container_width=True,
                ):
                    st.session_state["show_detail"] = True
                    st.session_state["detail_org"] = nama

            # Jika lembaga ini sedang ditampilkan detailnya
            if (
                st.session_state.get("show_detail")
                and st.session_state.get("detail_org") == nama
            ):
                # Cari ulang row lengkap dari df gabungan
                r = df[df["Nama Organisasi"] == nama].iloc[0].to_dict()

                st.markdown(
                    "<div class='detail-box'>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    "<div class='detail-title'>Detail lembaga</div>",
                    unsafe_allow_html=True,
                )

                st.markdown("**Profil Organisasi**")
                profil = safe_str(r.get("Profil Organisasi", ""))
                st.write(profil if profil else "—")

                st.markdown("**Layanan yang diberikan**")
                layanan_list = r.get("layanan_list", [])
                if isinstance(layanan_list, (list, tuple)) and layanan_list:
                    for item in layanan_list:
                        st.write(f"- {safe_str(item)}")
                else:
                    st.write("—")

                if st.button("Tutup detail", key="close_detail_section"):
                    st.session_state["show_detail"] = False
                    st.session_state["detail_org"] = None
                    st.rerun()

        # ---------- TABEL + DOWNLOAD ----------
        with st.expander("📋 Tampilkan semua hasil dalam bentuk tabel"):
            table_df = filtered[
                [
                    "Nama Organisasi",
                    "Alamat Organisasi",
                    "Kontak Lembaga/Layanan",
                    "Email Lembaga",
                    "Profil Organisasi",
                    "Layanan Yang Diberikan",
                    "Sumber Data",
                ]
            ].copy()
            st.dataframe(table_df, use_container_width=True)

            csv = table_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Unduh hasil pencarian (CSV)",
                data=csv,
                file_name="direktori_layanan_129_filtered.csv",
                mime="text/csv",
            )

        # ---------- LINK CEPAT KE FORM KOREKSI ----------
        st.markdown(
            """
            <div style="margin-top:1.75rem; font-size:0.85rem; color:#6b7280;">
              Ingin memperbarui atau mengoreksi data lembaga?  
              <a href="#koreksi-data" class="small-link">Buka tab "Koreksi Data"</a>
              dan isi formulir perubahan.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="margin-top:0.75rem; text-align:right;">
              <a href="#direktori-layanan" class="small-link">
                ⬆️ Kembali ke atas (Direktori Layanan)
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# TAB: SANDINGKAN LOKASI UPTD & FPL
# ============================================================
with tab_sanding:
    st.markdown("### 🔁 Sandingkan Lokasi UPTD PPA dan Jaringan FPL")

    st.markdown(
        "Halaman ini menampilkan kabupaten/kota yang telah memiliki **UPTD PPA** "
        "dan **jaringan FPL** di wilayah yang sama, serta wilayah yang baru memiliki "
        "salah satu jenis layanan."
    )

    if lokasi_uptd_fpl is None or lokasi_uptd_fpl.empty:
        st.info("Data lokasi UPTD dan FPL belum tersedia atau belum terpetakan.")
    else:
        data_terpetakan = lokasi_uptd_fpl[
            lokasi_uptd_fpl["Kategori Lokasi"] != "Belum terpetakan"
        ]
        total_lokasi = len(data_terpetakan)

        n_both = (lokasi_uptd_fpl["Kategori Lokasi"] == "UPTD & FPL").sum()
        n_uptd_only = (lokasi_uptd_fpl["Kategori Lokasi"] == "Hanya UPTD").sum()
        n_fpl_only = (lokasi_uptd_fpl["Kategori Lokasi"] == "Hanya FPL").sum()

        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Kab/Kota memiliki UPTD & FPL",
            int(n_both),
            f"{(n_both / total_lokasi * 100):.0f}% dari lokasi terpetakan"
            if total_lokasi
            else "",
        )
        col2.metric(
            "Kab/Kota hanya UPTD",
            int(n_uptd_only),
            f"{(n_uptd_only / total_lokasi * 100):.0f}%"
            if total_lokasi
            else "",
        )
        col3.metric(
            "Kab/Kota hanya jaringan FPL",
            int(n_fpl_only),
            f"{(n_fpl_only / total_lokasi * 100):.0f}%"
            if total_lokasi
            else "",
        )

        st.markdown("---")

        # Filter provinsi
        prov_options = (
            ["Semua provinsi"]
            + sorted(
                lokasi_uptd_fpl["Provinsi"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                    .tolist()
            )
        )
        selected_prov = st.selectbox("Filter provinsi", prov_options, index=0)

        if selected_prov != "Semua provinsi":
            data_tampil = lokasi_uptd_fpl[
                lokasi_uptd_fpl["Provinsi"].astype(str).str.strip()
                == selected_prov
            ]
        else:
            data_tampil = lokasi_uptd_fpl.copy()

        # Tabel lokasi dengan UPTD & FPL
        st.markdown("#### Kab/Kota dengan UPTD **dan** FPL")
        st.caption(
            "Tabel berikut memperlihatkan kabupaten/kota yang sudah memiliki UPTD PPA "
            "dan jaringan FPL sekaligus, termasuk jumlah lembaga pada masing-masing jenis layanan."
        )

        df_both = (
            data_tampil[data_tampil["Kategori Lokasi"] == "UPTD & FPL"]
            .sort_values(["Provinsi", "Kab/Kota"])
            .rename(
                columns={
                    "Provinsi": "Provinsi",
                    "Kab/Kota": "Kabupaten/Kota",
                    "jml_uptd": "Jumlah UPTD",
                    "jml_fpl": "Jumlah lembaga jaringan FPL",
                    "jml_lembaga": "Total lembaga terdaftar",
                }
            )
        )

        if df_both.empty:
            st.info(
                "Belum ada kabupaten/kota yang tercatat memiliki UPTD dan jaringan FPL "
                "sekaligus untuk pilihan filter saat ini."
            )
        else:
            st.dataframe(df_both, use_container_width=True)

        # Ringkasan status semua lokasi
        st.markdown("#### Ringkasan status layanan per kabupaten/kota")
        st.caption(
            "Daftar di bawah ini menunjukkan status setiap kabupaten/kota: "
            "apakah telah memiliki UPTD, jaringan FPL, atau keduanya."
        )

        df_ringkas = (
            data_tampil.sort_values(["Provinsi", "Kab/Kota"])
            .rename(
                columns={
                    "Provinsi": "Provinsi",
                    "Kab/Kota": "Kabupaten/Kota",
                    "jml_uptd": "Jumlah UPTD",
                    "jml_fpl": "Jumlah lembaga jaringan FPL",
                    "Kategori Lokasi": "Status layanan di kab/kota",
                }
            )[
                [
                    "Provinsi",
                    "Kabupaten/Kota",
                    "Status layanan di kab/kota",
                    "Jumlah UPTD",
                    "Jumlah lembaga jaringan FPL",
                ]
            ]
        )

        st.dataframe(df_ringkas, use_container_width=True)


# ============================================================
# TAB: KOREKSI DATA (FORM LENGKAP)
# ============================================================
with tab_koreksi:
    st.markdown("### ✏️ Form Koreksi Data Lembaga")

    suggestions_df = load_suggestions()
    total_suggestions = len(suggestions_df)

    col_info, _ = st.columns([1, 3])
    with col_info:
        st.markdown(
            f"Sudah ada **{total_suggestions}** usulan koreksi yang tersimpan."
        )
        st.caption(
            "Data koreksi ini akan digunakan oleh tim pengelola untuk melakukan "
            "verifikasi dan pembaruan berkala pada direktori."
        )

    st.markdown("---")

    # Quick hint
    hint = st.session_state.get("koreksi_hint")
    if hint:
        st.info(hint)

    org_options = sorted(df["Nama Organisasi"].dropna().unique())
    default_org = st.session_state.get("koreksi_target_org")
    if default_org in org_options:
        default_index = org_options.index(default_org)
    else:
        default_index = 0 if org_options else 0

    with st.form("suggest_form"):
        org_name = st.selectbox(
            "Pilih lembaga yang ingin dikoreksi",
            org_options,
            index=default_index,
        )
        pengaju = st.text_input("Nama Anda")
        kontak = st.text_input("Kontak (email / WA)")
        kolom = st.multiselect(
            "Bagian yang ingin diubah",
            [
                "Alamat Organisasi",
                "Kontak Lembaga/Layanan",
                "Email Lembaga",
                "Profil Organisasi",
                "Layanan Yang Diberikan",
                "Lainnya",
            ],
        )
        usulan = st.text_area(
            "Tuliskan usulan koreksi / tambahan informasi",
            height=150,
        )

        submitted = st.form_submit_button("Kirim usulan koreksi")
        if submitted:
            now = datetime.datetime.now().isoformat(timespec="seconds")
            new_row = {
                "id": (suggestions_df["id"].max() or 0) + 1
                if not suggestions_df.empty
                else 1,
                "timestamp": now,
                "organisasi": org_name,
                "pengaju": pengaju,
                "kontak": kontak,
                "kolom": "; ".join(kolom),
                "usulan": usulan,
                "catatan_internal": "",
                "status": "baru",
            }
            suggestions_df = pd.concat(
                [suggestions_df, pd.DataFrame([new_row])], ignore_index=True
            )
            save_suggestions(suggestions_df)
            st.success("Terima kasih, usulan koreksi Anda sudah tersimpan.")
            st.session_state["koreksi_target_org"] = org_name
            st.session_state["koreksi_hint"] = (
                "Usulan koreksi terakhir sudah dikirim. "
                "Tim akan melakukan verifikasi dan pembaruan data."
            )

    with st.expander("📋 Lihat daftar usulan koreksi yang masuk (ringkas)"):
        if suggestions_df.empty:
            st.caption("Belum ada usulan koreksi yang tersimpan.")
        else:
            st.dataframe(
                suggestions_df[
                    [
                        "timestamp",
                        "organisasi",
                        "pengaju",
                        "kontak",
                        "kolom",
                        "status",
                    ]
                ].sort_values("timestamp", ascending=False),
                use_container_width=True,
            )


# ============================================================
# TAB: ADMIN (RINGKAS)
# ============================================================
with tab_admin:
    st.markdown("### 🗂️ Admin & Ringkasan Data")
    st.caption(
        "Halaman ini memberikan gambaran ringkas komposisi data dalam direktori."
    )

    total_fpl = (df["Sumber Data"] == "Jaringan FPL").sum()
    total_uptd_prov = (df["Sumber Data"] == "UPTD PPA Provinsi").sum()
    total_uptd_kab = (df["Sumber Data"] == "UPTD PPA Kab/Kota").sum()

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total lembaga (semua sumber)", len(df))
    col_b.metric("Lembaga jaringan FPL", int(total_fpl))
    col_c.metric(
        "UPTD PPA (provinsi + kab/kota)",
        int(total_uptd_prov + total_uptd_kab),
    )

    st.markdown("---")

    st.markdown("#### Komposisi kategori layanan (berdasarkan teks layanan)")
    kat_series = (
        df["kategori_layanan"]
        .explode()
        .value_counts()
        .rename_axis("Kategori")
        .reset_index(name="Jumlah lembaga")
    )
    st.dataframe(kat_series, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Status file sumber")
    st.write(f"- File FPL: `{FPL_CSV.name}` – {'✅' if FPL_CSV.exists() else '❌ Tidak ditemukan'}")
    st.write(
        f"- File UPTD: `{UPTD_XLSX.name}` – {'✅' if UPTD_XLSX.exists() else '❌ Tidak ditemukan'}"
    )
    st.write(
        f"- File koreksi lokal: `{SUGGEST_PATH.name}` – "
        f"{'✅' if SUGGEST_PATH.exists() else 'Belum ada, akan dibuat saat pertama kali koreksi dikirim'}"
    )


# ============================================================
# TAB: TENTANG
# ============================================================
with tab_about:
    st.markdown("### ℹ️ Tentang Direktori Layanan 129")
    st.markdown(
        """
        Direktori ini disusun untuk membantu pemetaan lembaga layanan yang bekerja
        dalam pemenuhan hak dan perlindungan korban kekerasan berbasis perempuan dan anak,
        yang terhubung dengan layanan *hotline* SAPA 129.
        
        Sumber data utama meliputi:
        - Jaringan lembaga anggota Forum Pengada Layanan (FPL).
        - UPTD PPA Provinsi (berdasarkan data KemenPPPA).
        - UPTD PPA Kabupaten/Kota (berdasarkan data KemenPPPA).
        
        Informasi dikumpulkan melalui kompilasi data resmi, formulir, serta proses verifikasi internal.
        
        Direktori akan diperbarui secara berkala berdasarkan:
        - Usulan koreksi dari lembaga.
        - Hasil verifikasi lapangan dan koordinasi jaringan.
        
        Di masa depan, setelah koordinat lokasi (latitude/longitude) lebih lengkap,
        akan ditambahkan tampilan **peta interaktif** yang menampilkan sebaran lembaga
        layanan di seluruh Indonesia.
        """
    )
