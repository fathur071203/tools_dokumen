from dataclasses import dataclass

from src.services.crypto_service import CryptoService


class PasswordMode:
    SINGLE = "single"
    INDIVIDUAL = "individual"


@dataclass
class EncryptedArtifact:
    file_name: str
    content: bytes


@dataclass
class DecryptedArtifact:
    file_name: str
    content: bytes


class FileLockerModel:
    def __init__(self, crypto_service: CryptoService):
        self.crypto_service = crypto_service

    def encrypt_file(self, file_name: str, content: bytes, password: str) -> EncryptedArtifact:
        encrypted = self.crypto_service.encrypt_blob(content, password, file_name)
        return EncryptedArtifact(file_name=f"{file_name}.encrypted", content=encrypted)

    def decrypt_file(self, encrypted_content: bytes, password: str) -> DecryptedArtifact:
        original_name, plain = self.crypto_service.decrypt_blob(encrypted_content, password)
        return DecryptedArtifact(file_name=original_name, content=plain)
