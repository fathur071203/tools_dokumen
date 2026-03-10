from dataclasses import dataclass
from typing import Any
import pandas as pd

import streamlit as st

from src.models.file_locker_model import PasswordMode


@dataclass
class EncryptViewResult:
    go_home: bool
    go_decrypt: bool
    encrypt_clicked: bool
    uploads: list[Any]
    mode: str
    passwords: list[str]


class FileLockerEncryptView:
    def render(self) -> EncryptViewResult:
        # Header dengan spacing lebih besar untuk menghindari toolbar
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        col_a, col_b = st.columns([1, 8])
        with col_a:
            go_home = st.button("← Kembali", key="btn_home_encrypt")
        with col_b:
            st.markdown("## 🔐 File Locker")
            st.markdown("Enkripsi file dengan password. Bisa 1 password untuk semua file, atau password berbeda untuk tiap file.")

        st.markdown("---")
        
        col_nav1, col_nav2 = st.columns([2, 8])
        with col_nav1:
            go_decrypt = st.button("🔓 Buka Halaman Dekripsi", use_container_width=True, key="btn_decrypt_nav")

        uploads = st.file_uploader(
            "Upload file (boleh banyak file)",
            accept_multiple_files=True,
            help="Semua tipe file didukung.",
            type=None,
        )

        if not uploads:
            st.info("Belum ada file. Upload dulu untuk mulai enkripsi.")
            return EncryptViewResult(
                go_home=go_home,
                go_decrypt=go_decrypt,
                encrypt_clicked=False,
                uploads=[],
                mode=PasswordMode.SINGLE,
                passwords=[],
            )

        st.markdown("---")

        mode_label = st.radio(
            "⚙️ Mode Password",
            options=["1 password untuk semua file", "Password berbeda per file"],
            horizontal=True,
            key="mode_password_radio"
        )

        mode = PasswordMode.SINGLE if mode_label.startswith("1 password") else PasswordMode.INDIVIDUAL
        passwords: list[str] = []

        if mode == PasswordMode.SINGLE:
            single_password = st.text_input(
                "Password (minimal 8 karakter)",
                type="password",
                key="single_encrypt_password",
            )
            passwords = [single_password] * len(uploads)
            
            # Display file list
            st.markdown("### 📋 File yang akan dienkripsi")
            file_data = []
            for i, upload in enumerate(uploads, start=1):
                size_kb = upload.size / 1024
                file_data.append({
                    "No": i,
                    "Nama File": upload.name,
                    "Ukuran (KB)": f"{size_kb:.2f}",
                    "Password": single_password if single_password else "—"
                })
            
            df = pd.DataFrame(file_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.markdown("### 📋 File dan Password")
            st.caption("Masukkan password untuk setiap file di tabel bawah")
            
            # Create table with file info and password inputs
            file_data = []
            for i, upload in enumerate(uploads, start=1):
                size_kb = upload.size / 1024
                file_data.append({
                    "No": i,
                    "Nama File": upload.name,
                    "Ukuran (KB)": f"{size_kb:.2f}",
                })
            
            # Display file list first
            df = pd.DataFrame(file_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Create columns for password input
            st.markdown("#### Masukkan Password untuk Setiap File")
            
            col1, col2, col3 = st.columns([1, 2, 3])
            with col1:
                st.markdown("**No**")
            with col2:
                st.markdown("**File**")
            with col3:
                st.markdown("**Password**")
            
            st.markdown("---")
            
            passwords = []
            for idx, upload in enumerate(uploads):
                col1, col2, col3 = st.columns([1, 2, 3])
                with col1:
                    st.write(f"{idx + 1}")
                with col2:
                    st.write(upload.name)
                with col3:
                    per_file_password = st.text_input(
                        "Password",
                        type="password",
                        key=f"per_file_pwd_{idx}_{upload.name}",
                        label_visibility="collapsed"
                    )
                    passwords.append(per_file_password)
            
            st.markdown("---")
            
            # Alternative: Excel paste input
            with st.expander("📋 Atau paste password dari Excel", expanded=False):
                st.caption("Paste 1 password per baris dari Excel:")
                excel_input = st.text_area(
                    "Password dari Excel:",
                    height=150,
                    key="excel_password_input_alt"
                )
                
                if excel_input.strip():
                    passwords_from_excel = [p.strip() for p in excel_input.split('\n') if p.strip()]
                    
                    if len(passwords_from_excel) == len(uploads):
                        passwords = passwords_from_excel
                        st.success(f"✅ {len(passwords)} password berhasil dimuat")
                    else:
                        st.warning(f"⚠️ Jumlah password ({len(passwords_from_excel)}) ≠ jumlah file ({len(uploads)})")

        st.markdown("---")
        encrypt_clicked = st.button("🔒 Enkripsi File", type="primary", use_container_width=False)

        return EncryptViewResult(
            go_home=go_home,
            go_decrypt=go_decrypt,
            encrypt_clicked=encrypt_clicked,
            uploads=list(uploads),
            mode=mode,
            passwords=passwords,
        )
