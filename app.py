import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
import math

# --------------------------
# CONFIG & CONSTANTS
# --------------------------
st.set_page_config(
    page_title="Direktori Layanan FPL",
    page_icon="📚",
    layout="wide",
)

DATA_PATH = Path(__file__).parent / "fpl database.csv"
FPL_LOGO_PATH = Path(__file__).parent / "fpl_logo.png"  # optional
SUGGEST_PATH = Path(__file__).parent / "edit_suggestions.csv"

# --------------------------
# HELPER: SAFE STRING
# --------------------------
def safe_str(val) -> str:
    """Konversi nilai apa pun (termasuk NaN/float/None) ke string aman."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return str(val).strip()


# CSS: layout, tabs, card & tag
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
    /* jarak isi tab dari garis tab */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }
    /* card lembaga */
    .org-card {
        padding: 0.75rem 1rem;
        margin-bottom: 0.9rem;
        border-radius: 0.85rem;
        border: 1px solid #e5e7eb;
        background-color: #ffffff;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    .org-name {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.15rem;
    }
    .org-address {
        font-size: 0.88rem;
        color: #4b5563;
        margin-bottom: 0.25rem;
    }
    .org-meta {
        font-size: 0.85rem;
        color: #374151;
        margin-bottom: 0.2rem;
    }
    .org-meta span.label {
        font-weight: 600;
        color: #6b7280;
    }
    .tag {
        display: inline-block;
        padding: 0.15rem 0.55rem;
        margin: 0 0.25rem 0.25rem 0;
        border-radius: 999px;
        font-size: 0.75rem;
        background-color: #eef2ff;  /* indigo-50 */
        color: #3730a3;              /* indigo-800 */
        border: 1px solid #c7d2fe;   /* indigo-200 */
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# 1. LOAD & PREPARE MAIN DATA
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

    # mapping layanan ke kategori
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


def load_suggestions():
    """Baca file koreksi dan pastikan semua kolom yang dibutuhkan ada."""
    required_cols = [
        "id",
        "timestamp",
        "organisasi",
        "pengaju",
        "kontak",
        "kolom",
        "usulan",
        "status",
        "processed_at",
    ]

    if SUGGEST_PATH.exists():
        df = pd.read_csv(SUGGEST_PATH)

        # Tambah kolom yang belum ada
        if "id" not in df.columns:
            df["id"] = range(1, len(df) + 1)
        if "status" not in df.columns:
            df["status"] = "Pending"
        if "processed_at" not in df.columns:
            df["processed_at"] = ""

        for c in required_cols:
            if c not in df.columns:
                df[c] = ""

        df["id"] = pd.to_numeric(df["id"], errors="coerce")
        if df["id"].isna().any():
            df["id"] = range(1, len(df) + 1)

        return df[required_cols]
    else:
        # belum ada file → mulai dengan df kosong berkolom lengkap
        return pd.DataFrame(columns=required_cols)


def save_suggestions(df_sug: pd.DataFrame):
    df_sug.to_csv(SUGGEST_PATH, index=False)


df = load_data()

# --------------------------
# INIT SESSION STATE
# --------------------------
if "page" not in st.session_state:
    st.session_state["page"] = 1
if "koreksi_target_org" not in st.session_state:
    st.session_state["koreksi_target_org"] = None
if "koreksi_hint" not in st.session_state:
    st.session_state["koreksi_hint"] = None
if "detail_org" not in st.session_state:
    st.session_state["detail_org"] = None

# --------------------------
# 3. HEADER + LOGO
# --------------------------
st.divider()
st.divider()
logo_col, title_col = st.columns([3, 4])

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

# Banner hint (misalnya setelah klik “Usulkan koreksi”)
if st.session_state.get("koreksi_hint"):
    st.info(st.session_state["koreksi_hint"])

# --------------------------
# 4. TABS
# --------------------------
tab_dir, tab_koreksi, tab_admin, tab_about = st.tabs(
    ["📊 Direktori", "✏️ Koreksi Data", "🗂️ Admin", "ℹ️ Tentang"]
)

# ==========================
# TAB 1: DIREKTORI (CARD VIEW + PAGINATION + TABLE)
# ==========================
with tab_dir:
    st.subheader("📊 Direktori Layanan")

    fcol1, fcol2 = st.columns([1, 3])

    # --- Filter widgets (kolom kiri) ---
    with fcol1:
        st.markdown("#### 🔎 Filter")
        name = st.text_input("Cari Nama Organisasi")
        addr = st.text_input("Cari Alamat / Daerah")

        all_categories = sorted({c for cats in df["kategori_layanan"] for c in cats})
        selected_categories = st.multiselect("Kategori Layanan", all_categories)

        if st.button("Reset filter"):
            name = ""
            addr = ""
            selected_categories = []
            st.session_state["page"] = 1
            st.session_state["detail_org"] = None
            st.rerun()

    # --- Terapkan filter ---
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

    # --- Pagination controls (kolom kiri, di bawah filter) ---
    page_size = 10
    total_pages = max(1, math.ceil(max(filtered_count, 1) / page_size))

    # pastikan page tidak out of range
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
                    f"<div style='text-align:center;'>Halaman "
                    f"<b>{st.session_state['page']}</b> / {total_pages}</div>",
                    unsafe_allow_html=True,
                )

            with next_col:
                if st.button("▶", disabled=st.session_state["page"] >= total_pages):
                    st.session_state["page"] += 1
                    st.session_state["detail_org"] = None
                    st.rerun()

    # --- Konten utama (kolom kanan) ---
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

            # ---------- CARD VIEW (10 per page) ----------
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

                        if isinstance(kategori, str):
                            kategori_list = [
                                k.strip() for k in kategori.split(",") if k.strip()
                            ]
                        else:
                            kategori_list = kategori or []

                        if len(alamat) > 200:
                            alamat_disp = alamat[:200] + "…"
                        else:
                            alamat_disp = alamat

                        tags_html = ""
                        for cat in kategori_list:
                            tags_html += f'<span class="tag">{cat}</span>'

                        card_html = f"""
                        <div class="org-card">
                            <div class="org-name">{nama}</div>
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

                        bcol1, bcol2 = st.columns([1, 1])
                        with bcol1:
                            # Tombol kecil untuk usulkan koreksi
                            if st.button(
                                "✏️ Usulkan koreksi",
                                key=f"suggest_{start_idx + idx_row}",
                            ):
                                st.session_state["koreksi_target_org"] = nama
                                st.session_state["koreksi_hint"] = (
                                    f"Lembaga **{nama}** sudah otomatis dipilih "
                                    "di tab **Koreksi Data**. Silakan buka tab tersebut "
                                    "untuk mengisi formulir koreksi."
                                )
                                st.rerun()
                        with bcol2:
                            # Tombol lihat detail
                            if st.button(
                                "👁 Lihat detail",
                                key=f"detail_{start_idx + idx_row}",
                            ):
                                st.session_state["detail_org"] = nama
                                st.rerun()

            # ---------- DETAIL VIEW (CV STYLE) ----------
            if st.session_state.get("detail_org"):
                detail_org = st.session_state["detail_org"]
                detail_df = df[df["Nama Organisasi"] == detail_org]
                if not detail_df.empty:
                    r = detail_df.iloc[0]

                    st.markdown("---")
                    st.markdown("### 📄 Profil Lembaga")
                    st.markdown(f"**{safe_str(r.get('Nama Organisasi', ''))}**")

                    st.markdown("**Alamat**")
                    st.write(safe_str(r.get("Alamat Organisasi", "")) or "—")

                    st.markdown("**Kontak Layanan**")
                    st.write(safe_str(r.get("Kontak Lembaga/Layanan", "")) or "—")

                    st.markdown("**Email Layanan**")
                    st.write(safe_str(r.get("Email Lembaga", "")) or "—")

                    # Website jika ada kolom
                    if "Website" in r.index:
                        st.markdown("**Website**")
                        st.write(safe_str(r.get("Website", "")) or "—")

                    st.markdown("**Profil Organisasi**")
                    profil = safe_str(r.get("Profil Organisasi", ""))
                    st.write(profil or "—")

                    st.markdown("**Layanan yang diberikan**")
                    layanan_list = r.get("layanan_list", [])
                    if isinstance(layanan_list, (list, tuple)) and layanan_list:
                        for item in layanan_list:
                            st.write(f"- {safe_str(item)}")
                    else:
                        layanan_raw = safe_str(r.get("Layanan Yang Diberikan", ""))
                        if layanan_raw:
                            for item in layanan_raw.split(";"):
                                item = item.strip()
                                if item:
                                    st.write(f"- {item}")
                        else:
                            st.write("—")

                    # kategori layanan
                    st.markdown("**Kategori Layanan**")
                    kat = r.get("kategori_layanan", [])
                    if isinstance(kat, (list, tuple)) and kat:
                        st.write(", ".join(kat))
                    else:
                        st.write("—")

                    if st.button("Tutup detail"):
                        st.session_state["detail_org"] = None
                        st.rerun()

            # ---------- EXPANDER: FULL TABLE + DOWNLOAD ----------
            with st.expander("📋 Tampilkan semua hasil dalam bentuk tabel"):
                table_df = filtered.copy()

                cols_table = [c for c in [
                    "Nama Organisasi",
                    "Alamat Organisasi",
                    "Kontak Lembaga/Layanan",
                    "Email Lembaga",
                    "kategori_layanan",
                ] if c in table_df.columns]

                table_df = table_df[cols_table].copy()

                if "kategori_layanan" in table_df.columns:
                    def cat_to_text(x):
                        if isinstance(x, (list, tuple)):
                            return ", ".join(x)
                        return safe_str(x)
                    table_df["kategori_layanan"] = table_df["kategori_layanan"].apply(cat_to_text)

                # Rename header ke gaya internasional
                table_df = table_df.rename(columns={
                    "Nama Organisasi": "Organisation Name",
                    "Alamat Organisasi": "Address",
                    "Kontak Lembaga/Layanan": "Service Contact",
                    "Email Lembaga": "Service Email",
                    "kategori_layanan": "Service Categories",
                })

                # Tambah nomor urut
                table_df.insert(0, "No", range(1, len(table_df) + 1))

                st.dataframe(table_df, use_container_width=True)

                csv_data = table_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download filtered results (CSV)",
                    data=csv_data,
                    file_name="fpl_directory_filtered.csv",
                    mime="text/csv",
                )

