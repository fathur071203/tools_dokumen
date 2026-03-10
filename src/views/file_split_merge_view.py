from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from src.services.split_merge_service import SplitMergeService


@dataclass
class SplitMergeViewResult:
    go_home: bool
    action_clicked: bool
    uploads: list[Any]
    mode: str
    pattern_text: str
    output_names: list[str]


class FileSplitMergeView:
    def render(self) -> SplitMergeViewResult:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        col_a, col_b = st.columns([1, 8])
        with col_a:
            go_home = st.button("← Kembali", key="btn_home_split_merge")
        with col_b:
            st.markdown("## 🪄 Split & Gabung Dokumen")
            st.markdown(
                "Pisahkan atau gabungkan PDF, Word, dan PowerPoint. "
                "Satu baris pola = satu file output."
            )

        st.markdown("---")

        uploads = st.file_uploader(
            "Upload dokumen",
            accept_multiple_files=True,
            type=None,
            help="PDF, DOC/DOCX, PPT/PPTX",
        )

        if not uploads:
            st.info("Belum ada file. Upload dokumen untuk mulai split atau merge.")
            return SplitMergeViewResult(False, False, [], "", "", [])

        modes = SplitMergeService.get_supported_modes(list(uploads))
        if not modes:
            st.error("Mode tidak tersedia. Untuk split upload 1 file; untuk merge upload beberapa file dengan tipe yang sama.")
            return SplitMergeViewResult(go_home, False, list(uploads), "", "", [])

        st.markdown("### 📋 File yang Dipilih")
        for idx, upload in enumerate(uploads, start=1):
            st.write(f"{idx}. {upload.name} — {upload.size / 1024 / 1024:.2f} MB")

        st.markdown("---")
        mode = st.radio(
            "Pilih aksi",
            options=modes,
            format_func=lambda value: "Pisahkan Dokumen" if value == "split" else "Gabungkan Dokumen",
            horizontal=True,
        )

        pattern_text = ""
        output_names: list[str] = []
        if mode == "split":
            family = SplitMergeService.get_family(uploads[0].name)
            unit_label = "halaman" if family in {"pdf", "word"} else "slide"
            total_units, _ = SplitMergeService.estimate_total_units(uploads[0])
            input_mode = st.radio(
                "Metode pola split",
                options=["generator", "manual"],
                format_func=lambda value: "Generator Range" if value == "generator" else "Input Manual",
                horizontal=True,
            )

            if input_mode == "generator":
                st.caption(
                    f"Atur range master dan range tambahan. Cocok untuk pola seperti 1,2 lalu 1,2,3 lalu 1,2,4."
                )
                col1, col2 = st.columns(2)
                with col1:
                    master_start = st.number_input(f"Master {unit_label} dari", min_value=1, value=1, step=1)
                    variable_start = st.number_input(f"Tambahan {unit_label} dari", min_value=1, value=3, step=1)
                    pages_per_output = st.number_input(
                        f"Jumlah {unit_label} tambahan per output",
                        min_value=1,
                        value=1,
                        step=1,
                    )
                with col2:
                    master_end = st.number_input(f"Master {unit_label} sampai", min_value=1, value=2, step=1)
                    variable_end = st.number_input(f"Tambahan {unit_label} sampai", min_value=1, value=6, step=1)
                    step = st.number_input("Step perpindahan", min_value=1, value=1, step=1)

                try:
                    generated_groups = SplitMergeService.build_generated_groups(
                        int(master_start),
                        int(master_end),
                        int(variable_start),
                        int(variable_end),
                        int(pages_per_output),
                        int(step),
                    )
                    pattern_text = SplitMergeService.groups_to_text(generated_groups)
                    st.success(f"✅ {len(generated_groups)} output akan dibuat")
                    st.text_area(
                        f"Preview pola {unit_label}",
                        value=pattern_text,
                        height=170,
                        disabled=True,
                    )
                except ValueError as exc:
                    st.warning(str(exc))
                    pattern_text = ""
            else:
                st.caption(
                    f"Masukkan pola {unit_label}. Satu baris = satu file output. "
                    f"Contoh: 1,2 lalu 1,2,3 lalu 1,2,4"
                )
                pattern_text = st.text_area(
                    f"Pola {unit_label}",
                    height=170,
                    placeholder="1,2\n1,2,3\n1,2,4\n1,2,5",
                    help="Bisa juga pakai range seperti 1-3,5",
                )

            with st.expander("Contoh pola", expanded=False):
                st.code("1,2\n1,2,3\n1,2,4\n1,2,5", language="text")
                st.info(
                    f"Contoh generator: master 1-2, tambahan 3-6, per output 1, step 1 → 1,2,3 | 1,2,4 | 1,2,5 | 1,2,6"
                )
                if family == "word":
                    st.info("Split Word menghasilkan PDF per pola halaman untuk menjaga layout tetap rapi.")

            if pattern_text.strip():
                try:
                    groups = SplitMergeService.parse_groups(pattern_text)
                    preview_rows = SplitMergeService.build_output_preview(groups)
                    st.markdown("---")
                    st.markdown("### 📊 Estimasi Hasil Split")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"Total {unit_label.title()} Sumber", total_units)
                    with col2:
                        st.metric("Total File Output", len(groups))
                    with col3:
                        avg_units = round(sum(len(group) for group in groups) / len(groups), 2)
                        st.metric(f"Rata-rata {unit_label}/Output", avg_units)

                    st.caption(
                        f"Di bawah ini terlihat estimasi tiap output: isi {unit_label} apa saja, jumlah {unit_label}, dan nama file output yang bisa Anda ubah."
                    )
                    preview_df = pd.DataFrame(preview_rows)
                    edited_df = st.data_editor(
                        preview_df,
                        use_container_width=True,
                        hide_index=True,
                        disabled=["No", "Isi Halaman", "Jumlah Halaman"],
                        column_config={
                            "No": st.column_config.NumberColumn("No", width="small"),
                            "Isi Halaman": st.column_config.TextColumn(f"Isi {unit_label.title()}"),
                            "Jumlah Halaman": st.column_config.NumberColumn(f"Jumlah {unit_label.title()}", width="small"),
                            "Nama Output": st.column_config.TextColumn("Nama Output", help="Nama file tanpa harus menulis ekstensi juga boleh"),
                        },
                        key="split_preview_editor",
                    )
                    output_names = edited_df["Nama Output"].fillna("").astype(str).tolist()
                except Exception as exc:
                    st.warning(f"Estimasi belum bisa dibuat: {exc}")

        st.markdown("---")
        action_label = "🪄 Proses Split" if mode == "split" else "🧩 Gabungkan File"
        action_clicked = st.button(action_label, type="primary", use_container_width=True)

        return SplitMergeViewResult(
            go_home=go_home,
            action_clicked=action_clicked,
            uploads=list(uploads),
            mode=mode,
            pattern_text=pattern_text,
            output_names=output_names,
        )
