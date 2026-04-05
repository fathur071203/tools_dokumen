import mimetypes
import io
import re
import zipfile
from pathlib import Path
from dataclasses import dataclass

from src.services.crypto_service import CryptoService
from src.services.output_naming_service import OutputNamingService


class PasswordMode:
    SINGLE = "single"
    INDIVIDUAL = "individual"


@dataclass
class EncryptedArtifact:
    file_name: str
    content: bytes
    mime_type: str


@dataclass
class DecryptedArtifact:
    file_name: str
    content: bytes
    mime_type: str


class FileLockerModel:
    OFFICE_ARCHIVE_EXTENSIONS = {
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
    }

    def __init__(self, crypto_service: CryptoService):
        self.crypto_service = crypto_service

    def encrypt_file(
        self,
        file_name: str,
        content: bytes,
        password: str,
        output_index: int | None = None,
        output_label: str | None = None,
    ) -> EncryptedArtifact:
        suffix = Path(file_name).suffix.lower()

        if suffix == ".pdf":
            encrypted_pdf = self.crypto_service.encrypt_pdf(content, password, original_name=file_name)
            return EncryptedArtifact(
                file_name=self._build_encrypted_output_name("pdf", output_index, output_label),
                content=encrypted_pdf,
                mime_type="application/pdf",
            )

        original_name = file_name
        if self._should_archive_before_encrypt(file_name):
            original_name, content = self._archive_file(file_name, content)

        encrypted = self.crypto_service.encrypt_blob(content, password, original_name)
        return EncryptedArtifact(
            file_name=self._build_encrypted_output_name("encrypted", output_index, output_label),
            content=encrypted,
            mime_type="application/octet-stream",
        )

    def decrypt_file(self, encrypted_content: bytes, password: str, uploaded_name: str | None = None) -> DecryptedArtifact:
        if self.crypto_service.is_file_locker_format(encrypted_content):
            original_name, plain = self.crypto_service.decrypt_blob(encrypted_content, password)
            output_name = OutputNamingService.build_filename("decrypted_file", Path(original_name).suffix or ".bin")
            return DecryptedArtifact(file_name=output_name, content=plain, mime_type=self._guess_mime_type(original_name))

        if self.crypto_service.is_pdf(encrypted_content):
            plain, original_name = self.crypto_service.decrypt_pdf(encrypted_content, password)
            extension = Path(original_name or uploaded_name or "decrypted_document.pdf").suffix or ".pdf"
            output_name = OutputNamingService.build_filename("decrypted_document", extension)
            return DecryptedArtifact(file_name=output_name, content=plain, mime_type="application/pdf")

        raise ValueError("Format file tidak didukung untuk dekripsi.")

    @staticmethod
    def _guess_mime_type(file_name: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type or "application/octet-stream"

    @classmethod
    def _should_archive_before_encrypt(cls, file_name: str) -> bool:
        return Path(file_name).suffix.lower() in cls.OFFICE_ARCHIVE_EXTENSIONS

    @staticmethod
    def _archive_file(file_name: str, content: bytes) -> tuple[str, bytes]:
        archive_name = f"{Path(file_name).stem}.zip"
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr(file_name, content)
        archive_buffer.seek(0)
        return archive_name, archive_buffer.getvalue()

    @staticmethod
    def _build_encrypted_output_name(
        extension: str,
        output_index: int | None = None,
        output_label: str | None = None,
    ) -> str:
        if output_label:
            safe_label = re.sub(r"[^A-Za-z0-9._-]+", "_", output_label.strip())
            safe_label = Path(safe_label).stem.strip("._-")
            if safe_label:
                return f"{safe_label}.{extension}"

        index = output_index or 1
        return f"locked_file_{index:03d}.{extension}"
