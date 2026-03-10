import mimetypes
from pathlib import Path
from dataclasses import dataclass

from src.services.crypto_service import CryptoService


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
    def __init__(self, crypto_service: CryptoService):
        self.crypto_service = crypto_service

    def encrypt_file(self, file_name: str, content: bytes, password: str) -> EncryptedArtifact:
        if Path(file_name).suffix.lower() == ".pdf":
            encrypted_pdf = self.crypto_service.encrypt_pdf(content, password)
            return EncryptedArtifact(file_name=file_name, content=encrypted_pdf, mime_type="application/pdf")

        encrypted = self.crypto_service.encrypt_blob(content, password, file_name)
        return EncryptedArtifact(
            file_name=f"{file_name}.encrypted",
            content=encrypted,
            mime_type="application/octet-stream",
        )

    def decrypt_file(self, encrypted_content: bytes, password: str, uploaded_name: str | None = None) -> DecryptedArtifact:
        if self.crypto_service.is_file_locker_format(encrypted_content):
            original_name, plain = self.crypto_service.decrypt_blob(encrypted_content, password)
            return DecryptedArtifact(file_name=original_name, content=plain, mime_type=self._guess_mime_type(original_name))

        if self.crypto_service.is_pdf(encrypted_content):
            plain = self.crypto_service.decrypt_pdf(encrypted_content, password)
            output_name = uploaded_name or "decrypted_document.pdf"
            return DecryptedArtifact(file_name=output_name, content=plain, mime_type="application/pdf")

        raise ValueError("Format file tidak didukung untuk dekripsi.")

    @staticmethod
    def _guess_mime_type(file_name: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type or "application/octet-stream"
