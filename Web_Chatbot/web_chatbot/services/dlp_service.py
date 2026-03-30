from __future__ import annotations

import os
import re


class DLPService:
    ENV_DLP_ENABLED = "TOOLS_DOKUMEN_DLP_ENABLED"

    _SENSITIVE_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
        ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE), "[REDACTED_EMAIL]"),
        ("phone", re.compile(r"(?:\+62|62|0)\d{8,13}\b", re.IGNORECASE), "[REDACTED_PHONE]"),
        ("nik", re.compile(r"\b\d{16}\b", re.IGNORECASE), "[REDACTED_NIK]"),
        ("npwp", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}\.?\d-?\d{3}\.?\d{3}\b", re.IGNORECASE), "[REDACTED_NPWP]"),
        ("api_key_google", re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"), "[REDACTED_API_KEY]"),
        ("api_key_openai", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "[REDACTED_API_KEY]"),
        ("password_like", re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*[^\s,;]{4,}"), "password=[REDACTED]"),
        ("long_account_number", re.compile(r"\b\d{10,20}\b"), "[REDACTED_NUMBER]"),
    ]

    _BLOCKED_REQUEST_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"(?i)\b(tampilkan|beri|print|dump)\b.*\b(seluruh|full|lengkap)\b.*\b(dokumen|isi|teks)\b"),
        re.compile(r"(?i)\b(api\s*key|credential|token|password|secret)\b.*\b(tampilkan|berikan|kirim)\b"),
        re.compile(r"(?i)\b(copy|salin)\b.*\b(mentah|raw|apa adanya)\b"),
    ]

    @classmethod
    def is_enabled(cls) -> bool:
        raw = str(os.getenv(cls.ENV_DLP_ENABLED, "true") or "").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    @classmethod
    def validate_question(cls, question: str) -> tuple[bool, str]:
        if not cls.is_enabled():
            return True, "OK"

        q = question.strip()
        if not q:
            return False, "Pertanyaan kosong."

        for pattern in cls._BLOCKED_REQUEST_PATTERNS:
            if pattern.search(q):
                return False, "Permintaan ditolak oleh kebijakan DLP. Gunakan pertanyaan berbentuk ringkasan/analisis."

        return True, "OK"

    @classmethod
    def redact_text(cls, text: str, max_length: int | None = None) -> tuple[str, list[str]]:
        if not text:
            return "", []

        output = text
        hits: list[str] = []

        if cls.is_enabled():
            for label, pattern, replacement in cls._SENSITIVE_PATTERNS:
                if pattern.search(output):
                    output = pattern.sub(replacement, output)
                    hits.append(label)

        if max_length is not None and max_length > 0 and len(output) > max_length:
            output = output[: max_length - 3].rstrip() + "..."

        return output, sorted(set(hits))

    @classmethod
    def sanitize_source_label(cls, source_path: str) -> str:
        parts = [segment for segment in source_path.replace("\\", "/").split("/") if segment]
        if not parts:
            return source_path
        if len(parts) == 1:
            return parts[0]
        return f"{parts[-2]}/{parts[-1]}"

    @classmethod
    def build_dlp_notice(cls, findings: list[str]) -> str:
        if not findings:
            return ""
        return f"⚠️ Sebagian konten disamarkan otomatis oleh DLP ({', '.join(findings)})."
