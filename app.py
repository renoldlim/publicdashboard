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
FPL_LOGO_PATH = BASE_DIR / "fpl_logo.png"  # opsional

# ============================================================
# 1. HELPER FUNCTIONS
# ============================================================
def safe_str(val) -> str:
    """Konversi nilai apa pun (termasuk NaN/None) ke string aman."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return str(val).strip()


# ---------- CSS ----------
st.markdown(
    """
    <style>
    body {
        background-color: #f9fafb;
    }
    .block-container {
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
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }
    .org-name {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.15rem;
        color: #111827;
    }
    .org-address {
        font-size: 0.9rem;
        color: #4b5563;
        margin-bottom: 0.35rem;
    }
    .org-meta {
        font-size: 0.86rem;
        color: #374151;
        margin-bottom: 0.15rem;
    }
    .org-meta span.label {
        font-weight: 600;
        color: #6b7280;
    }
    .tag {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        margin: 0 0.25rem 0.25rem 0;
        border-radius: 999px;
        font-size: 0.76rem;
        background-color: #eef2ff;
        color: #3730a3;
        border: 1px solid #c7d2fe;
        white-space: nowrap;
    }

    .source-badge {
        font-size: 0.72rem;
        padding: 0.1rem 0.55rem;
        border-radius: 999px;
        border: 1px solid transparent;
        white-space: nowrap;
    }
    .source-fpl {
        background-color: #f5f3ff;   /* ungu muda */
        color: #5b21b6;              /* ungu tua */
        border-color: #ddd6fe;
    }
    .source-prov {
        background-color: #eff6ff;   /* biru muda */
        color: #1d4ed8;              /* biru tua */
        border-color: #bfdbfe;
    }
    .source-kab {
        background-color: #ecfdf5;   /* hijau muda */
        color: #047857;              /* hijau tua */
        border-color: #bbf7d0;
    }
    .source-other {
        background-color: #f3f4f6;   /* abu muda */
        color: #4b5563;              /* abu tua */
        border-color: #d1d5db;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_source_badge_html(source_raw: str) -> str:
    """Return HTML span untuk badge sumber data dengan warna berbeda."""
    source = safe_str(source_raw) or "Tidak diketahui"
    s = source.lower()

    if "fpl" in s:
        css_class = "source-badge source-fpl"
    elif "provinsi" in s:
        css_class = "source-badge source-prov"
    elif "kab/kota" in s or "kabupaten" in s or "kab." in s or "kota" in s:
        css_class = "source-badge source-kab"
    else:
        css_class = "source-badge source-other"

    return f'<span class="{css_class}">{source}</span>'


# ============================================================
# 2. LOAD & PREPARE DATA (FPL + UPTD PROV + UPTD KAB/KOTA)
# ============================================================

# definisi kategori layanan dari teks
KATEGORI_DEFS = {
    "Evakuasi": ["evakuasi"],
    "Hukum / Litigasi": ["hukum", "litigasi", "bantuan hukum", "pendampingan hukum"],
    "Konseling & Psikologis": [
        "konseling", "psikolog", "psikososial", "support group", "trauma"
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
        if any(kw in text_l for kw in keywords):
            hasil.add(kat)
    if not hasil:
        hasil.add("Lainnya")
    return sorted(hasil)


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

    # pastikan kolom standar
    for col in [
        "Nama Organisasi",
        "Alamat Organisasi",
        "Kontak Lembaga/Layanan",
        "Email Lembaga",
        "Profil Organisasi",
        "Layanan Yang Diberikan",
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
        ]
    ]

def _read_excel_safe(path: Path, sheet_name: str):
    """Coba baca Excel; kalau gagal (file/engine), kembalikan None."""
    if not path.exists():
        return None
    try:
        return pd.read_excel(
            path,
            sheet_name=sheet_name,
            header=None,
            engine="openpyxl",  # paksa pakai openpyxl
        )
    except ImportError:
        # Kalau openpyxl belum terinstall, jangan crash
        st.warning(
            f"Tidak dapat membaca '{path.name}' (library openpyxl belum terinstall). "
            "Data UPTD akan dilewati sampai dependensi terpasang."
        )
        return None
    except Exception as e:
        st.warning(
            f"Gagal membaca sheet '{sheet_name}' dari '{path.name}': {e}. "
            "Data UPTD akan dilewati."
        )
        return None
        
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
    out["Kontak Lembaga/Layanan"] = (
        df["HOTLINE"].replace({0: np.nan}).fillna(df["TELP_KANTOR"])
    )
    out["Email Lembaga"] = ""
    out["Profil Organisasi"] = "UPTD PPA tingkat provinsi di Provinsi " + prov_clean
    out["Layanan Yang Diberikan"] = (
        "Layanan pengaduan; konseling psikologis; pendampingan hukum; rujukan layanan."
    )
    out["Sumber Data"] = "UPTD PPA Provinsi"
    out["Latitude"] = np.nan
    out["Longitude"] = np.nan

    return out


def load_uptd_kabkota() -> pd.DataFrame:
    raw = _read_excel_safe(UPTD_XLSX, sheet_name="UPTD PPA KabKota")
    if raw is None:
        return pd.DataFrame()

    df = raw.iloc[3:].copy()
    df = df.rename(
        columns={
            0: "PROVINSI",
            2: "KABKOTA",
            4: "ALAMAT_KANTOR",
            5: "TELP_KANTOR",
            6: "HOTLINE",
        }
    )

    df = df[df["KABKOTA"].notna()]
    df = df[df["KABKOTA"] != "(4)"]  # buang baris header dalam data

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
        "UPTD PPA tingkat kabupaten/kota di "
        + kab_clean
        + ", Provinsi "
        + prov_clean
    )
    out["Layanan Yang Diberikan"] = (
        "Layanan pengaduan; konseling psikologis; pendampingan hukum; rujukan layanan."
    )
    out["Sumber Data"] = "UPTD PPA Kab/Kota"
    out["Latitude"] = np.nan
    out["Longitude"] = np.nan

    return out


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """Gabungkan FPL + UPTD PPA Provinsi + UPTD PPA Kab/Kota, plus kategori."""
    fpl = load_fpl()
    uptd_prov = load_uptd_prov()
    uptd_kab = load_uptd_kabkota()

    df = pd.concat([fpl, uptd_prov, uptd_kab], ignore_index=True, sort=False)

    # normalisasi layanan & kategori
    raw_text = (
        df.get("Layanan Yang Diberikan", "")
        .fillna("")
        .astype(str)
        .str.replace("\n", " ")
    )
    df["layanan_list"] = raw_text.apply(
        lambda t: [p.strip() for p in t.replace(";", ";").split(";") if p.strip()]
    )
    df["kategori_layanan"] = raw_text.apply(_extract_kategori)

    # kolom standar
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


# ============================================================
# 3. SUGGESTION DATA (KOREKSI)
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
        "lat",
        "lon",
        "status",
        "processed_at",
    ]

    if SUGGEST_PATH.exists():
        df = pd.read_csv(SUGGEST_PATH)

        if "id" not in df.columns:
            df["id"] = range(1, len(df) + 1)
        if "status" not in df.columns:
            df["status"] = "Pending"
        if "processed_at" not in df.columns:
            df["processed_at"] = ""
        if "lat" not in df.columns:
            df["lat"] = ""
        if "lon" not in df.columns:
            df["lon"] = ""

        for c in required_cols:
            if c not in df.columns:
                df[c] = ""

        df["id"] = pd.to_numeric(df["id"], errors="coerce")
        if df["id"].isna().any():
            df["id"] = range(1, len(df) + 1)

        return df[required_cols]

    else:
        return pd.DataFrame(columns=required_cols)