# ==========================
# TAB 2: KOREKSI DATA (FORM + COUNT)
# ==========================
with tab_koreksi:
    st.subheader("✏️ Form Koreksi Data Lembaga")

    suggestions_df = load_suggestions()
    total_suggestions = len(suggestions_df)

    col_info, col_blank = st.columns([1, 3])
    with col_info:
        st.metric("Total usulan koreksi yang tercatat", total_suggestions)

    st.markdown(
        """
        Jika Anda **pengelola lembaga** dan menemukan data yang tidak sesuai,
        silakan mengisi form berikut. Usulan Anda akan muncul di tab **Admin**
        untuk ditinjau dan disetujui oleh tim.
        """
    )

    # default lembaga dari tombol "Usulkan koreksi"
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
            key="koreksi_org_select",
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
            else:
                suggestions_df = load_suggestions()
                if suggestions_df.empty:
                    new_id = 1
                else:
                    new_id = int(suggestions_df["id"].max()) + 1

                new_row = {
                    "id": int(new_id),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "organisasi": org_name,
                    "pengaju": pengaju,
                    "kontak": kontak,
                    "kolom": "; ".join(kolom) if kolom else "",
                    "usulan": usulan.strip(),
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

# ==========================
# TAB 3: ADMIN – REVIEW & APPROVAL (WITH PASSWORD)
# ==========================
with tab_admin:
    st.subheader("🗂️ Panel Admin – Review & Approval")

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
                    st.write(safe_str(row.get("usulan", "")))

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

            csv_data = suggestions_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download semua usulan (CSV) untuk diolah offline",
                data=csv_data,
                file_name="edit_suggestions_fpl.csv",
                mime="text/csv",
            )

# ==========================
# TAB 4: TENTANG (PALING KANAN)
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
