from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.services.compress_service import CompressService


@dataclass
class CompressViewResult:
    go_home: bool
    compress_clicked: bool
    uploads: list[Any]
    compression_mode: str
    pdf_method: str


class FileCompressorView:
    @staticmethod
    def _render_page_styles() -> None:
        st.markdown(
            """
            <style>
            .stApp {
                background-color: #ffffff !important;
                background-image:
                    radial-gradient(circle at 10% 92%, rgba(37, 99, 235, 0.13) 0%, rgba(37, 99, 235, 0.07) 24%, rgba(37, 99, 235, 0.00) 52%),
                    radial-gradient(circle at 92% 88%, rgba(37, 99, 235, 0.20) 0%, rgba(37, 99, 235, 0.11) 24%, rgba(37, 99, 235, 0.00) 56%) !important;
                background-repeat: no-repeat !important;
                background-attachment: fixed !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: #ffffff !important;
                border-radius: 18px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0px 12px 35px rgba(0, 0, 0, 0.18) !important;
                padding: 20px !important;
                margin-bottom: 20px !important;
            }

            /* Perbesar komponen input di halaman kompresi */
            div[data-testid="stFileUploaderDropzone"] {
                min-height: 170px !important;
                padding: 20px 18px !important;
                border-radius: 14px !important;
            }

            div[data-testid="stFileUploaderDropzone"] * {
                font-size: 1rem !important;
            }

            div[data-testid="stRadio"] label {
                font-size: 1.02rem !important;
                font-weight: 600 !important;
            }

            div[data-testid="stRadio"] [role="radiogroup"] {
                gap: 0.9rem !important;
            }

            div[data-testid="stRadio"] [role="radio"] {
                padding: 0.45rem 0.65rem !important;
                border-radius: 10px !important;
            }

            div[data-testid="stButton"] button {
                min-height: 48px !important;
                font-size: 1.02rem !important;
                font-weight: 700 !important;
                border-radius: 12px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    @staticmethod
    def _render_page_header() -> bool:
        col_left, col_right = st.columns([1, 8])
        with col_left:
            go_home = st.button("← Kembali", key="btn_home_compress")
        with col_right:
            st.markdown(
                """
                <div class="td-page-intro-card">
                    <p class="td-feature-title">📦 Kompresi File</p>
                    <p class="td-feature-desc">
                        Kompres file dengan metode optimal. Khusus PPTX/PDF tunggal, gambar di dalam file bisa di-resize/recompress
                        agar ukuran turun signifikan.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return go_home

    def render(self) -> CompressViewResult:
        self._render_page_styles()
        go_home = self._render_page_header()

        with st.container(border=True):
            st.markdown("#### 📂 Upload File")
            uploads = st.file_uploader(
                "Upload file yang ingin dikompres (boleh banyak file)",
                accept_multiple_files=True,
                help="Semua tipe file didukung.",
                type=None,
            )

        if not uploads:
            st.info("Belum ada file. Upload dulu untuk mulai kompresi.")
            return CompressViewResult(
                go_home=go_home,
                compress_clicked=False,
                uploads=[],
                compression_mode=CompressService.MODE_BALANCED,
                pdf_method=CompressService.PDF_METHOD_AUTO,
            )

        with st.container(border=True):
            st.markdown("#### 📋 File yang akan dikompres")

            file_data = []
            total_size = 0
            for i, upload in enumerate(uploads, start=1):
                size_bytes = upload.size
                total_size += size_bytes
                file_data.append({
                    "No": i,
                    "Nama File": upload.name,
                    "Ukuran": CompressService.format_size(size_bytes),
                })

            import pandas as pd

            df = pd.DataFrame(file_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total File", len(uploads))
            with col2:
                st.metric("Ukuran Total", CompressService.format_size(total_size))

        with st.container(border=True):
            compression_mode = st.radio(
                "Mode Kompresi",
                options=[
                    CompressService.MODE_SAFE,
                    CompressService.MODE_BALANCED,
                    CompressService.MODE_AGGRESSIVE,
                ],
                format_func=lambda value: {
                    CompressService.MODE_SAFE: "Aman (kualitas tetap)",
                    CompressService.MODE_BALANCED: "Seimbang (disarankan)",
                    CompressService.MODE_AGGRESSIVE: "Maksimal (ukuran kecil)",
                }[value],
                horizontal=True,
                index=1,
            )

            mode_desc = {
                CompressService.MODE_SAFE: "🟢 Aman — optimasi ringan tanpa resize agresif, cocok untuk poster/desain.",
                CompressService.MODE_BALANCED: "⚖️ Seimbang — kompresi terasa, visual tetap aman untuk sebagian besar file.",
                CompressService.MODE_AGGRESSIVE: "🔴 Maksimal — ukuran turun lebih banyak, perubahan visual bisa lebih terasa.",
            }
            st.info(mode_desc.get(compression_mode, "Mode kompresi dipilih"))

            single_pdf_upload = len(uploads) == 1 and str(getattr(uploads[0], "name", "")).lower().endswith(".pdf")
            if single_pdf_upload:
                st.markdown("---")
                st.markdown("#### ⚙️ Metode Kompresi PDF (Local)")

                ghostscript_ready = CompressService.is_ghostscript_available()
                if ghostscript_ready:
                    st.caption("Ghostscript terdeteksi di local environment.")
                    pdf_method_options = [
                        CompressService.PDF_METHOD_AUTO,
                        CompressService.PDF_METHOD_GHOSTSCRIPT,
                        CompressService.PDF_METHOD_PYMUPDF,
                    ]
                else:
                    st.warning(
                        "Ghostscript tidak terdeteksi. Opsi Ghostscript disembunyikan dan sistem akan memakai PyMuPDF.\n\n"
                        "Install Ghostscript dari: https://ghostscript.com/releases/\n"
                        "Setelah install, restart terminal/aplikasi. Jika perlu, set environment variable `GHOSTSCRIPT_PATH` "
                        "ke path executable `gswin64c.exe`."
                    )
                    pdf_method_options = [
                        CompressService.PDF_METHOD_AUTO,
                        CompressService.PDF_METHOD_PYMUPDF,
                    ]

                pdf_method = st.selectbox(
                    "Pilih engine kompresi PDF",
                    options=pdf_method_options,
                    format_func=lambda value: {
                        CompressService.PDF_METHOD_AUTO: "Auto (Ghostscript → fallback PyMuPDF)",
                        CompressService.PDF_METHOD_GHOSTSCRIPT: "Ghostscript (recommended, local)",
                        CompressService.PDF_METHOD_PYMUPDF: "PyMuPDF (internal fallback)",
                    }[value],
                    index=0,
                    help="Muncul untuk PDF tunggal agar jelas metode yang dipakai saat proses lokal.",
                )
            else:
                pdf_method = CompressService.PDF_METHOD_AUTO

            estimated_size, estimated_low, estimated_high = CompressService.estimate_compressed_size(
                uploads,
                compression_mode=compression_mode,
            )
            original_size = sum(upload.size for upload in uploads)
            savings_ratio = CompressService.get_compression_ratio(original_size, estimated_size)

            st.markdown("---")
            st.markdown("#### 🧮 Estimasi Hasil")
            est_col1, est_col2, est_col3 = st.columns(3)
            with est_col1:
                st.metric("Perkiraan Ukuran", CompressService.format_size(estimated_size))
            with est_col2:
                st.metric("Rentang Estimasi", f"{CompressService.format_size(estimated_low)} - {CompressService.format_size(estimated_high)}")
            with est_col3:
                st.metric("Perkiraan Penghematan", f"{savings_ratio:.1f}%")

            st.caption("Estimasi ini bersifat perkiraan sebelum proses. Ukuran final bisa sedikit berbeda tergantung isi file.")

        with st.container(border=True):
            compress_clicked = st.button("📦 Proses File", type="primary", use_container_width=True, key="btn_compress")

        return CompressViewResult(
            go_home=go_home,
            compress_clicked=compress_clicked,
            uploads=list(uploads),
            compression_mode=compression_mode,
            pdf_method=pdf_method,
        )
