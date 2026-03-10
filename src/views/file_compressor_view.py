from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.services.compress_service import CompressService


@dataclass
class CompressViewResult:
    go_home: bool
    compress_clicked: bool
    uploads: list[Any]
    compression_level: int


class FileCompressorView:
    def render(self) -> CompressViewResult:
        # Header dengan spacing
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        col_a, col_b = st.columns([1, 8])
        with col_a:
            go_home = st.button("← Kembali", key="btn_home_compress")
        with col_b:
            st.markdown("## 📦 Kompresi File")
            st.markdown(
                "Kompres file dengan metode optimal. "
                "Khusus file PPTX/PDF tunggal, gambar di dalam akan di-resize/recompress "
                "lalu disimpan kembali agar ukuran turun signifikan."
            )

        st.markdown("---")

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
                compression_level=9,
            )

        st.markdown("---")

        # Display uploaded files
        st.markdown("### 📋 File yang akan dikompres")
        
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

        st.markdown("---")

        # Compression level selector
        col1, col2 = st.columns([1, 2])
        with col1:
            compression_level = st.slider(
                "Tingkat Kompresi",
                min_value=1,
                max_value=9,
                value=6,
                help="1 = Cepat, 6 = Balanced, 9 = Maksimal (lambat)"
            )
        with col2:
            compression_desc = {
                1: "🚀 Sangat Cepat - Kompresi minimal",
                6: "⚖️  Seimbang - Kecepatan & ukuran",
                9: "📦 Maksimal - Ukuran paling kecil (lambat)",
            }
            st.info(compression_desc.get(compression_level, f"Level {compression_level}"))

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            compress_clicked = st.button("📦 Proses File", type="primary", use_container_width=True, key="btn_compress")
        with col2:
            st.write("")  # Spacing

        return CompressViewResult(
            go_home=go_home,
            compress_clicked=compress_clicked,
            uploads=list(uploads),
            compression_level=compression_level,
        )
