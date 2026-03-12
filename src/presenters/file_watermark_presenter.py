import streamlit as st

from src.services.watermark_service import WatermarkService
from src.state.session_state import Page, SessionStateManager
from src.views.file_watermark_view import FileWatermarkView


class FileWatermarkPresenter:
    def __init__(self, view: FileWatermarkView):
        self.view = view
        self.service = WatermarkService()

    def present(self) -> None:
        result = self.view.render()

        if result.go_home:
            SessionStateManager.go(Page.HOME)

        if not result.apply_clicked:
            return

        try:
            with st.spinner("💧 Menambahkan watermark ke PDF..."):
                output, filename, mime_type, message = self.service.add_watermark(
                    pdf_upload=result.pdf_upload,
                    watermark_mode=result.watermark_mode,
                    text=result.watermark_text,
                    image_upload=result.watermark_image,
                    position=result.position,
                    orientation=result.orientation,
                    opacity=result.opacity,
                    size_ratio=result.size_ratio,
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
            st.error(f"❌ Gagal menambahkan watermark: {exc}")