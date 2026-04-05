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
    merge_page_rules: list[str]


class FileSplitMergeView:
    @staticmethod
    def _render_split_output_preview(upload: Any, groups: list[list[int]]) -> None:
        if not groups:
            st.info("Preview output split akan muncul setelah pola berhasil dibuat.")
            return

        family = SplitMergeService.get_family(upload.name)
        if family != "pdf":
            st.info(
                "Preview output per halaman saat ini tersedia untuk PDF. "
                "Untuk Word/PPT, hasil split tetap bisa diproses dan diunduh."
            )
            return

        max_show = st.number_input(
            "Tampilkan output sampai",
            min_value=1,
            max_value=len(groups),
            value=min(5, len(groups)),
            step=1,
            help="Batasi jumlah output yang ditampilkan agar preview tetap ringan.",
        )

        visible_groups = groups[: int(max_show)]
        selected_output = st.selectbox(
            "Pilih output untuk dipreview",
            options=list(range(1, len(visible_groups) + 1)),
            format_func=lambda idx: f"Output {idx} ({len(visible_groups[idx - 1])} halaman)",
        )

        selected_group = visible_groups[selected_output - 1]
        st.caption(f"Komposisi output {selected_output}: {', '.join(str(page) for page in selected_group)}")

        rendered_pages = SplitMergeService.build_pdf_split_output_preview_images(upload, selected_group)
        if not rendered_pages:
            st.warning("Preview output belum bisa ditampilkan untuk pola ini.")
            return

        if len(rendered_pages) > 1:
            page_idx = st.slider(
                "Lihat halaman ke (di dalam output terpilih)",
                min_value=1,
                max_value=len(rendered_pages),
                value=1,
                step=1,
                key=f"split_output_preview_page_{getattr(upload, 'name', 'pdf')}_{selected_output}",
            )
            source_page, image_bytes = rendered_pages[page_idx - 1]
            st.image(
                image_bytes,
                caption=f"Output {selected_output} • halaman urutan {page_idx} (sumber halaman {source_page})",
                use_container_width=True,
            )
        else:
            source_page, image_bytes = rendered_pages[0]
            st.image(
                image_bytes,
                caption=f"Output {selected_output} • sumber halaman {source_page}",
                use_container_width=True,
            )

        st.caption("Preview menampilkan output split (bukan dokumen input), per halaman, secara realtime mengikuti perubahan pola.")

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
            go_home = st.button("← Kembali", key="btn_home_split_merge")
        with col_right:
            description = "Pisahkan atau gabungkan PDF, Word, dan PowerPoint. Satu baris pola = satu file output."
            if not SplitMergeService.supports_office_automation():
                description = (
                    "Di server ini, split/gabung PDF tersedia penuh. "
                    "Split/gabung Word dan PowerPoint hanya aktif di Windows dengan Microsoft Office desktop."
                )
            st.markdown(
                f"""
                <div class="td-page-intro-card">
                    <p class="td-feature-title">🪄 Split &amp; Gabung Dokumen</p>
                    <p class="td-feature-desc">{description}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return go_home

    def render(self) -> SplitMergeViewResult:
        self._render_page_styles()
        go_home = self._render_page_header()

        with st.container(border=True):
            st.markdown("#### Step 1 - 📂 Upload Dokumen")
            uploads = st.file_uploader(
                "Upload dokumen",
                accept_multiple_files=True,
                type=None,
                help="PDF selalu didukung; DOC/DOCX dan PPT/PPTX hanya aktif penuh di Windows + Microsoft Office desktop",
            )

        if not uploads:
            st.info("Belum ada file. Upload dokumen untuk mulai split atau merge.")
            return SplitMergeViewResult(False, False, [], "", "", [], [])

        modes = SplitMergeService.get_supported_modes(list(uploads))
        if not modes:
            st.error(
                "Mode tidak tersedia. Untuk split upload 1 file; untuk merge upload beberapa file dengan tipe yang sama. "
                "Di Linux deploy, Word/PPT tidak didukung untuk fitur ini."
            )
            return SplitMergeViewResult(go_home, False, list(uploads), "", "", [], [])

        with st.container(border=True):
            st.markdown("#### Step 2 - 🧭 Pilih Flow")
            st.caption("Split dan Merge dipisah agar alur kerja lebih fokus dan tidak membebani pengguna.")
            for idx, upload in enumerate(uploads, start=1):
                st.write(f"{idx}. {upload.name} — {upload.size / 1024 / 1024:.2f} MB")

            mode = st.radio(
                "Toggle Mode",
                options=modes,
                format_func=lambda value: "Split" if value == "split" else "Merge",
                horizontal=True,
            )

        pattern_text = ""
        output_names: list[str] = []
        merge_page_rules: list[str] = []
        groups_for_preview: list[list[int]] = []
        valid_rules = True

        if mode == "split":
            family = SplitMergeService.get_family(uploads[0].name)
            unit_label = "halaman" if family in {"pdf", "word"} else "slide"
            total_units, _ = SplitMergeService.estimate_total_units(uploads[0])
            with st.container(border=True):
                st.markdown("#### Step 3 - 🧩 Pilih Cara Split")
                split_method = st.radio(
                    "Pilih cara",
                    options=["simple", "advanced"],
                    format_func=lambda value: "Simple Split" if value == "simple" else "Advanced / Generator",
                    horizontal=True,
                )

            col_setup, col_preview = st.columns([1, 1.2], gap="large")

            with col_setup:
                st.markdown("#### Input")
                if split_method == "simple":
                    st.caption(
                        f"Masukkan pola {unit_label}. Satu baris = satu output."
                    )
                    pattern_text = st.text_area(
                        f"Pola {unit_label}",
                        height=170,
                        placeholder="1,2\n1,2,3\n1,2,4\n1,2,5",
                        help="Bisa juga pakai range seperti 1-3,5",
                    )
                else:
                    st.caption("Generator disimpan di panel Advanced agar tampilan awal tetap ringan.")
                    with st.expander("Advanced / Generator", expanded=False):
                        with st.expander("Panduan Generator", expanded=False):
                            st.markdown(
                                "\n".join(
                                    [
                                        "- **Master** selalu ikut di setiap output.",
                                        "- **Tambahan** digeser sesuai step untuk membentuk output berikutnya.",
                                        "- Gunakan mode ini untuk pola berulang yang panjang.",
                                    ]
                                )
                            )

                        col1, col2 = st.columns(2)
                        with col1:
                            master_start = st.number_input(f"Master {unit_label} dari", min_value=1, value=1, step=1)
                            variable_start = st.number_input(f"Tambahan {unit_label} dari", min_value=1, value=3, step=1)
                            pages_per_output = st.number_input(
                                f"Jumlah {unit_label} tambahan/output",
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
                            st.success(f"{len(generated_groups)} output terbuat dari generator")
                            st.text_area(
                                f"Preview pola {unit_label}",
                                value=pattern_text,
                                height=170,
                                disabled=True,
                            )
                        except ValueError as exc:
                            st.warning(str(exc))
                            pattern_text = ""

                with st.expander("Contoh pola", expanded=False):
                    st.code("1,2\n1,2,3\n1,2,4\n1,2,5", language="text")
                    st.info("Contoh generator: master 1-2, tambahan 3-6, per output 1, step 1")
                    if family == "word":
                        st.info("Split Word menghasilkan PDF per pola halaman untuk menjaga layout tetap rapi.")

            with col_preview:
                st.markdown("#### Preview")
                st.caption("Preview realtime")
                if pattern_text.strip():
                    try:
                        groups_for_preview = SplitMergeService.parse_groups(pattern_text)
                    except Exception as exc:
                        st.warning(f"Pola belum valid: {exc}")
                self._render_split_output_preview(uploads[0], groups_for_preview)

            with st.container(border=True):
                st.markdown("#### Step 4 - 📊 Estimasi & Aksi")
                if groups_for_preview:
                    preview_rows = SplitMergeService.build_output_preview(groups_for_preview, output_names)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"Total {unit_label.title()} Sumber", total_units)
                    with col2:
                        st.metric("Total File Output", len(groups_for_preview))
                    with col3:
                        avg_units = round(sum(len(group) for group in groups_for_preview) / len(groups_for_preview), 2)
                        st.metric(f"Rata-rata {unit_label}/Output", avg_units)

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
                            "Nama Output": st.column_config.TextColumn("Nama Output", help="Nama file boleh tanpa ekstensi"),
                        },
                        key="split_preview_editor",
                    )
                    output_names = edited_df["Nama Output"].fillna("").astype(str).tolist()
                else:
                    st.info("Isi pola split terlebih dulu agar estimasi dan nama output muncul.")
        else:
            family = SplitMergeService.get_family(uploads[0].name)
            summary_rows: list[dict[str, str | int]] = []

            col_left, col_right = st.columns([1, 1.2], gap="large")

            with col_left:
                with st.container(border=True):
                    st.markdown("#### Step 3 - 🧱 Pilih Halaman per File")
                    st.caption("Gunakan all atau format 1,2,5-8")

                    if family != "pdf":
                        st.info("Seleksi halaman merge saat ini tersedia untuk PDF. Word/PPT akan mengambil semua halaman/slide.")
                    else:
                        rule_cols = st.columns(2)
                        for index, upload in enumerate(uploads, start=1):
                            with rule_cols[(index - 1) % 2]:
                                total_pages, _ = SplitMergeService.estimate_total_units(upload)
                                st.markdown(f"**File {index}**")
                                st.caption(f"{upload.name} • {total_pages} halaman")
                                rule_text = st.text_input(
                                    "Halaman diambil",
                                    value="all",
                                    key=f"merge_rule_{index}",
                                    help="Contoh: all atau 1,2,5-8",
                                )
                                merge_page_rules.append(rule_text)

                                try:
                                    kept_pages = SplitMergeService.parse_page_selection_rule(int(total_pages), rule_text)
                                    removed_pages = [page for page in range(1, int(total_pages) + 1) if page not in set(kept_pages)]
                                    summary_rows.append(
                                        {
                                            "Dokumen": index,
                                            "Nama File": upload.name,
                                            "Dipertahankan": len(kept_pages),
                                            "Dihapus": len(removed_pages),
                                            "Halaman Dipertahankan": ", ".join(str(page) for page in kept_pages),
                                            "Halaman Dihapus": ", ".join(str(page) for page in removed_pages) if removed_pages else "-",
                                        }
                                    )
                                except Exception as exc:
                                    valid_rules = False
                                    summary_rows.append(
                                        {
                                            "Dokumen": index,
                                            "Nama File": upload.name,
                                            "Dipertahankan": 0,
                                            "Dihapus": 0,
                                            "Halaman Dipertahankan": "Rule tidak valid",
                                            "Halaman Dihapus": str(exc),
                                        }
                                    )

            with col_right:
                with st.container(border=True):
                    st.markdown("#### Step 4 - 👁️ Preview Output")
                    st.caption("Preview hasil merge sebelum download")

                    if family != "pdf":
                        st.info("Preview merge saat ini fokus untuk PDF.")
                    else:
                        try:
                            merged_previews = SplitMergeService.build_pdf_merge_preview_images(uploads, merge_page_rules)
                        except Exception as exc:
                            merged_previews = []
                            st.warning(f"Preview output belum bisa dibuat: {exc}")

                        if merged_previews:
                            st.caption(f"Total halaman preview: {len(merged_previews)}")
                            if len(merged_previews) > 1:
                                preview_limit = st.number_input(
                                    "Tampilkan halaman sampai",
                                    min_value=1,
                                    max_value=len(merged_previews),
                                    value=min(5, len(merged_previews)),
                                    step=1,
                                    key="merge_output_preview_limit",
                                )
                                visible_previews = merged_previews[: int(preview_limit)]
                                page_pick = st.slider(
                                    "Lihat halaman output ke",
                                    min_value=1,
                                    max_value=len(visible_previews),
                                    value=1,
                                    step=1,
                                    key="merge_output_preview_page",
                                )
                                source_name, source_page, image_bytes = visible_previews[page_pick - 1]
                            else:
                                source_name, source_page, image_bytes = merged_previews[0]

                            st.image(
                                image_bytes,
                                caption=f"Output merge • {source_name} halaman {source_page}",
                                use_container_width=True,
                            )
                        else:
                            st.info("Preview output akan muncul setelah rule halaman valid.")

            with st.container(border=True):
                st.markdown("#### Step 5 - 📊 Ringkasan & Aksi")
                if summary_rows:
                    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Ringkasan halaman akan muncul setelah rule diisi.")

        with st.container(border=True):
            action_label = "🪄 Proses Split" if mode == "split" else "🧩 Gabungkan File"
            action_disabled = (mode == "split" and not groups_for_preview) or (mode == "merge" and not valid_rules)
            action_clicked = st.button(action_label, type="primary", use_container_width=True, disabled=action_disabled)

        return SplitMergeViewResult(
            go_home=go_home,
            action_clicked=action_clicked,
            uploads=list(uploads),
            mode=mode,
            pattern_text=pattern_text,
            output_names=output_names,
            merge_page_rules=merge_page_rules,
        )
