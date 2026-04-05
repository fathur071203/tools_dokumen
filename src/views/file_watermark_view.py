from dataclasses import dataclass
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from src.services.watermark_service import WatermarkService


@dataclass
class WatermarkViewResult:
    go_home: bool
    preview_clicked: bool
    apply_clicked: bool
    pdf_upload: Any
    watermark_mode: str
    watermark_text: str
    watermark_template: str
    watermark_image: Any
    text_color: str
    use_bezel: bool
    position: str
    orientation: str
    opacity: float
    size_ratio: float


class FileWatermarkView:
    KEY_WATERMARK_MODE = "wm_mode"
    KEY_WATERMARK_TEXT = "wm_text"
    KEY_WATERMARK_TEMPLATE = "wm_template"
    KEY_WATERMARK_IMAGE_NONCE = "wm_image_nonce"
    KEY_WATERMARK_PREVIEW_PDF = "wm_preview_pdf"
    KEY_WATERMARK_PREVIEW_IMAGES = "wm_preview_images"
    KEY_WATERMARK_PREVIEW_SOURCE = "wm_preview_source"

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
            go_home = st.button("← Kembali", key="btn_home_watermark")
        with col_right:
            st.markdown(
                """
                <div class="td-page-intro-card">
                    <p class="td-feature-title">💧 Watermark PDF</p>
                    <p class="td-feature-desc">
                        Tambahkan watermark ke PDF menggunakan teks custom atau gambar PNG.
                        Atur posisi, orientasi lurus/miring, ukuran, dan transparansi.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return go_home

    def render(self) -> WatermarkViewResult:
        self._render_page_styles()
        go_home = self._render_page_header()

        with st.container(border=True):
            st.markdown("### Step 1 - Upload PDF")
            pdf_upload = st.file_uploader(
                "Upload file PDF",
                type=["pdf"],
                accept_multiple_files=False,
                help="Hanya 1 file PDF per proses agar hasil watermark lebih terkontrol.",
            )

        if pdf_upload is None:
            st.info("Belum ada file PDF. Upload file untuk mulai menambahkan watermark.")
            st.session_state.pop(self.KEY_WATERMARK_PREVIEW_PDF, None)
            st.session_state.pop(self.KEY_WATERMARK_PREVIEW_IMAGES, None)
            st.session_state.pop(self.KEY_WATERMARK_PREVIEW_SOURCE, None)
            return WatermarkViewResult(go_home, False, False, None, "text", "", "", None, "#B40000", True, "center", "straight", 0.32, 0.45)

        current_pdf_source = f"{getattr(pdf_upload, 'name', '')}:{int(getattr(pdf_upload, 'size', 0) or 0)}"
        previous_pdf_source = st.session_state.get(self.KEY_WATERMARK_PREVIEW_SOURCE)
        if previous_pdf_source and previous_pdf_source != current_pdf_source:
            st.session_state.pop(self.KEY_WATERMARK_PREVIEW_PDF, None)
            st.session_state.pop(self.KEY_WATERMARK_PREVIEW_IMAGES, None)

        if self.KEY_WATERMARK_MODE not in st.session_state:
            st.session_state[self.KEY_WATERMARK_MODE] = "text"
        if self.KEY_WATERMARK_IMAGE_NONCE not in st.session_state:
            st.session_state[self.KEY_WATERMARK_IMAGE_NONCE] = 0
        if self.KEY_WATERMARK_PREVIEW_IMAGES not in st.session_state:
            st.session_state[self.KEY_WATERMARK_PREVIEW_IMAGES] = []
        if self.KEY_WATERMARK_PREVIEW_PDF not in st.session_state:
            st.session_state[self.KEY_WATERMARK_PREVIEW_PDF] = b""
        if self.KEY_WATERMARK_PREVIEW_SOURCE not in st.session_state:
            st.session_state[self.KEY_WATERMARK_PREVIEW_SOURCE] = ""

        with st.container(border=True):
            st.markdown("### Step 2 - Watermark Setup")
            col_left, col_right = st.columns([1, 1.2], gap="large")

            with col_left:
                st.markdown("#### ⚙️ Mode dan Input")

                previous_mode = st.session_state[self.KEY_WATERMARK_MODE]
                watermark_mode = st.radio(
                    "Pilih tipe watermark",
                    options=["text", "template", "image"],
                    format_func=lambda value: {
                        "text": "Teks Custom",
                        "template": "Template Bawaan",
                        "image": "Gambar PNG",
                    }[value],
                    horizontal=True,
                    key=self.KEY_WATERMARK_MODE,
                )

                if watermark_mode != previous_mode:
                    if watermark_mode != "text" and self.KEY_WATERMARK_TEXT in st.session_state:
                        del st.session_state[self.KEY_WATERMARK_TEXT]
                    if watermark_mode != "template" and self.KEY_WATERMARK_TEMPLATE in st.session_state:
                        del st.session_state[self.KEY_WATERMARK_TEMPLATE]
                    st.session_state[self.KEY_WATERMARK_IMAGE_NONCE] += 1
                    st.session_state.pop(self.KEY_WATERMARK_PREVIEW_IMAGES, None)

                watermark_text = ""
                watermark_template = ""
                watermark_image = None
                if watermark_mode == "text":
                    watermark_text = st.text_area(
                        "Isi watermark",
                        value="RAHASIA",
                        placeholder="Contoh: INTERNAL, DRAFT, Nama Instansi",
                        help="Bisa diisi nama unit, label dokumen, atau teks lain. Jika perlu, gunakan lebih dari satu baris.",
                        height=110,
                        key=self.KEY_WATERMARK_TEXT,
                    )
                elif watermark_mode == "template":
                    watermark_template = st.selectbox(
                        "Pilih preset watermark",
                        options=list(WatermarkService.TEMPLATE_OPTIONS.keys()),
                        help="Preset dipilih lewat dropdown. BPK/DAI otomatis 2 baris huruf kapital.",
                        key=self.KEY_WATERMARK_TEMPLATE,
                    )
                    st.code(WatermarkService.TEMPLATE_OPTIONS[watermark_template], language="text")
                else:
                    watermark_image = st.file_uploader(
                        "Upload gambar watermark PNG",
                        type=["png"],
                        accept_multiple_files=False,
                        help="Gunakan PNG transparan agar watermark terlihat lebih rapi.",
                        key=f"watermark_png_upload_{st.session_state[self.KEY_WATERMARK_IMAGE_NONCE]}",
                    )

            with col_right:
                st.markdown("#### 👁️ Preview")
                preview_pdf_bytes = st.session_state.get(self.KEY_WATERMARK_PREVIEW_PDF, b"") or b""
                preview_images = st.session_state.get(self.KEY_WATERMARK_PREVIEW_IMAGES, []) or []
                if preview_pdf_bytes:
                    import base64
                    pdf_b64 = base64.b64encode(preview_pdf_bytes).decode("utf-8")
                    components.html(
                        f"""
                        <div style="width:100%; height:700px; border:1px solid #dbe4f0; border-radius:12px; overflow:hidden; background:white;">
                            <iframe id="wm_pdf_preview" style="width:100%; height:100%; border:0; background:white;"></iframe>
                        </div>
                        <script>
                        (function() {{
                            const base64Pdf = "{pdf_b64}";
                            const binary = atob(base64Pdf);
                            const bytes = new Uint8Array(binary.length);
                            for (let i = 0; i < binary.length; i++) {{
                                bytes[i] = binary.charCodeAt(i);
                            }}
                            const blob = new Blob([bytes], {{ type: 'application/pdf' }});
                            const url = URL.createObjectURL(blob);
                            const iframe = document.getElementById('wm_pdf_preview');
                            iframe.src = url;
                        }})();
                        </script>
                        """,
                        height=700,
                    )
                    st.caption("Preview PDF ditampilkan sebagai dokumen asli lewat blob URL. Jika browser tetap membatasi, gambar halaman tetap tersedia di bawah.")
                    if preview_images:
                        with st.expander("Lihat preview halaman sebagai gambar", expanded=False):
                            if len(preview_images) > 1:
                                page_number = st.slider(
                                    "Halaman preview",
                                    min_value=1,
                                    max_value=len(preview_images),
                                    value=1,
                                    step=1,
                                    key="wm_preview_page",
                                )
                                st.image(preview_images[page_number - 1], caption=f"Preview halaman {page_number}", use_container_width=True)
                            else:
                                st.image(preview_images[0], caption="Preview halaman 1", use_container_width=True)
                elif preview_images:
                    if len(preview_images) > 1:
                        page_number = st.slider(
                            "Halaman preview",
                            min_value=1,
                            max_value=len(preview_images),
                            value=1,
                            step=1,
                            key="wm_preview_page",
                        )
                        st.image(preview_images[page_number - 1], caption=f"Preview halaman {page_number}", use_container_width=True)
                    else:
                        st.image(preview_images[0], caption="Preview halaman 1", use_container_width=True)
                    st.caption("Preview ditampilkan dari hasil proses terakhir. Klik tombol Preview untuk refresh.")
                else:
                    st.info("Preview belum tersedia. Atur watermark lalu klik tombol Preview di Step 4.")

        with st.container(border=True):
            st.markdown("### Step 3 - Advanced Setting (Optional)")
            with st.expander("⚙️ Advanced Settings", expanded=False):
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
                    text_color = st.color_picker(
                        "Warna watermark",
                        value="#B40000",
                        help="Dipakai untuk warna teks/template atau warna bezel jika watermark gambar memakai kotak.",
                    )
                    use_bezel = st.checkbox(
                        "Pakai bezel / kotak",
                        value=True,
                        help="Tambahkan kotak/bezel di sekitar watermark. Bisa dimatikan jika ingin watermark tanpa bingkai.",
                    )
                with col2:
                    opacity = st.slider("Transparansi", min_value=0.05, max_value=0.90, value=0.32, step=0.05)
                    size_ratio = st.slider("Ukuran watermark", min_value=0.15, max_value=0.90, value=0.45, step=0.05)

                st.markdown(
                    "\n".join(
                        [
                            "- Pilih **Tengah + Miring** untuk watermark seperti cap dokumen.",
                            "- Pilih **Kanan Atas/Bawah + Lurus** untuk watermark yang lebih formal.",
                            "- Preset **BPK** dan **DAI** otomatis dibuat 2 baris huruf kapital.",
                            "- Preset **PENYELENGGARA**, **ARSIP**, dan **PPATK** tersedia lewat dropdown.",
                            "- PNG transparan cocok untuk logo instansi atau stempel.",
                        ]
                    )
                )

        with st.container(border=True):
            st.markdown("### Step 4 - Action")
            col_preview, col_apply = st.columns(2)
            with col_preview:
                preview_clicked = st.button("👁️ Preview Watermark", use_container_width=True)
            with col_apply:
                apply_clicked = st.button("💧 Tambahkan Watermark", type="primary", use_container_width=True)

        return WatermarkViewResult(
            go_home=go_home,
            preview_clicked=preview_clicked,
            apply_clicked=apply_clicked,
            pdf_upload=pdf_upload,
            watermark_mode=watermark_mode,
            watermark_text=watermark_text,
            watermark_template=watermark_template,
            watermark_image=watermark_image,
            text_color=text_color,
            use_bezel=use_bezel,
            position=position,
            orientation=orientation,
            opacity=opacity,
            size_ratio=size_ratio,
        )