from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.services.convert_service import ConvertService


@dataclass
class ConverterViewResult:
    go_home: bool
    convert_clicked: bool
    uploads: list[Any]
    target_format: str
    pdf_output_mode: str


class FileConverterView:
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
            </style>
            """,
            unsafe_allow_html=True,
        )

    @staticmethod
    def _render_page_header() -> bool:
        col_left, col_right = st.columns([1, 8])
        with col_left:
            go_home = st.button("← Kembali", key="btn_home_converter")
        with col_right:
            description = (
                "Konversi dokumen dua arah untuk skenario utama: PDF ke Word/PPT/Excel, "
                "dan Word/Excel/PPT/gambar ke PDF."
            )
            if not ConvertService.supports_office_to_pdf():
                description = (
                    "Konversi PDF ke Word/PPT/Excel dan gambar ke PDF tersedia di server ini. "
                    "Konversi Word/Excel/PPT ke PDF hanya aktif di Windows dengan Microsoft Office desktop."
                )
            st.markdown(
                f"""
                <div class="td-page-intro-card">
                    <p class="td-feature-title">🔄 Konversi Dokumen</p>
                    <p class="td-feature-desc">{description}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return go_home

    def render(self) -> ConverterViewResult:
        self._render_page_styles()
        go_home = self._render_page_header()

        with st.container(border=True):
            st.markdown("#### 📂 Upload File")
            uploads = st.file_uploader(
                "Upload file yang ingin dikonversi",
                accept_multiple_files=True,
                type=None,
                help="Contoh: PDF, DOCX, XLSX, PPTX, JPG, PNG",
            )

        if not uploads:
            st.info("Belum ada file. Upload satu atau beberapa file untuk mulai konversi.")
            return ConverterViewResult(
                go_home=go_home,
                convert_clicked=False,
                uploads=[],
                target_format="",
                pdf_output_mode="merge",
            )

        uploads = list(uploads)
        targets = ConvertService.get_available_targets_for_uploads(uploads)

        with st.container(border=True):
            st.markdown("#### 📋 Detail File")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Jumlah File", len(uploads))
            with col2:
                total_size_mb = sum(upload.size for upload in uploads) / 1024 / 1024
                st.metric("Total Ukuran", f"{total_size_mb:.2f} MB")

            if len(uploads) == 1:
                st.caption(f"File dipilih: {uploads[0].name}")
            else:
                with st.expander("Lihat daftar file", expanded=False):
                    for idx, upload in enumerate(uploads, start=1):
                        st.write(f"{idx}. {upload.name} — {upload.size / 1024 / 1024:.2f} MB")

        if not targets:
            st.error(
                "Kombinasi file ini belum didukung. Untuk multi-file, saat ini semua file harus bisa dikonversi ke PDF."
            )
            return ConverterViewResult(
                go_home=go_home,
                convert_clicked=False,
                uploads=uploads,
                target_format="",
                pdf_output_mode="merge",
            )

        with st.container(border=True):
            target_format = st.selectbox(
                "Pilih format output",
                options=targets,
                format_func=lambda value: value.upper(),
            )

            pdf_output_mode = "merge"
            if len(uploads) > 1 and target_format == "pdf":
                pdf_output_mode = st.radio(
                    "Mode hasil PDF",
                    options=["merge", "separate"],
                    format_func=lambda value: (
                        "Gabungkan semua menjadi 1 PDF" if value == "merge" else "1 file = 1 PDF (download ZIP)"
                    ),
                    horizontal=True,
                )
                st.caption("Mode multi-file hanya tersedia untuk output PDF.")

            st.caption("Konversi yang tersedia tergantung jenis file sumber.")
            with st.expander("Lihat dukungan konversi", expanded=False):
                support_lines = [
                    "- PDF → DOCX",
                    "- PDF → PPTX",
                    "- PDF → XLSX (Excel)",
                    "- JPG/PNG/BMP/WEBP → PDF",
                    "- Multi-file → PDF gabungan atau ZIP berisi PDF per file",
                ]
                if ConvertService.supports_office_to_pdf():
                    support_lines[2:2] = [
                        "- DOC/DOCX → PDF",
                        "- XLS/XLSX → PDF",
                        "- PPT/PPTX → PDF",
                    ]
                else:
                    support_lines.append("- Word/Excel/PPT → PDF hanya tersedia di Windows + Microsoft Office desktop")
                st.markdown("\n".join(support_lines))

        with st.container(border=True):
            convert_clicked = st.button("🔄 Konversi Sekarang", type="primary", use_container_width=True, key="btn_convert")

        return ConverterViewResult(
            go_home=go_home,
            convert_clicked=convert_clicked,
            uploads=uploads,
            target_format=target_format,
            pdf_output_mode=pdf_output_mode,
        )