def save_suggestions(df_sug: pd.DataFrame):
    df_sug.to_csv(SUGGEST_PATH, index=False)


# ============================================================
# 4. INIT STATE & LOAD DF
# ============================================================
df = load_data()

if "page" not in st.session_state:
    st.session_state["page"] = 1
if "koreksi_target_org" not in st.session_state:
    st.session_state["koreksi_target_org"] = None
if "koreksi_hint" not in st.session_state:
    st.session_state["koreksi_hint"] = None
if "detail_org" not in st.session_state:
    st.session_state["detail_org"] = None

# ============================================================
# 5. HEADER
# ============================================================
logo_col, title_col = st.columns([1, 4])
with logo_col:
    if FPL_LOGO_PATH.exists():
        st.image(FPL_LOGO_PATH, width=90)
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

if st.session_state.get("koreksi_hint"):
    st.info(st.session_state["koreksi_hint"])

# ============================================================
# 6. TABS
# ============================================================
tab_dir, tab_koreksi, tab_admin, tab_about = st.tabs(
    ["📊 Direktori", "✏️ Koreksi Data", "🗂️ Admin", "ℹ️ Tentang"]
)

# ============================================================
# TAB: DIREKTORI
# ============================================================
with tab_dir:
    st.markdown("### 📊 Direktori Layanan")

    fcol1, fcol2 = st.columns([1, 3])

    # ----- FILTER -----
    with fcol1:
        st.markdown("#### 🔎 Filter")
        name = st.text_input("Cari Nama Organisasi")
        addr = st.text_input("Cari Alamat / Daerah")

        all_categories = sorted({c for cats in df["kategori_layanan"] for c in cats})
        selected_categories = st.multiselect("Kategori Layanan", all_categories)

        if st.button("Reset filter", use_container_width=True):
            name = ""
            addr = ""
            selected_categories = []
            st.session_state["page"] = 1
            st.session_state["detail_org"] = None
            st.rerun()

    filtered = df.copy()
    if name:
        filtered = filtered[filtered["Nama Organisasi"]
                            .fillna("")
                            .str.contains(name, case=False, na=False)]
    if addr:
        filtered = filtered[filtered["Alamat Organisasi"]
                            .fillna("")
                            .str.contains(addr, case=False, na=False)]

    if selected_categories:
        def has_cat(lst):
            return any(c in lst for c in selected_categories)

        filtered = filtered[filtered["kategori_layanan"].apply(has_cat)]

    total_count = len(df)
    filtered_count = len(filtered)

    # ----- PAGINATION -----
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
                    st.session_state["detail_org"] = None
                    st.rerun()
            with mid_col:
                st.markdown(
                    f"<div style='text-align:center; padding-top:4px;'>Halaman "
                    f"<b>{st.session_state['page']}</b> dari {total_pages}</div>",
                    unsafe_allow_html=True,
                )
            with next_col:
                if st.button("▶", disabled=st.session_state["page"] >= total_pages):
                    st.session_state["page"] += 1
                    st.session_state["detail_org"] = None
                    st.rerun()

    # ----- CARD LIST -----
    with fcol2:
        st.markdown(
            f"Menampilkan **{filtered_count}** dari **{total_count}** lembaga"
        )
        st.markdown("---")

        if filtered_count == 0:
            st.info("Belum ada lembaga yang cocok dengan filter.")
        else:
            cards_df = filtered.reset_index(drop=True)
            page = st.session_state["page"]
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_df = cards_df.iloc[start_idx:end_idx]

            st.caption(
                f"Menampilkan lembaga nomor {start_idx+1}–"
                f"{min(end_idx, len(cards_df))} dari {len(cards_df)} hasil."
            )

            n_cols = 2 if len(page_df) > 1 else 1

            for i in range(0, len(page_df), n_cols):
                cols = st.columns(n_cols)
                chunk = page_df.iloc[i:i + n_cols]

                for col, (idx_row, row) in zip(cols, chunk.iterrows()):
                    with col:
                        nama = safe_str(row.get("Nama Organisasi", ""))
                        alamat = safe_str(row.get("Alamat Organisasi", ""))
                        kontak = safe_str(row.get("Kontak Lembaga/Layanan", ""))
                        email = safe_str(row.get("Email Lembaga", ""))
                        kategori = row.get("kategori_layanan", [])
                        sumber = safe_str(row.get("Sumber Data", ""))

                        if isinstance(kategori, str):
                            kategori_list = [
                                k.strip() for k in kategori.split(",") if k.strip()
                            ]
                        else:
                            kategori_list = kategori or []

                        alamat_disp = alamat if len(alamat) <= 200 else alamat[:200] + "…"

                        tags_html = "".join(
                            f'<span class="tag">{cat}</span>' for cat in kategori_list
                        )
                        badge_html = get_source_badge_html(sumber)

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
                        with bcol1:
                            if st.button(
                                "✏️ Usulkan koreksi",
                                key=f"suggest_{start_idx + idx_row}",
                                use_container_width=True,
                            ):
                                st.session_state["koreksi_target_org"] = nama
                                st.session_state["koreksi_hint"] = (
                                    f"Lembaga **{nama}** sudah otomatis dipilih "
                                    "di tab **Koreksi Data**. Silakan buka tab tersebut "
                                    "untuk mengisi formulir koreksi (termasuk koordinat lokasi bila ada)."
                                )
                                st.rerun()
                        with bcol2:
                            if st.button(
                                "👁 Lihat detail",
                                key=f"detail_{start_idx + idx_row}",
                                use_container_width=True,
                            ):
                                st.session_state["detail_org"] = nama
                                st.rerun()

            # ----- DETAIL VIEW -----
            if st.session_state.get("detail_org"):
                detail_org = st.session_state["detail_org"]
                detail_df = df[df["Nama Organisasi"] == detail_org]
                if not detail_df.empty:
                    r = detail_df.iloc[0]

                    st.markdown("---")
                    st.markdown("### 📄 Profil Lembaga")

                    sumber = safe_str(r.get("Sumber Data", ""))
                    badge_html = get_source_badge_html(sumber)

                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem;'>"
                        f"<div><b>{safe_str(r.get('Nama Organisasi', ''))}</b></div>"
                        f"<div>{badge_html}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.markdown("**Alamat**")
                        st.write(safe_str(r.get("Alamat Organisasi", "")) or "—")

                        st.markdown("**Kontak Layanan**")
                        st.write(safe_str(r.get("Kontak Lembaga/Layanan", "")) or "—")

                        st.markdown("**Email Layanan**")
                        st.write(safe_str(r.get("Email Lembaga", "")) or "—")

                        st.markdown("**Profil Organisasi**")
                        st.write(safe_str(r.get("Profil Organisasi", "")) or "—")

                    with col_b:
                        st.markdown("**Koordinat Lokasi**")
                        lat = safe_str(r.get("Latitude", ""))
                        lon = safe_str(r.get("Longitude", ""))
                        if lat and lon:
                            st.write(f"Lat: `{lat}`, Lon: `{lon}`")
                        else:
                            st.write(
                                "Belum ada koordinat latitude/longitude. "
                                "Dapat diusulkan melalui tab **Koreksi Data**."
                            )

                        st.markdown("**Kategori Layanan**")
                        kat = r.get("kategori_layanan", [])
                        if isinstance(kat, (list, tuple)) and kat:
                            for c in kat:
                                st.markdown(f"- {c}")
                        else:
                            st.write("—")

                    st.markdown("**Layanan yang diberikan**")
                    layanan_list = r.get("layanan_list", [])
                    if isinstance(layanan_list, (list, tuple)) and layanan_list:
                        for item in layanan_list:
                            st.write(f"- {safe_str(item)}")
                    else:
                        st.write("—")

                    if st.button("Tutup detail"):
                        st.session_state["detail_org"] = None
                        st.rerun()

            # ----- TABLE + DOWNLOAD -----
            with st.expander("📋 Tampilkan semua hasil dalam bentuk tabel"):
                table_df = filtered.copy()
                cols_table = [
                    c
                    for c in [
                        "Nama Organisasi",
                        "Alamat Organisasi",
                        "Kontak Lembaga/Layanan",
                        "Email Lembaga",
                        "kategori_layanan",
                        "Sumber Data",
                        "Latitude",
                        "Longitude",
                    ]
                    if c in table_df.columns
                ]
                table_df = table_df[cols_table].copy()

                if "kategori_layanan" in table_df.columns:
                    table_df["kategori_layanan"] = table_df["kategori_layanan"].apply(
                        lambda x: ", ".join(x) if isinstance(x, (list, tuple)) else safe_str(x)
                    )

                table_df = table_df.rename(
                    columns={
                        "Nama Organisasi": "Organisation Name",
                        "Alamat Organisasi": "Address",
                        "Kontak Lembaga/Layanan": "Service Contact",
                        "Email Lembaga": "Service Email",
                        "kategori_layanan": "Service Categories",
                        "Sumber Data": "Source",
                    }
                )
                table_df.insert(0, "No", range(1, len(table_df) + 1))

                st.dataframe(table_df, use_container_width=True)

                csv_data = table_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download filtered results (CSV)",
                    data=csv_data,
                    file_name="direktori_layanan129_filtered.csv",
                    mime="text/csv",
                )

