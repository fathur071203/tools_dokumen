from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.services.ltdbb_cleaner_service import LTDBBCleanerService


@dataclass
class CleanerViewResult:
    go_home: bool
    process_clicked: bool
    upload: Any | None
    variant_override: str | None


class FileCleanerView:
    def render(self) -> CleanerViewResult:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        col_a, col_b = st.columns([1, 8])
        with col_a:
            go_home = st.button("← Kembali", key="btn_home_cleaner")
        with col_b:
            st.markdown("## 🧹 Cleaner Data LTDBB LKPBU")
            st.markdown(
                "Bersihkan file LTDBB dari template CSV/XLS/XLSX: buang baris awal, hilangkan kolom A/B, "
                "rapikan header, dan siapkan CSV bersih plus ringkasan analitik."
            )

        st.markdown("---")
        upload = st.file_uploader(
            "Upload file LTDBB",
            type=["csv", "xls", "xlsx"],
            accept_multiple_files=False,
            help="Format yang didukung: CSV, XLS, XLSX.",
        )

        variant_override = st.selectbox(
            "Jenis laporan (override opsional)",
            options=list(LTDBBCleanerService.VARIANT_OPTIONS.keys()),
            format_func=lambda value: LTDBBCleanerService.VARIANT_OPTIONS[value],
        )

        with st.expander("Tips", expanded=False):
            st.markdown(
                "\n".join(
                    [
                        "- Upload file mentah LTDBB langsung dari sistem sumber.",
                        "- Cleaner akan memakai baris ke-6 sebagai header dan membuang kolom A/B.",
                        "- Override jenis hanya dipakai bila auto-detect tidak pas.",
                    ]
                )
            )

        st.markdown("---")
        process_clicked = st.button("🧹 Proses & Buat CSV Bersih", type="primary", use_container_width=True)

        return CleanerViewResult(
            go_home=go_home,
            process_clicked=process_clicked,
            upload=upload,
            variant_override=variant_override or None,
        )