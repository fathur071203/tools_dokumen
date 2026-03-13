from __future__ import annotations

import secrets
from pathlib import Path


class OutputNamingService:
    @staticmethod
    def build_filename(prefix: str, extension: str, index: int | None = None) -> str:
        ext = extension if extension.startswith(".") else f".{extension}"
        if index is None:
            return f"{prefix}_{secrets.token_hex(4)}{ext}"
        return f"{prefix}_{index:03d}{ext}"

    @classmethod
    def anonymize_named_payloads(
        cls,
        items: list[tuple[str, bytes]],
        prefix: str,
        default_extension: str = ".bin",
    ) -> list[tuple[str, bytes]]:
        anonymized: list[tuple[str, bytes]] = []
        for index, (filename, file_bytes) in enumerate(items, start=1):
            extension = Path(filename).suffix or default_extension
            anonymized.append((cls.build_filename(prefix, extension, index=index), file_bytes))
        return anonymized
