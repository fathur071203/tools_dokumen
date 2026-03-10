import streamlit as st

from src.services.split_merge_service import SplitMergeService
from src.state.session_state import Page, SessionStateManager
from src.views.file_split_merge_view import FileSplitMergeView


class FileSplitMergePresenter:
    def __init__(self, view: FileSplitMergeView):
        self.view = view
        self.service = SplitMergeService()

    def present(self) -> None:
        result = self.view.render()

        if result.go_home:
            SessionStateManager.go(Page.HOME)

        if not result.action_clicked:
            return

        try:
            with st.spinner("🔄 Memproses dokumen..."):
                if result.mode == "split":
                    output, filename, mime_type, message = self.service.split_document(
                        result.uploads[0],
                        result.pattern_text,
                        result.output_names,
                    )
                else:
                    output, filename, mime_type, message = self.service.merge_documents(result.uploads)

            st.success(f"✅ {message}")
            st.download_button(
                label=f"📥 Download {filename}",
                data=output,
                file_name=filename,
                mime=mime_type,
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"❌ Gagal memproses dokumen: {exc}")
            st.info(
                "Untuk Word/PPT, fitur ini hanya berjalan di Windows dengan Microsoft Office desktop. "
                "Di deploy Linux, gunakan file PDF untuk split/gabung."
            )
