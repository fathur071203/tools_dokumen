import streamlit as st

from src.services.convert_service import ConvertService
from src.state.session_state import Page, SessionStateManager
from src.views.file_converter_view import FileConverterView


class FileConverterPresenter:
    def __init__(self, view: FileConverterView):
        self.view = view
        self.convert_service = ConvertService()

    def present(self) -> None:
        result = self.view.render()

        if result.go_home:
            SessionStateManager.go(Page.HOME)

        if not result.convert_clicked:
            return

        if not result.uploads:
            st.error("❌ Tidak ada file untuk dikonversi")
            return

        spinner_text = "🔄 Mengonversi file..."
        if len(result.uploads) > 1 and result.target_format == "pdf":
            spinner_text = "🔄 Mengonversi dan menyiapkan PDF..."

        with st.spinner(spinner_text):
            try:
                output, filename, mime_type, message = self.convert_service.convert_files(
                    result.uploads,
                    result.target_format,
                    result.pdf_output_mode,
                )
                st.success(f"✅ {message}")
                st.download_button(
                    label=f"📥 Download {filename}",
                    data=output,
                    file_name=filename,
                    mime=mime_type,
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"❌ Gagal mengonversi file: {exc}")
                st.info(
                    "Untuk Word/Excel/PPT ke PDF, pastikan Microsoft Office desktop tersedia di Windows ini."
                )