# ============================================================
# TAB: KOREKSI DATA
# ============================================================
with tab_koreksi:
    st.markdown("### ✏️ Form Koreksi Data Lembaga")

    suggestions_df = load_suggestions()
    total_suggestions = len(suggestions_df)

    col_info, _ = st.columns([1, 3])
    with col_info:
        st.metric("Total usulan koreksi yang tercatat", total_suggestions)

    st.markdown(
        """
        Jika Anda **pengelola lembaga** dan menemukan data yang tidak sesuai,
        silakan mengisi form berikut.  
        Anda juga dapat menambahkan/merapikan **koordinat lokasi (Latitude & Longitude)** 
        supaya di masa depan lembaga bisa ditampilkan dalam peta Indonesia.
        """
    )

    org_options = sorted(df["Nama Organisasi"].dropna().unique())
    default_org = st.session_state.get("koreksi_target_org", None)
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
                "Layanan Yang Diberikan",
                "Profil Organisasi",
                "Koordinat (Latitude/Longitude)",
                "Lainnya",
            ],
        )

        st.markdown("**Opsional – Koordinat Lokasi Lembaga**")
        lat_col, lon_col = st.columns(2)
        with lat_col:
            lat_val = st.text_input("Latitude (contoh: -6.1767)")
        with lon_col:
            lon_val = st.text_input("Longitude (contoh: 106.8305)")

        usulan = st.text_area(
            "Tuliskan data baru / koreksi yang diusulkan",
            height=150,
        )

        submitted = st.form_submit_button("Kirim Usulan Koreksi")

        if submitted:
            if not usulan.strip() and not (lat_val.strip() and lon_val.strip()):
                st.warning(
                    "Mohon isi perubahan yang diusulkan atau koordinat latitude/longitude."
                )
            else:
                suggestions_df = load_suggestions()
                new_id = 1 if suggestions_df.empty else int(suggestions_df["id"].max()) + 1

                new_row = {
                    "id": int(new_id),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "organisasi": org_name,
                    "pengaju": pengaju,
                    "kontak": kontak,
                    "kolom": "; ".join(kolom) if kolom else "",
                    "usulan": usulan.strip(),
                    "lat": lat_val.strip(),
                    "lon": lon_val.strip(),
                    "status": "Pending",
                    "processed_at": "",
                }
                suggestions_df = pd.concat(
                    [suggestions_df, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                save_suggestions(suggestions_df)
                st.session_state["koreksi_hint"] = None
                st.success(
                    "Terima kasih, usulan koreksi Anda sudah tercatat. "
                    "Admin akan meninjau sebelum mengubah data utama."
                )

# ============================================================
# TAB: ADMIN
# ============================================================
with tab_admin:
    st.markdown("### 🗂️ Panel Admin – Review & Approval")

    pwd = st.text_input(
        "Masukkan admin password untuk mengakses panel:",
        type="password",
        key="admin_pwd",
    )

    if pwd != "renolds":
        st.info("Masukkan password yang benar untuk melihat dan mengelola usulan koreksi.")
    else:
        suggestions_df = load_suggestions()

        if suggestions_df.empty:
            st.caption("Belum ada usulan koreksi yang tercatat.")
        else:
            suggestions_df = suggestions_df.sort_values(
                "timestamp", ascending=False
            ).reset_index(drop=True)

            pending_count = (suggestions_df["status"] == "Pending").sum()
            st.metric("Usulan Pending", pending_count)

            for idx, row in suggestions_df.iterrows():
                status = safe_str(row.get("status", "Pending"))
                org = safe_str(row.get("organisasi", ""))
                pengaju = safe_str(row.get("pengaju", "")) or "—"

                title = f"[{status}] {org} (oleh {pengaju})"
                box = st.expander(title, expanded=(status == "Pending"))

                with box:
                    st.write(f"**Waktu pengajuan**: {safe_str(row.get('timestamp', ''))}")
                    st.write(f"**Kontak pengaju**: {safe_str(row.get('kontak', '')) or '—'}")
                    st.write(f"**Bagian yang dikoreksi**: {safe_str(row.get('kolom', '')) or '—'}")
                    st.write("**Usulan koreksi:**")
                    st.write(safe_str(row.get("usulan", "")) or "—")

                    lat_s = safe_str(row.get("lat", ""))
                    lon_s = safe_str(row.get("lon", ""))
                    if lat_s or lon_s:
                        st.write("**Usulan Koordinat:**")
                        st.write(f"Lat: `{lat_s or '-'}`, Lon: `{lon_s or '-'}`")

                    col_a, col_b, col_c = st.columns([1, 1, 3])
                    current_status = status

                    if col_a.button(
                        "✅ Approve",
                        key=f"approve_{int(row['id'])}",
                        use_container_width=True,
                    ):
                        suggestions_df.loc[idx, "status"] = "Approved"
                        suggestions_df.loc[idx, "processed_at"] = (
                            datetime.datetime.now(datetime.timezone.utc).isoformat()
                        )
                        save_suggestions(suggestions_df)
                        st.rerun()

                    if col_b.button(
                        "❌ Reject",
                        key=f"reject_{int(row['id'])}",
                        use_container_width=True,
                    ):
                        suggestions_df.loc[idx, "status"] = "Rejected"
                        suggestions_df.loc[idx, "processed_at"] = (
                            datetime.datetime.now(datetime.timezone.utc).isoformat()
                        )
                        save_suggestions(suggestions_df)
                        st.rerun()

                    col_c.write(f"Status sekarang: **{current_status}**")

            st.markdown("---")
            st.caption(
                "Catatan: koordinat yang telah di-approve dapat dimasukkan ke kolom "
                "`Latitude` dan `Longitude` di file utama untuk keperluan peta."
            )

            csv_data = suggestions_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download semua usulan (CSV) untuk diolah offline",
                data=csv_data,
                file_name="edit_suggestions_layanan129.csv",
                mime="text/csv",
            )

# ============================================================
# TAB: TENTANG
# ============================================================
with tab_about:
    st.markdown("### ℹ️ Tentang Direktori Layanan 129")
    st.markdown(
        """
        Direktori ini disusun untuk membantu:

        - Penyintas kekerasan dan pendamping menemukan **lembaga layanan yang relevan dan terdekat**.
        - Jaringan FPL, UPTD PPA, dan mitra melihat **peta layanan** berdasarkan jenis layanan dan wilayah.
        
        **Sumber data utama:**
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
