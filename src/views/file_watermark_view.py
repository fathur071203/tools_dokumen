from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.services.watermark_service import WatermarkService


@dataclass
class WatermarkViewResult:
    go_home: bool
    apply_clicked: bool
    pdf_upload: Any
    watermark_mode: str
    watermark_text: str
    watermark_image: Any
    position: str
    orientation: str
    opacity: float
    size_ratio: float


class FileWatermarkView:
    def render(self) -> WatermarkViewResult:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        col_a, col_b = st.columns([1, 8])
        with col_a:
            go_home = st.button("← Kembali", key="btn_home_watermark")
        with col_b:
            st.markdown("## 💧 Watermark PDF")
            st.markdown(
                "Tambahkan watermark ke PDF menggunakan teks custom atau gambar PNG. "
                "Atur posisi, orientasi lurus/miring, ukuran, dan transparansi."
            )

        st.markdown("---")

        pdf_upload = st.file_uploader(
            "Upload file PDF",
            type=["pdf"],
            accept_multiple_files=False,
            help="Hanya 1 file PDF per proses agar hasil watermark lebih terkontrol.",
        )

        if pdf_upload is None:
            st.info("Belum ada file PDF. Upload file untuk mulai menambahkan watermark.")
            return WatermarkViewResult(False, False, None, "text", "", None, "center", "straight", 0.32, 0.45)

        st.markdown("### ⚙️ Jenis Watermark")
        watermark_mode = st.radio(
            "Pilih tipe watermark",
            options=["text", "image"],
            format_func=lambda value: "Teks Custom" if value == "text" else "Gambar PNG",
            horizontal=True,
        )

        watermark_text = ""
        watermark_image = None
        if watermark_mode == "text":
            watermark_text = st.text_input(
                "Isi watermark",
                value="RAHASIA",
                placeholder="Contoh: INTERNAL, DRAFT, Nama Instansi",
                help="Bisa diisi nama unit, label dokumen, atau teks lain.",
            )
        else:
            watermark_image = st.file_uploader(
                "Upload gambar watermark PNG",
                type=["png"],
                accept_multiple_files=False,
                help="Gunakan PNG transparan agar watermark terlihat lebih rapi.",
                key="watermark_png_upload",
            )

        st.markdown("---")
        st.markdown("### 🎛️ Pengaturan Watermark")

        col1, col2 = st.columns(2)
        with col1:
            position = st.selectbox(
                "Posisi watermark",
                options=list(WatermarkService.POSITION_OPTIONS.keys()),
                format_func=lambda value: WatermarkService.POSITION_OPTIONS[value],
            )
            orientation = st.radio(
                "Orientasi",
                options=list(WatermarkService.ORIENTATION_OPTIONS.keys()),
                format_func=lambda value: WatermarkService.ORIENTATION_OPTIONS[value],
                horizontal=True,
            )
        with col2:
            opacity = st.slider("Transparansi", min_value=0.05, max_value=0.90, value=0.32, step=0.05)
            size_ratio = st.slider("Ukuran watermark", min_value=0.15, max_value=0.80, value=0.45, step=0.05)

        with st.expander("Tips penggunaan", expanded=False):
            st.markdown(
                "\n".join(
                    [
                        "- Pilih **Tengah + Miring** untuk watermark seperti cap dokumen.",
                        "- Pilih **Kanan Atas/Bawah + Lurus** untuk watermark yang lebih formal.",
                        "- PNG transparan cocok untuk logo instansi atau stempel.",
                    ]
                )
            )

        st.markdown("---")
        apply_clicked = st.button("💧 Tambahkan Watermark", type="primary", use_container_width=True)

        return WatermarkViewResult(
            go_home=go_home,
            apply_clicked=apply_clicked,
            pdf_upload=pdf_upload,
            watermark_mode=watermark_mode,
            watermark_text=watermark_text,
            watermark_image=watermark_image,
            position=position,
            orientation=orientation,
            opacity=opacity,
            size_ratio=size_ratio,
        )