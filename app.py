import streamlit as st
import pandas as pd
from pathlib import Path
import datetime

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
SUGGEST_PATH = Path(__file__).parent / "edit_suggestions.csv"

# CSS: rapikan layout + turunkan isi tab sedikit
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
    /* Tambah jarak isi tab dari garis tab, supaya judul tidak kepotong */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# 1. LOAD & PREPARE DATA UTAMA
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
    """Selalu baca file koreksi terbaru (tanpa cache)."""
    if SUGGEST_PATH.exists():
        return pd.read_csv(SUGGEST_PATH)
    else:
        return pd.DataFrame(
            columns=[
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
        )


def save_suggestions(df_sug):
    df_sug.to_csv(SUGGEST_PATH, index=False)


df = load_data()
suggestions_df = load_suggestions()

# --------------------------
# 2. HEADER + LOGO
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
# 3. TABS
# --------------------------
tab_dir, tab_about, tab_admin = st.tabs(
    ["📊 Direktori", "ℹ️ Tentang", "✏️ Koreksi Data & Admin"]
)

# ==========================
# TAB 1: DIREKTORI
# ==========================
with tab_dir:
    st.subheader("📊 Direktori Layanan")

    fcol1, fcol2 = st.columns([1, 3])

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

    st.info(
        "Untuk mengusulkan koreksi data lembaga, silakan buka tab "
        "**✏️ Koreksi Data & Admin**."
    )

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
with tab_admin:
    st.subheader("✏️ Ajukan Koreksi Data Lembaga")

    st.markdown(
        """
        Jika Anda **pengelola lembaga** dan menemukan data yang tidak sesuai,
        silakan mengisi form di bawah ini.
        
        Usulan akan muncul di tabel di bawah (status **Pending**) dan
        dapat di-approve / reject oleh admin. Perubahan ke file utama
        tetap dilakukan manual supaya aman.
        """
    )

    # ---------- FORM INPUT KOREKSI ----------
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
                new_id = (
                    suggestions_df["id"].max() + 1
                    if not suggestions_df.empty else 1
                )
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
                    "Admin dapat melihatnya di tabel di bawah."
                )

    st.markdown("---")
    st.subheader("📥 Panel Admin – Review & Approval")

    suggestions_df = load_suggestions()

    if suggestions_df.empty:
        st.caption("Belum ada usulan koreksi yang tercatat.")
    else:
        # urutkan paling baru di atas
        suggestions_df = suggestions_df.sort_values(
            "timestamp", ascending=False
        ).reset_index(drop=True)

        # tampilkan per baris dengan tombol Approve / Reject
        for idx, row in suggestions_df.iterrows():
            box = st.expander(
                f"[{row['status']}] {row['organisasi']} "
                f"(oleh {row['pengaju'] or '—'})",
                expanded=(row["status"] == "Pending"),
            )
            with box:
                st.write(f"**Waktu**: {row['timestamp']}")
                st.write(f"**Kontak**: {row['kontak'] or '—'}")
                st.write(f"**Bagian dikoreksi**: {row['kolom'] or '—'}")
                st.write("**Usulan:**")
                st.write(row["usulan"])

                col_a, col_b, col_c = st.columns([1, 1, 3])
                current_status = row["status"]

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

        # Tombol download semua koreksi
        csv_data = suggestions_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download semua usulan (CSV) untuk diolah offline",
            data=csv_data,
            file_name="edit_suggestions_fpl.csv",
            mime="text/csv",
        )
