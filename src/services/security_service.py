from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class SecurityService:
    ENV_MAX_FILE_MB = "TOOLS_DOKUMEN_MAX_FILE_MB"
    ENV_MAX_TOTAL_MB = "TOOLS_DOKUMEN_MAX_TOTAL_MB"
    ENV_MAX_FILES = "TOOLS_DOKUMEN_MAX_FILES"

    DEFAULT_MAX_FILE_MB = 50
    DEFAULT_MAX_TOTAL_MB = 250
    DEFAULT_MAX_FILES = 25

    BLOCKED_EXTENSIONS = {
        ".exe",
        ".dll",
        ".bat",
        ".cmd",
        ".ps1",
        ".scr",
        ".com",
        ".msi",
        ".vbs",
        ".js",
        ".jar",
        ".apk",
        ".sh",
    }

    @classmethod
    def validate_uploads(
        cls,
        uploads: list[Any],
        allowed_extensions: set[str] | None = None,
    ) -> tuple[bool, str]:
        if not uploads:
            return False, "Tidak ada file yang diupload."

        max_files = cls._get_env_int(cls.ENV_MAX_FILES, cls.DEFAULT_MAX_FILES, min_value=1)
        max_file_mb = cls._get_env_int(cls.ENV_MAX_FILE_MB, cls.DEFAULT_MAX_FILE_MB, min_value=1)
        max_total_mb = cls._get_env_int(cls.ENV_MAX_TOTAL_MB, cls.DEFAULT_MAX_TOTAL_MB, min_value=1)

        if len(uploads) > max_files:
            return False, f"Jumlah file melebihi batas keamanan ({max_files} file per proses)."

        total_size = 0
        normalized_allowed = {ext.lower() for ext in (allowed_extensions or set())}

        for upload in uploads:
            file_name = str(getattr(upload, "name", "") or "").strip()
            if not file_name:
                return False, "Nama file tidak valid."

            extension = Path(file_name).suffix.lower()
            if extension in cls.BLOCKED_EXTENSIONS:
                return False, f"Ekstensi file `{extension}` diblokir demi keamanan."

            if normalized_allowed and extension not in normalized_allowed:
                allowed_label = ", ".join(sorted(normalized_allowed))
                return False, f"File `{file_name}` tidak didukung. Ekstensi yang diizinkan: {allowed_label}."

            file_size = int(getattr(upload, "size", 0) or 0)
            if file_size <= 0:
                return False, f"Ukuran file `{file_name}` tidak valid."

            if file_size > max_file_mb * 1024 * 1024:
                return False, f"File `{file_name}` melebihi batas {max_file_mb} MB per file."

            total_size += file_size

        if total_size > max_total_mb * 1024 * 1024:
            return False, f"Total ukuran upload melebihi batas {max_total_mb} MB per proses."

        return True, "OK"

    @classmethod
    def _get_env_int(cls, key: str, default: int, min_value: int = 1) -> int:
        raw = str(os.getenv(key, str(default)) or "").strip()
        try:
            value = int(raw)
        except ValueError:
            value = default
        return max(value, min_value)
