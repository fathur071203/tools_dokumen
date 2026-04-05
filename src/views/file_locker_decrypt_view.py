from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass
class DecryptViewResult:
    go_back: bool
    decrypt_clicked: bool
    encrypted_file: Any | None
    password: str


class FileLockerDecryptView:
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

    def render(self) -> DecryptViewResult:
        # Apply card styles
        self._render_card_styles()

        col_a, col_b = st.columns([1, 8])
        with col_a:
            go_back = st.button("← Kembali", key="btn_back_decrypt")
        with col_b:
            st.markdown(
                """
                <div class="td-page-intro-card">
                    <p class="td-feature-title">🔓 Dekripsi File</p>
                    <p class="td-feature-desc">
                        Buka file .encrypted dari File Locker atau lepas password dari PDF yang diproteksi.
                        Khusus file Office yang dikunci, hasil dekripsi berupa arsip ZIP.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 📂 Upload Card (native Streamlit)
        with st.container(border=True):
            st.markdown("#### 📂 Upload File Terenkripsi")
            st.caption("Upload file .encrypted atau PDF yang diproteksi password")
            encrypted_file = st.file_uploader(
                "Upload file terenkripsi",
                accept_multiple_files=False,
                type=None,
                help="Bisa file .encrypted atau file PDF yang diproteksi password.",
                label_visibility="collapsed",
            )

        if encrypted_file:
            # 📄 File Info Card
            with st.container(border=True):
                st.markdown("#### 📄 Informasi File")
                file_info_col1, file_info_col2 = st.columns(2)

                with file_info_col1:
                    st.metric("Nama File", encrypted_file.name)

                with file_info_col2:
                    size_mb = encrypted_file.size / (1024 * 1024)
                    st.metric("Ukuran", f"{size_mb:.2f} MB")

                if not (
                    encrypted_file.name.endswith(".encrypted") or encrypted_file.name.lower().endswith(".pdf")
                ):
                    st.warning("⚠️ File bukan .encrypted atau .pdf. Tetap dicoba selama format internal valid.")
                else:
                    st.success("✅ Format file valid")

        # 🔐 Password Card
        with st.container(border=True):
            st.markdown("#### 🔐 Password")
            st.caption("Gunakan password yang dipakai saat proses enkripsi")
            password = st.text_input(
                "Password dekripsi",
                type="password",
                label_visibility="collapsed",
                placeholder="Masukkan password dekripsi",
            )

        # 🚀 Action Card
        with st.container(border=True):
            st.markdown("#### 🚀 Action")
            decrypt_clicked = st.button("🔓 Dekripsi", type="primary", use_container_width=True, key="btn_decrypt")

        return DecryptViewResult(
            go_back=go_back,
            decrypt_clicked=decrypt_clicked,
            encrypted_file=encrypted_file,
            password=password,
        )
