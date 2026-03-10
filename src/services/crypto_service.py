import base64
import io
import os
import struct

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pypdf import PdfReader, PdfWriter


class CryptoService:
    MAGIC = b"FLK1"

    @classmethod
    def is_file_locker_format(cls, file_bytes: bytes) -> bool:
        return len(file_bytes) >= 4 and file_bytes[:4] == cls.MAGIC

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
        token = Fernet(key).encrypt(file_bytes)

        name_bytes = original_name.encode("utf-8")
        if len(name_bytes) > 65535:
            raise ValueError("Nama file terlalu panjang.")

        header = self.MAGIC + salt + struct.pack(">H", len(name_bytes)) + name_bytes
        return header + token

    def decrypt_blob(self, encrypted_bytes: bytes, password: str) -> tuple[str, bytes]:
        min_header = 4 + 16 + 2
        if len(encrypted_bytes) < min_header:
            raise ValueError("Format file tidak valid.")

        magic = encrypted_bytes[:4]
        if magic != self.MAGIC:
            raise ValueError("File bukan format File Locker (magic header tidak cocok).")

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

    def encrypt_pdf(self, file_bytes: bytes, password: str) -> bytes:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            raise ValueError("PDF sudah memiliki password atau proteksi lain.")

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        if reader.metadata:
            writer.add_metadata(reader.metadata)

        writer.encrypt(password)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    def decrypt_pdf(self, file_bytes: bytes, password: str) -> bytes:
        reader = PdfReader(io.BytesIO(file_bytes))
        if not reader.is_encrypted:
            raise ValueError("File PDF ini tidak diproteksi dengan password.")

        if reader.decrypt(password) == 0:
            raise ValueError("Password PDF salah atau file PDF rusak.")

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        if reader.metadata:
            writer.add_metadata(reader.metadata)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
