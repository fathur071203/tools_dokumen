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
    output_labels: list[str]


class FileLockerEncryptView:
    @staticmethod
    def _default_alias(index: int) -> str:
        return f"file_anon_{index:03d}"

    @staticmethod
    def _render_card_styles() -> None:
        """Render connected full-card styles"""
        st.markdown(
            """
            <style>
            .locker-main-card {
                background: white;
                padding: 24px;
                border-radius: 18px;
                box-shadow: 0px 10px 30px rgba(0,0,0,0.12);
                margin: 16px 0 20px 0;
                border: 1px solid rgba(31, 78, 121, 0.08);
            }
            
            .section-title {
                font-weight: 700;
                font-size: 16px;
                color: #1f4e79;
                margin: 0 0 10px 0;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .section-subtitle {
                font-size: 0.88rem;
                color: #64748b;
                margin: 0 0 12px 0;
            }

            .section-divider {
                border-top: 1px solid #e2e8f0;
                margin: 18px 0;
            }

            /* File Locker page background: white dominant, subtle blue accent at bottom-right */
            .stApp {
                background-color: #ffffff !important;
                background-image:
                    radial-gradient(
                        circle at 10% 92%,
                        rgba(37, 99, 235, 0.13) 0%,
                        rgba(37, 99, 235, 0.07) 24%,
                        rgba(37, 99, 235, 0.00) 52%
                    ),
                    radial-gradient(
                        circle at 92% 88%,
                        rgba(37, 99, 235, 0.20) 0%,
                        rgba(37, 99, 235, 0.11) 24%,
                        rgba(37, 99, 235, 0.00) 56%
                    ) !important;
                background-repeat: no-repeat !important;
                background-attachment: fixed !important;
            }

            /* Native Streamlit container card - final stable style */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: #ffffff !important;
                border-radius: 18px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0px 12px 35px rgba(0, 0, 0, 0.18) !important;
                padding: 20px !important;
                margin-bottom: 20px !important;
                transition: transform 0.2s ease !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:hover {
                transform: translateY(-2px) !important;
            }
            
            .td-page-intro-card {
                background: linear-gradient(135deg, #f0f9ff 0%, #f0fdfa 100%);
                padding: 20px;
                border-radius: 16px;
                border-left: 4px solid #2bb3c0;
            }
            
            .td-feature-title {
                font-weight: 700;
                font-size: 20px;
                color: #1f4e79;
                margin: 0 0 8px 0;
            }
            
            .td-feature-desc {
                font-size: 0.9rem;
                color: #475569;
                margin: 0;
                line-height: 1.5;
            }
            
            /* ===== FORCE LIGHT THEME - DARK MODE OVERRIDE ===== */
            /* Global force light theme styling */
            html[data-theme="dark"],
            body[data-theme="dark"],
            html[data-theme="dark"] *,
            body[data-theme="dark"] * {
                background-color: transparent !important;
                color: #0f172a !important;
            }
            
            /* Force light background on main containers */
            html[data-theme="dark"] .stApp,
            body[data-theme="dark"] .stApp {
                background-color: #ffffff !important;
                background-image:
                    radial-gradient(
                        circle at 10% 92%,
                        rgba(37, 99, 235, 0.13) 0%,
                        rgba(37, 99, 235, 0.07) 24%,
                        rgba(37, 99, 235, 0.00) 52%
                    ),
                    radial-gradient(
                        circle at 92% 88%,
                        rgba(37, 99, 235, 0.20) 0%,
                        rgba(37, 99, 235, 0.11) 24%,
                        rgba(37, 99, 235, 0.00) 56%
                    ) !important;
                background-repeat: no-repeat !important;
                background-attachment: fixed !important;
                color: #0f172a !important;
            }
            
            /* Force white background on all major containers */
            html[data-theme="dark"] div[data-testid="stVerticalBlockBorderWrapper"],
            body[data-theme="dark"] div[data-testid="stVerticalBlockBorderWrapper"],
            html[data-theme="dark"] .stContainer,
            body[data-theme="dark"] .stContainer,
            html[data-theme="dark"] .stForm,
            body[data-theme="dark"] .stForm {
                background: #ffffff !important;
                color: #0f172a !important;
            }
            
            /* Force text color on all headings and text */
            html[data-theme="dark"] h1, html[data-theme="dark"] h2, html[data-theme="dark"] h3, html[data-theme="dark"] h4, html[data-theme="dark"] h5, html[data-theme="dark"] h6,
            body[data-theme="dark"] h1, body[data-theme="dark"] h2, body[data-theme="dark"] h3, body[data-theme="dark"] h4, body[data-theme="dark"] h5, body[data-theme="dark"] h6 {
                color: #0f172a !important;
            }
            
            html[data-theme="dark"] p, html[data-theme="dark"] label, html[data-theme="dark"] span, html[data-theme="dark"] div,
            body[data-theme="dark"] p, body[data-theme="dark"] label, body[data-theme="dark"] span, body[data-theme="dark"] div {
                color: #0f172a !important;
            }
            
            /* Input fields and buttons */
            html[data-theme="dark"] input, html[data-theme="dark"] textarea, html[data-theme="dark"] select,
            body[data-theme="dark"] input, body[data-theme="dark"] textarea, body[data-theme="dark"] select {
                background: #ffffff !important;
                color: #0f172a !important;
                border: 1px solid #e2e8f0 !important;
            }
            
            html[data-theme="dark"] button,
            body[data-theme="dark"] button {
                color: #ffffff !important;
            }
            
            /* Data tables and markdown */
            html[data-theme="dark"] .stDataFrame, html[data-theme="dark"] .stTable, html[data-theme="dark"] .stMarkdown,
            body[data-theme="dark"] .stDataFrame, body[data-theme="dark"] .stTable, body[data-theme="dark"] .stMarkdown {
                color: #0f172a !important;
            }
            
            /* Custom card styles */
            html[data-theme="dark"] .locker-main-card,
            body[data-theme="dark"] .locker-main-card {
                background: #ffffff !important;
                color: #0f172a !important;
            }
            
            html[data-theme="dark"] .section-title,
            body[data-theme="dark"] .section-title {
                color: #1f4e79 !important;
            }
            
            html[data-theme="dark"] .section-subtitle,
            body[data-theme="dark"] .section-subtitle {
                color: #64748b !important;
            }
            
            html[data-theme="dark"] .td-feature-title,
            body[data-theme="dark"] .td-feature-title {
                color: #1f4e79 !important;
            }
            
            html[data-theme="dark"] .td-feature-desc,
            body[data-theme="dark"] .td-feature-desc {
                color: #475569 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    @staticmethod
    def _render_page_header() -> tuple[bool, bool]:
        col_a, col_b, col_c = st.columns([1, 7, 2])
        with col_a:
            go_home = st.button("← Kembali", key="btn_home_encrypt")
        with col_b:
            st.markdown(
                """
                <div class="td-page-intro-card">
                    <p class="td-feature-title">🔐 File Locker</p>
                    <p class="td-feature-desc">
                        Enkripsi file dengan password. PDF tetap format .pdf, file non-PDF menjadi .encrypted,
                        dan nama output disamarkan. Word/Excel/PPT dibungkus ZIP sebelum dikunci.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_c:
            go_decrypt = st.button("🔓 Buka Halaman Dekripsi", use_container_width=True, key="btn_decrypt_nav")

        return go_home, go_decrypt

    def render(self) -> EncryptViewResult:
        # Apply card styles
        self._render_card_styles()

        go_home, go_decrypt = self._render_page_header()

        st.caption("Step 1: Upload → Step 2: Isi Password & Alias → Step 3: Enkripsi")

        col_left, col_right = st.columns([1, 1.25], gap="large")

        with col_left:
            with st.container(border=True):
                st.markdown("#### 📂 Upload File")
                st.caption("Upload satu atau lebih file untuk dienkripsi")
                uploads = st.file_uploader(
                    "Upload file (boleh banyak file)",
                    accept_multiple_files=True,
                    help="PDF tetap berekstensi .pdf, file lain menjadi .encrypted. File Office dibungkus ZIP sebelum enkripsi.",
                    type=None,
                    label_visibility="collapsed",
                )

            with st.container(border=True):
                st.markdown("#### 🔐 Mode Password")
                mode_label = st.radio(
                    "Mode Password",
                    options=["1 password untuk semua file", "Password berbeda per file"],
                    horizontal=False,
                    key="mode_password_radio",
                    label_visibility="collapsed",
                )

                mode = PasswordMode.SINGLE if mode_label.startswith("1 password") else PasswordMode.INDIVIDUAL
                if mode == PasswordMode.SINGLE:
                    st.caption("Satu password dipakai untuk semua file")
                    single_password = st.text_input(
                        "Password",
                        type="password",
                        key="single_encrypt_password",
                        label_visibility="collapsed",
                        placeholder="Masukkan password utama",
                    )
                else:
                    st.caption("Setiap file bisa memakai password berbeda")

        if not uploads:
            st.info("📥 Belum ada file. Upload dulu untuk mulai enkripsi.")
            return EncryptViewResult(
                go_home=go_home,
                go_decrypt=go_decrypt,
                encrypt_clicked=False,
                uploads=[],
                mode=PasswordMode.SINGLE,
                passwords=[],
                output_labels=[],
            )

        mode = PasswordMode.SINGLE if mode_label.startswith("1 password") else PasswordMode.INDIVIDUAL
        output_labels: list[str] = [self._default_alias(i) for i in range(1, len(uploads) + 1)]
        passwords: list[str] = []

        with col_right:
            if mode == PasswordMode.SINGLE:
                with st.container(border=True):
                    st.markdown("#### 📋 File dan Alias Output")
                    st.caption("Mode 1 password aktif: isi alias output per file. Password mengikuti Password Utama.")

                    h1, h2, h3 = st.columns([0.55, 2.6, 1.8])
                    with h1:
                        st.markdown("**No**")
                    with h2:
                        st.markdown("**Nama Asli**")
                    with h3:
                        st.markdown("**Alias Output**")

                    st.markdown("---")

                    for idx, upload in enumerate(uploads, start=1):
                        c1, c2, c3 = st.columns([0.55, 2.6, 1.8])
                        with c1:
                            st.write(idx)
                        with c2:
                            st.write(upload.name)
                        with c3:
                            alias_value = st.text_input(
                                f"Alias {idx}",
                                value=self._default_alias(idx),
                                key=f"alias_inline_single_{idx}_{upload.name}",
                                label_visibility="collapsed",
                            ).strip()
                            output_labels[idx - 1] = alias_value or self._default_alias(idx)

                    passwords = [single_password] * len(uploads)

                    with st.expander("⚙️ Advanced: Import Alias dari Excel", expanded=False):
                        st.caption("Isi 1 baris alias output per file.")
                        alias_excel_input = st.text_area(
                            "Alias Output dari Excel",
                            height=140,
                            key="excel_alias_input_alt_single",
                            label_visibility="collapsed",
                            placeholder="file_anon_001\nfile_anon_002\n...",
                        )

                        alias_lines = [line.strip() for line in alias_excel_input.split("\n") if line.strip()]
                        if alias_lines:
                            if len(alias_lines) == len(uploads):
                                output_labels = [
                                    alias_lines[i] if alias_lines[i] else self._default_alias(i + 1)
                                    for i in range(len(uploads))
                                ]
                                st.success(f"✅ {len(alias_lines)} alias output berhasil dimuat")
                            else:
                                st.warning(f"⚠️ Jumlah alias ({len(alias_lines)}) ≠ jumlah file ({len(uploads)})")
            else:
                with st.container(border=True):
                    st.markdown("#### 📋 File, Alias Output, dan Password")
                    st.caption("Isi alias output dan password langsung per baris file")

                    h1, h2, h3, h4 = st.columns([0.55, 2.2, 1.6, 1.6])
                    with h1:
                        st.markdown("**No**")
                    with h2:
                        st.markdown("**Nama Asli**")
                    with h3:
                        st.markdown("**Alias Output**")
                    with h4:
                        st.markdown("**Password**")

                    st.markdown("---")

                    for idx, upload in enumerate(uploads, start=1):
                        c1, c2, c3, c4 = st.columns([0.55, 2.2, 1.6, 1.6])
                        with c1:
                            st.write(idx)
                        with c2:
                            st.write(upload.name)
                        with c3:
                            alias_value = st.text_input(
                                f"Alias {idx}",
                                value=self._default_alias(idx),
                                key=f"alias_inline_{idx}_{upload.name}",
                                label_visibility="collapsed",
                            ).strip()
                            output_labels[idx - 1] = alias_value or self._default_alias(idx)
                        with c4:
                            pwd_value = st.text_input(
                                f"Password {idx}",
                                type="password",
                                key=f"per_file_pwd_{idx}_{upload.name}",
                                label_visibility="collapsed",
                            )
                            passwords.append(pwd_value)

                    with st.expander("⚙️ Advanced: Import dari Excel", expanded=False):
                        st.caption("Isi 1 baris per file. Alias Output dan Password dipisah dalam 2 kolom.")

                        adv_col_alias, adv_col_password = st.columns(2)
                        with adv_col_alias:
                            st.markdown("**Alias Output (opsional)**")
                            alias_excel_input = st.text_area(
                                "Alias Output dari Excel",
                                height=140,
                                key="excel_alias_input_alt",
                                label_visibility="collapsed",
                                placeholder="file_anon_001\nfile_anon_002\n...",
                            )

                        with adv_col_password:
                            st.markdown("**Password**")
                            password_excel_input = st.text_area(
                                "Password dari Excel",
                                height=140,
                                key="excel_password_input_alt",
                                label_visibility="collapsed",
                                placeholder="password1\npassword2\n...",
                            )

                        alias_lines = [line.strip() for line in alias_excel_input.split("\n") if line.strip()]
                        password_lines = [line.strip() for line in password_excel_input.split("\n") if line.strip()]

                        if alias_lines or password_lines:
                            if alias_lines:
                                if len(alias_lines) == len(uploads):
                                    output_labels = [
                                        alias_lines[i] if alias_lines[i] else self._default_alias(i + 1)
                                        for i in range(len(uploads))
                                    ]
                                    st.success(f"✅ {len(alias_lines)} alias output berhasil dimuat")
                                else:
                                    st.warning(f"⚠️ Jumlah alias ({len(alias_lines)}) ≠ jumlah file ({len(uploads)})")

                            if password_lines:
                                if len(password_lines) == len(uploads):
                                    passwords = password_lines
                                    st.success(f"✅ {len(password_lines)} password berhasil dimuat")
                                else:
                                    st.warning(f"⚠️ Jumlah password ({len(password_lines)}) ≠ jumlah file ({len(uploads)})")

        st.markdown("---")

        action_col_left, action_col_mid, action_col_right = st.columns([1, 1.4, 1])
        with action_col_mid:
            encrypt_clicked = st.button(
                "🔒 Enkripsi File",
                type="primary",
                use_container_width=True,
                key="btn_encrypt",
            )

        pdf_count = sum(1 for upload in uploads if upload.name.lower().endswith(".pdf"))
        office_count = sum(
            1
            for upload in uploads
            if upload.name.lower().endswith((".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"))
        )

        with st.container(border=True):
            info_chunks: list[str] = []
            if pdf_count:
                info_chunks.append(f"📄 PDF: {pdf_count} file tetap berekstensi .pdf")
            if office_count:
                info_chunks.append(f"📦 Office: {office_count} file dibungkus ZIP sebelum enkripsi")
            info_chunks.append("🔒 Output memakai Alias Output yang Anda isi")
            st.caption(" | ".join(info_chunks))

        return EncryptViewResult(
            go_home=go_home,
            go_decrypt=go_decrypt,
            encrypt_clicked=encrypt_clicked,
            uploads=list(uploads),
            mode=mode,
            passwords=passwords,
            output_labels=output_labels,
        )
