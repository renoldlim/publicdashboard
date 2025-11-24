import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
import re

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
# 2. SIMPLE "LLM-LIKE" SEARCH ENGINE
# --------------------------
def search_directory(df: pd.DataFrame, question: str, top_k: int = 5):
    """
    Pencarian sederhana berbasis keyword: hitung berapa banyak token
    pertanyaan muncul di setiap lembaga.
    """
    q = question.lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) >= 3]
    if not tokens:
        return pd.DataFrame()

    scores = []
    for idx, row in df.iterrows():
        parts = [
            str(row.get("Nama Organisasi", "")),
            str(row.get("Alamat Organisasi", "")),
            " ".join(row.get("kategori_layanan", []))
            if isinstance(row.get("kategori_layanan"), (list, tuple))
            else str(row.get("kategori_layanan", "")),
            str(row.get("Layanan Yang Diberikan", "")),
        ]
        doc = " ".join(parts).lower()
        score = sum(doc.count(tok) for tok in tokens)
        if score > 0:
            scores.append((score, idx))

    scores.sort(reverse=True)
    if not scores:
        return pd.DataFrame()

    best_indices = [idx for _, idx in scores[:top_k]]
    return df.loc[best_indices].copy()


# --------------------------
# 3. HEADER + LOGO
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
# 4. TABS
# --------------------------
tab_dir, tab_koreksi, tab_admin, tab_about = st.tabs(
    ["📊 Direktori", "✏️ Koreksi Data", "🗂️ Admin", "ℹ️ Tentang"]
)

# ==========================
# TAB 1: DIREKTORI (CARD VIEW + "LLM")
# ==========================
with tab_dir:
    st.subheader("📊 Direktori Layanan")

    fcol1, fcol2 = st.columns([1, 3])

    # --- Filter ---
    with fcol1:
        st.markdown("#### 🔎 Filter")
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
        st.markdown(
            f"Menampilkan **{filtered_count}** dari **{total_count}** lembaga"
        )

        # ---- LLM-like Q&A section ----
        st.markdown("#### 🤖 Tanya Direktori (Knowledge Search)")

        qa_question = st.text_area(
            "Tulis pertanyaan Anda (contoh: *“Lembaga yang punya shelter aman di Jakarta”*):",
            height=80,
        )
        if st.button("Cari jawaban", key="qa_button"):
            if not qa_question.strip():
                st.warning("Silakan tulis pertanyaan terlebih dahulu.")
            else:
                results = search_directory(df, qa_question, top_k=5)
                if results.empty:
                    st.info(
                        "Belum menemukan lembaga yang cocok dengan pertanyaan tersebut. "
                        "Coba gunakan kata kunci wilayah atau jenis layanan."
                    )
                else:
                    st.write(
                        f"Aku menemukan **{len(results)}** lembaga yang paling relevan:"
                    )
                    for _, row in results.iterrows():
                        nama = row.get("Nama Organisasi", "").strip()
                        alamat = row.get("Alamat Organisasi", "").strip()
                        kategori = row.get("kategori_layanan", [])
                        if isinstance(kategori, str):
                            kategori_list = [
                                k.strip() for k in kategori.split(",") if k.strip()
                            ]
                        else:
                            kategori_list = kategori or []

                        kat_str = ", ".join(kategori_list) if kategori_list else "tidak tercantum"

                        if len(alamat) > 180:
                            alamat_disp = alamat[:180] + "…"
                        else:
                            alamat_disp = alamat

                        st.markdown(
                            f"- **{nama}** – {kat_str}\n"
                            f"  \n  _{alamat_disp}_"
                        )

        st.markdown("---")

        # ---- Card view for filtered results ----
        if filtered_count == 0:
            st.info("Belum ada lembaga yang cocok dengan filter.")
        else:
            cards_df = filtered.reset_index(drop=True)
            n_cols = 2 if len(cards_df) > 1 else 1

            for i in range(0, len(cards_df), n_cols):
                cols = st.columns(n_cols)
                chunk = cards_df.iloc[i:i + n_cols]

                for col, (_, row) in zip(cols, chunk.iterrows()):
                    with col:
                        nama = row.get("Nama Organisasi", "").strip()
                        alamat = row.get("Alamat Organisasi", "").strip()
                        kontak = row.get("Kontak Lembaga/Layanan", "").strip()
                        email = row.get("Email Lembaga", "").strip()
                        kategori = row.get("kategori_layanan", [])

                        if isinstance(kategori, str):
                            kategori_list = [k.strip() for k in kategori.split(",") if k.strip()]
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
            else:
                suggestions_df = load_suggestions()
                if suggestions_df.empty:
                    new_id = 1
                else:
                    new_id = int(suggestions_df["id"].max()) + 1

                new_row = {
                    "id": int(new_id),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
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
                status = row.get("status", "Pending")
                org = row.get("organisasi", "")
                pengaju = row.get("pengaju", "") or "—"

                title = f"[{status}] {org} (oleh {pengaju})"

                box = st.expander(title, expanded=(status == "Pending"))
                with box:
                    st.write(f"**Waktu pengajuan**: {row.get('timestamp', '')}")
                    st.write(f"**Kontak pengaju**: {row.get('kontak', '') or '—'}")
                    st.write(f"**Bagian yang dikoreksi**: {row.get('kolom', '') or '—'}")
                    st.write("**Usulan koreksi:**")
                    st.write(row.get("usulan", ""))

                    col_a, col_b, col_c = st.columns([1, 1, 3])
                    current_status = status

                    if col_a.button(
                        "✅ Approve",
                        key=f"approve_{int(row['id'])}",
                        use_container_width=True,
                    ):
                        suggestions_df.loc[idx, "status"] = "Approved"
                        suggestions_df.loc[idx, "processed_at"] = (
                            datetime.datetime.utcnow().isoformat()
                        )
                        save_suggestions(suggestions_df)
                        st.experimental_rerun()

                    if col_b.button(
                        "❌ Reject",
                        key=f"reject_{int(row['id'])}",
                        use_container_width=True,
                    ):
                        suggestions_df.loc[idx, "status"] = "Rejected"
                        suggestions_df.loc[idx, "processed_at"] = (
                            datetime.datetime.utcnow().isoformat()
                        )
                        save_suggestions(suggestions_df)
                        st.experimental_rerun()

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
