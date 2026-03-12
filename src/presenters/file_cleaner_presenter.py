import streamlit as st

from src.services.ltdbb_cleaner_service import CleanerResult, LTDBBCleanerService
from src.state.session_state import Page, SessionStateManager
from src.views.file_cleaner_view import FileCleanerView


class FileCleanerPresenter:
    def __init__(self, view: FileCleanerView):
        self.view = view
        self.service = LTDBBCleanerService()

    def present(self) -> None:
        result = self.view.render()

        if result.go_home:
            SessionStateManager.go(Page.HOME)

        if not result.process_clicked:
            return

        if result.upload is None:
            st.error("❌ Tidak ada file yang dipilih.")
            return

        try:
            with st.spinner("🧹 Membersihkan file LTDBB..."):
                cleaned = self.service.process_upload(result.upload, result.variant_override)
        except ValueError as exc:
            st.error(f"❌ Kesalahan pemrosesan: {exc}")
            return
        except Exception:
            st.error(
                "❌ File tidak dapat dibaca sebagai Excel/CSV. Pastikan format benar (CSV/XLSX/XLS) dan bukan file rusak."
            )
            return

        self._render_output(cleaned)

    def _render_output(self, cleaned: CleanerResult) -> None:
        st.success("✅ File berhasil diproses. Lihat ringkasan di bawah dan unduh CSV bersih.")

        summary = cleaned.summary
        st.markdown("---")
        st.markdown("### 📊 Ringkasan Hasil")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Jenis", summary.get("variant") or "-")
        col2.metric("Nama PJP", summary.get("pjp_name") or "-")
        col3.metric("Sandi PJP", summary.get("pjp_sandi") or "-")
        col4.metric("Periode", summary.get("periode_text") or "-")

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Total Baris", f"{summary.get('rows', 0):,}")
        total_frekuensi = summary.get("total_frekuensi")
        total_nominal = summary.get("total_nominal")
        col6.metric("Total Frekuensi", f"{int(total_frekuensi):,}" if total_frekuensi is not None else "-")
        col7.metric("Total Nominal", f"Rp {total_nominal:,.0f}" if total_nominal is not None else "-")
        col8.metric("Jumlah Kolom", f"{summary.get('columns', 0):,}")

        st.download_button(
            "📥 Unduh CSV Bersih",
            data=cleaned.cleaned_csv,
            file_name=cleaned.download_name,
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("---")
        st.markdown("### 👀 Preview 10 Baris Pertama")
        st.dataframe(cleaned.preview_df, use_container_width=True, hide_index=True)

        if not cleaned.top_dest_by_freq.empty or not cleaned.top_dest_by_nominal.empty:
            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("### 🔝 Top 10 Destinasi berdasarkan Frekuensi")
                st.dataframe(cleaned.top_dest_by_freq, use_container_width=True, hide_index=True)
                if not cleaned.top_dest_by_freq.empty:
                    st.download_button(
                        "📥 Export Top Frekuensi",
                        data=cleaned.top_dest_by_freq.to_csv(index=False, encoding="utf-8").encode("utf-8"),
                        file_name="top_destinasi_frekuensi.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_top_freq",
                    )
            with col_b:
                st.markdown("### 💰 Top 10 Destinasi berdasarkan Nominal")
                st.dataframe(cleaned.top_dest_by_nominal, use_container_width=True, hide_index=True)
                if not cleaned.top_dest_by_nominal.empty:
                    st.download_button(
                        "📥 Export Top Nominal",
                        data=cleaned.top_dest_by_nominal.to_csv(index=False, encoding="utf-8").encode("utf-8"),
                        file_name="top_destinasi_nominal.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_top_nominal",
                    )