import streamlit as st

from src.services.security_service import SecurityService
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

        if not result.preview_clicked and not result.apply_clicked:
            return

        pdf_safe, pdf_message = SecurityService.validate_uploads([result.pdf_upload], allowed_extensions={".pdf"})
        if not pdf_safe:
            st.error(f"❌ Upload PDF ditolak: {pdf_message}")
            return

        if result.watermark_mode == "image" and result.watermark_image is not None:
            image_safe, image_message = SecurityService.validate_uploads(
                [result.watermark_image],
                allowed_extensions={".png"},
            )
            if not image_safe:
                st.error(f"❌ Upload gambar ditolak: {image_message}")
                return

        try:
            action_text = "Membuat preview watermark" if result.preview_clicked else "Menambahkan watermark ke PDF"
            with st.spinner(f"💧 {action_text}..."):
                output, filename, mime_type, message = self.service.add_watermark(
                    pdf_upload=result.pdf_upload,
                    watermark_mode=result.watermark_mode,
                    text=result.watermark_text,
                    template_name=result.watermark_template,
                    image_upload=result.watermark_image,
                    text_color=result.text_color,
                    use_bezel=result.use_bezel,
                    position=result.position,
                    orientation=result.orientation,
                    opacity=result.opacity,
                    size_ratio=result.size_ratio,
                )

            if result.preview_clicked:
                st.session_state[FileWatermarkView.KEY_WATERMARK_PREVIEW_PDF] = output.getvalue()
                preview_images = self.service.build_pdf_preview_images(output, max_pages=3, zoom=1.2)
                st.session_state[FileWatermarkView.KEY_WATERMARK_PREVIEW_IMAGES] = preview_images
                st.session_state[FileWatermarkView.KEY_WATERMARK_PREVIEW_SOURCE] = (
                    f"{getattr(result.pdf_upload, 'name', '')}:{int(getattr(result.pdf_upload, 'size', 0) or 0)}"
                )
                st.success("✅ Preview watermark berhasil dibuat. Lihat panel preview di sebelah kanan.")
                st.rerun()
                return

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