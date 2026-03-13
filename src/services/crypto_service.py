import base64
import io
import os
import struct

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pypdf import PdfReader, PdfWriter


class CryptoService:
    MAGIC = b"FLK2"
    LEGACY_MAGIC = b"FLK1"
    PDF_NAME_SALT_KEY = "/FLKNameSalt"
    PDF_NAME_TOKEN_KEY = "/FLKNameToken"

    @classmethod
    def is_file_locker_format(cls, file_bytes: bytes) -> bool:
        return len(file_bytes) >= 4 and file_bytes[:4] in {cls.MAGIC, cls.LEGACY_MAGIC}

    @staticmethod
    def is_pdf(file_bytes: bytes) -> bool:
        return file_bytes.lstrip().startswith(b"%PDF-")

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

    def encrypt_blob(self, file_bytes: bytes, password: str, original_name: str) -> bytes:
        salt = os.urandom(16)
        key = self._derive_key(password, salt)

        name_bytes = original_name.encode("utf-8")
        if len(name_bytes) > 65535:
            raise ValueError("Nama file terlalu panjang.")

        payload = struct.pack(">H", len(name_bytes)) + name_bytes + file_bytes
        token = Fernet(key).encrypt(payload)

        header = self.MAGIC + salt
        return header + token

    def decrypt_blob(self, encrypted_bytes: bytes, password: str) -> tuple[str, bytes]:
        min_header = 4 + 16
        if len(encrypted_bytes) < min_header:
            raise ValueError("Format file tidak valid.")

        magic = encrypted_bytes[:4]
        if magic not in {self.MAGIC, self.LEGACY_MAGIC}:
            raise ValueError("File bukan format File Locker (magic header tidak cocok).")

        if magic == self.LEGACY_MAGIC:
            return self._decrypt_legacy_blob(encrypted_bytes, password)

        salt = encrypted_bytes[4:20]
        token = encrypted_bytes[20:]

        key = self._derive_key(password, salt)
        try:
            plain_payload = Fernet(key).decrypt(token)
        except InvalidToken as exc:
            raise ValueError("Password salah atau file terenkripsi rusak.") from exc

        if len(plain_payload) < 2:
            raise ValueError("Payload file terenkripsi rusak.")

        name_len = struct.unpack(">H", plain_payload[:2])[0]
        start_name = 2
        end_name = start_name + name_len
        if len(plain_payload) < end_name:
            raise ValueError("Payload nama file rusak.")

        original_name = plain_payload[start_name:end_name].decode("utf-8", errors="replace")
        plain = plain_payload[end_name:]
        return original_name, plain

    def _decrypt_legacy_blob(self, encrypted_bytes: bytes, password: str) -> tuple[str, bytes]:
        min_header = 4 + 16 + 2
        if len(encrypted_bytes) < min_header:
            raise ValueError("Format file lama tidak valid.")

        salt = encrypted_bytes[4:20]
        name_len = struct.unpack(">H", encrypted_bytes[20:22])[0]

        start_name = 22
        end_name = start_name + name_len
        if len(encrypted_bytes) < end_name:
            raise ValueError("Header file rusak.")

        original_name = encrypted_bytes[start_name:end_name].decode("utf-8", errors="replace")
        token = encrypted_bytes[end_name:]

        key = self._derive_key(password, salt)
        try:
            plain = Fernet(key).decrypt(token)
        except InvalidToken as exc:
            raise ValueError("Password salah atau file terenkripsi rusak.") from exc

        return original_name, plain

    def encrypt_pdf(self, file_bytes: bytes, password: str, original_name: str | None = None) -> bytes:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            raise ValueError("PDF sudah memiliki password atau proteksi lain.")

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        metadata: dict[str, str] = {}
        if original_name:
            name_salt, name_token = self._encrypt_filename_token(original_name, password)
            metadata[self.PDF_NAME_SALT_KEY] = name_salt
            metadata[self.PDF_NAME_TOKEN_KEY] = name_token
        if metadata:
            writer.add_metadata(metadata)

        writer.encrypt(password)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    def decrypt_pdf(self, file_bytes: bytes, password: str) -> tuple[bytes, str | None]:
        reader = PdfReader(io.BytesIO(file_bytes))
        if not reader.is_encrypted:
            raise ValueError("File PDF ini tidak diproteksi dengan password.")

        if reader.decrypt(password) == 0:
            raise ValueError("Password PDF salah atau file PDF rusak.")

        original_name = self._decrypt_pdf_filename(reader.metadata, password)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue(), original_name

    def _encrypt_filename_token(self, original_name: str, password: str) -> tuple[str, str]:
        salt = os.urandom(16)
        key = self._derive_key(password, salt)
        token = Fernet(key).encrypt(original_name.encode("utf-8"))
        return base64.urlsafe_b64encode(salt).decode("ascii"), token.decode("ascii")

    def _decrypt_pdf_filename(self, metadata: dict | None, password: str) -> str | None:
        if not metadata:
            return None

        salt_value = metadata.get(self.PDF_NAME_SALT_KEY)
        token_value = metadata.get(self.PDF_NAME_TOKEN_KEY)
        if not salt_value or not token_value:
            return None

        try:
            salt = base64.urlsafe_b64decode(str(salt_value).encode("ascii"))
            key = self._derive_key(password, salt)
            plain_name = Fernet(key).decrypt(str(token_value).encode("ascii"))
            return plain_name.decode("utf-8", errors="replace")
        except Exception:
            return None
