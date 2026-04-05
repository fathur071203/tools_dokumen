from src.services.compress_service import CompressService
from src.services.security_service import SecurityService
from src.state.session_state import Page, SessionStateManager
from src.views.file_compressor_view import FileCompressorView
import streamlit as st


class FileCompressorPresenter:
    def __init__(self, view: FileCompressorView):
        self.view = view
        self.compress_service = CompressService()

    def present(self) -> None:
        result = self.view.render()

        if result.go_home:
            SessionStateManager.go(Page.HOME)

        if result.compress_clicked:
            if not result.uploads:
                st.error("❌ Tidak ada file untuk dikompres")
                return

            is_safe, security_message = SecurityService.validate_uploads(result.uploads)
            if not is_safe:
                st.error(f"❌ Upload ditolak: {security_message}")
                return

            # Compress files
            with st.spinner("🔄 Memproses file..."):
                try:
                    file_buffer, filename, is_compressed = self.compress_service.compress_files(
                        result.uploads,
                        compression_mode=result.compression_mode,
                        pdf_method=result.pdf_method,
                    )

                    # Calculate compression info
                    original_size = sum(f.size for f in result.uploads)
                    compressed_size = len(file_buffer.getvalue())
                    ratio = self.compress_service.get_compression_ratio(original_size, compressed_size)

                    # Determine format
                    if filename.endswith('.pptx'):
                        if result.compression_mode == self.compress_service.MODE_SAFE:
                            st.success("✅ PPT berhasil diproses dengan mode aman (optimasi ringan tanpa resize agresif).")
                        elif result.compression_mode == self.compress_service.MODE_BALANCED:
                            st.success("✅ PPT berhasil dioptimasi dengan mode seimbang.")
                        else:
                            st.success("✅ PPT berhasil dioptimasi dengan mode maksimal.")
                        action_text = "PPT Optimized"
                    elif filename.endswith('.pdf'):
                        actual_pdf_method = self.compress_service.get_last_pdf_method_used()
                        if result.compression_mode == self.compress_service.MODE_SAFE:
                            st.success("✅ PDF berhasil diproses dengan mode aman (optimasi ringan).")
                        elif result.compression_mode == self.compress_service.MODE_BALANCED:
                            st.success("✅ PDF berhasil dioptimasi dengan mode seimbang.")
                        else:
                            st.success("✅ PDF berhasil dioptimasi dengan mode maksimal.")
                        method_label = {
                            self.compress_service.PDF_METHOD_GHOSTSCRIPT: "Ghostscript",
                            self.compress_service.PDF_METHOD_PYMUPDF: "PyMuPDF",
                        }.get(actual_pdf_method, "Auto")
                        st.info(f"ℹ️ Metode PDF yang digunakan: **{method_label}**")
                        action_text = "PDF Optimized"
                    elif filename.endswith('.7z'):
                        st.success("✅ Kompresi selesai dengan format 7Z.")
                        action_text = "File 7Z"
                    else:
                        if result.compression_mode == self.compress_service.MODE_SAFE:
                            st.success("✅ Kompresi selesai dengan mode aman.")
                        elif result.compression_mode == self.compress_service.MODE_BALANCED:
                            st.success("✅ Kompresi selesai dengan mode seimbang.")
                        else:
                            st.success("✅ Kompresi selesai dengan mode maksimal.")
                        action_text = "File ZIP"

                    # Jelaskan bila rasio kompresi kecil
                    compressed_exts = {
                        ".zip", ".7z", ".rar", ".gz", ".bz2", ".xz",
                        ".jpg", ".jpeg", ".png", ".gif", ".webp",
                        ".mp4", ".mkv", ".avi", ".mov", ".mp3", ".aac",
                        ".docx", ".xlsx", ".pptx", ".pdf",
                    }
                    upload_exts = {
                        (f.name[f.name.rfind("."):].lower() if "." in f.name else "")
                        for f in result.uploads
                    }
                    if ratio <= 1.0 and any(ext in compressed_exts for ext in upload_exts):
                        st.info(
                            "ℹ️ Beberapa format file sudah terkompres (mis. PPTX/PDF/JPG/MP4), "
                            "jadi penghematan bisa sangat kecil meski proses kompresi berhasil."
                        )

                    st.markdown("---")

                    # Display compression stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Ukuran Asli", self.compress_service.format_size(original_size))
                    with col2:
                        st.metric("Ukuran Output", self.compress_service.format_size(compressed_size))
                    with col3:
                        st.metric("Penghematan", f"{ratio:.1f}%")

                    # Download button
                    if filename.endswith('.7z'):
                        mime_type = "application/x-7z-compressed"
                    elif filename.endswith('.pptx'):
                        mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    elif filename.endswith('.pdf'):
                        mime_type = "application/pdf"
                    else:
                        mime_type = "application/zip"
                    st.download_button(
                        label=f"📥 Download {action_text}",
                        data=file_buffer,
                        file_name=filename,
                        mime=mime_type,
                        use_container_width=True,
                    )

                except Exception as e:
                    st.error(f"❌ Gagal memproses file: {str(e)}")
                    error_text = str(e).lower()
                    if "ghostscript" in error_text or "pymupdf" in error_text or ".pdf" in error_text:
                        st.write("💡 Tip: Untuk PDF lokal, install Ghostscript agar metode Ghostscript dapat digunakan. Jika belum tersedia, gunakan Auto/PyMuPDF.")
                    else:
                        st.write("💡 Tip: Jika 7z tidak tersedia, coba gunakan format ZIP")
