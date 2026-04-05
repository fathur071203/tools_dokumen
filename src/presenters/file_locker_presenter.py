import io
import zipfile
import csv
from datetime import datetime

import streamlit as st

from src.models.file_locker_model import DecryptedArtifact, EncryptedArtifact, FileLockerModel
from src.services.security_service import SecurityService
from src.state.session_state import Page, SessionStateManager
from src.views.file_locker_decrypt_view import FileLockerDecryptView
from src.views.file_locker_encrypt_view import FileLockerEncryptView


class FileLockerPresenter:
    def __init__(
        self,
        model: FileLockerModel,
        encrypt_view: FileLockerEncryptView,
        decrypt_view: FileLockerDecryptView,
    ):
        self.model = model
        self.encrypt_view = encrypt_view
        self.decrypt_view = decrypt_view

    def present_encrypt_page(self) -> None:
        result = self.encrypt_view.render()

        if result.go_home:
            SessionStateManager.go(Page.HOME)
        if result.go_decrypt:
            SessionStateManager.go(Page.DECRYPT)

        if not result.encrypt_clicked:
            return

        if not result.uploads:
            st.error("Tidak ada file untuk dienkripsi.")
            return

        is_safe, security_message = SecurityService.validate_uploads(result.uploads)
        if not is_safe:
            st.error(f"❌ Upload ditolak: {security_message}")
            return

        if len(result.output_labels) != len(result.uploads):
            st.error("Konfigurasi alias output tidak valid. Silakan muat ulang halaman.")
            return

        if any(not label.strip() for label in result.output_labels):
            st.error("Alias output tidak boleh kosong.")
            return

        lowered = [label.strip().lower() for label in result.output_labels]
        if len(set(lowered)) != len(lowered):
            st.error("Alias output harus unik untuk setiap file.")
            return

        encrypted_artifacts: list[EncryptedArtifact] = []

        try:
            for index, (upload, password, output_label) in enumerate(
                zip(result.uploads, result.passwords, result.output_labels),
                start=1,
            ):
                encrypted = self.model.encrypt_file(
                    file_name=upload.name,
                    content=upload.read(),
                    password=password.strip(),
                    output_index=index,
                    output_label=output_label,
                )
                encrypted_artifacts.append(encrypted)
        except Exception as exc:
            st.error(f"Gagal mengenkripsi file: {exc}")
            return

        st.success("✅ File berhasil dienkripsi.")
        self._render_encrypt_mapping(encrypted_artifacts, result.passwords)
        self._render_encrypt_download(encrypted_artifacts)

    def present_decrypt_page(self) -> None:
        result = self.decrypt_view.render()

        if result.go_back:
            SessionStateManager.go(Page.LOCKER)

        if not result.decrypt_clicked:
            return

        if not result.encrypted_file:
            st.error("Tidak ada file yang dipilih.")
            return

        dec_safe, dec_message = SecurityService.validate_uploads(
            [result.encrypted_file],
            allowed_extensions={".encrypted", ".pdf"},
        )
        if not dec_safe:
            st.error(f"❌ File dekripsi ditolak: {dec_message}")
            return

        try:
            decrypted: DecryptedArtifact = self.model.decrypt_file(
                encrypted_content=result.encrypted_file.read(),
                password=result.password.strip(),
                uploaded_name=result.encrypted_file.name,
            )
        except Exception as exc:
            st.error(f"❌ Gagal dekripsi: {exc}")
            return

        st.success("✅ File berhasil didekripsi.")
        st.download_button(
            "📥 Download File Terdekripsi",
            data=decrypted.content,
            file_name=decrypted.file_name,
            mime=decrypted.mime_type,
        )

    def _render_encrypt_download(self, encrypted_artifacts: list[EncryptedArtifact]) -> None:
        if len(encrypted_artifacts) == 1:
            artifact = encrypted_artifacts[0]
            st.download_button(
                "📥 Download File Terenkripsi",
                data=artifact.content,
                file_name=artifact.file_name,
                mime=artifact.mime_type,
            )
            return

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for artifact in encrypted_artifacts:
                zf.writestr(artifact.file_name, artifact.content)

        zip_buffer.seek(0)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "📥 Download Semua (ZIP)",
            data=zip_buffer,
            file_name=f"encrypted_files_{ts}.zip",
            mime="application/zip",
        )

    @staticmethod
    def _render_encrypt_mapping(
        encrypted_artifacts: list[EncryptedArtifact],
        passwords: list[str],
    ) -> None:
        st.markdown("#### 🧾 Mapping Download & Password")

        rows: list[dict[str, str]] = []
        for idx, (artifact, pwd) in enumerate(zip(encrypted_artifacts, passwords), start=1):
            rows.append(
                {
                    "No": str(idx),
                    "File Hasil": artifact.file_name,
                    "Password": pwd,
                }
            )

        st.dataframe(rows, use_container_width=True, hide_index=True)

        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["No", "File Hasil", "Password"])
        writer.writeheader()
        writer.writerows(rows)

        st.download_button(
            "📥 Download Mapping (CSV)",
            data=csv_buffer.getvalue().encode("utf-8"),
            file_name=f"mapping_password_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
