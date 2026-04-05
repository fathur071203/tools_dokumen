from __future__ import annotations

import json
import base64
import hashlib
import hmac
import os
import random
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gspread
from gspread.exceptions import APIError


@dataclass
class LoginIdentity:
    full_name: str
    username: str
    email: str
    unit: str
    role: str = "user"


class SpreadsheetTrackingService:
    BASE_DIR = Path(__file__).resolve().parents[2]
    CREDENTIALS_PATH = BASE_DIR / "static" / "credentials.json"

    ENV_SPREADSHEET_ID = "TOOLS_DOKUMEN_SPREADSHEET_ID"
    ENV_SPREADSHEET_NAME = "TOOLS_DOKUMEN_SPREADSHEET_NAME"
    ENV_GOOGLE_SERVICE_ACCOUNT_JSON = "GOOGLE_SERVICE_ACCOUNT_JSON"
    DEFAULT_SPREADSHEET_ID = "1yzRr2cJXzARkbEOlpJd2SqGyfAMn_h0o3jG2-P2Pxb8"
    DEFAULT_SPREADSHEET_NAME = "tools_dokumen"

    USERS_SHEET = "users"
    ACCESS_LOG_SHEET = "access_log"
    ENV_ADMIN_USERNAMES = "TOOLS_DOKUMEN_ADMIN_USERNAMES"

    USER_STATUS_ACTIVE = "active"
    USER_STATUS_PENDING = "pending"
    USER_STATUS_REJECTED = "rejected"
    USER_ROLE_USER = "user"
    USER_ROLE_ADMIN = "admin"

    USER_HEADERS = [
        "registered_at",
        "last_login_at",
        "full_name",
        "username",
        "email",
        "unit",
        "status",
        "password_hash",
        "role",
        "approved_by",
        "approved_at",
    ]
    ACCESS_LOG_HEADERS = ["timestamp", "full_name", "email", "unit", "status", "reason"]

    PASSWORD_HASH_ALGO = "pbkdf2_sha256"
    PASSWORD_HASH_ITERATIONS = 310000

    LOGIN_QUEUE_LOCK_TIMEOUT_SECONDS = 30.0
    API_MAX_RETRIES = 6
    API_INITIAL_BACKOFF_SECONDS = 0.6
    API_MAX_BACKOFF_SECONDS = 6.0
    API_JITTER_SECONDS = 0.25

    _sheet_operation_lock = threading.Lock()

    @classmethod
    def register_user(cls, identity: LoginIdentity, password: str) -> tuple[bool, str]:
        def _operation() -> tuple[bool, str]:
            spreadsheet = cls._open_spreadsheet()
            users_sheet = cls._get_or_create_worksheet(spreadsheet, cls.USERS_SHEET, cls.USER_HEADERS)

            row, existing = cls._find_user_row_by_username(users_sheet, identity.username)
            if row:
                status = str(existing.get("status", "active") or "active")
                return False, f"Username {identity.username} sudah terdaftar dengan status {status}."

            row, existing = cls._find_user_row_by_email(users_sheet, identity.email)
            if row:
                status = str(existing.get("status", "active") or "active")
                return False, f"Email {identity.email} sudah terdaftar dengan status {status}."

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            password_hash = cls._hash_password(password)

            is_admin_account = cls.is_admin_username(identity.username)
            initial_status = cls.USER_STATUS_ACTIVE if is_admin_account else cls.USER_STATUS_PENDING
            initial_role = cls.USER_ROLE_ADMIN if is_admin_account else cls.USER_ROLE_USER

            users_sheet.append_row(
                [
                    now,
                    "",
                    identity.full_name,
                    identity.username,
                    identity.email,
                    identity.unit,
                    initial_status,
                    password_hash,
                    initial_role,
                    "",
                    "",
                ],
                value_input_option="USER_ENTERED",
            )

            if is_admin_account:
                return True, "Registrasi admin berhasil. Akun admin langsung aktif."
            return True, "Registrasi berhasil. Akun Anda menunggu persetujuan admin."

        return cls._run_sheet_operation_with_queue(_operation)

    @classmethod
    def verify_user_credentials(cls, username: str, password: str) -> tuple[bool, str, LoginIdentity | None]:
        def _operation() -> tuple[bool, str, LoginIdentity | None]:
            spreadsheet = cls._open_spreadsheet()
            users_sheet = cls._get_or_create_worksheet(spreadsheet, cls.USERS_SHEET, cls.USER_HEADERS)

            _, existing_data = cls._find_user_row_by_username(users_sheet, username)
            if not existing_data:
                return False, "Username belum terdaftar.", None

            stored_hash = str(existing_data.get("password_hash", "") or "").strip()
            if not stored_hash:
                return False, "Password user belum terdaftar. Silakan daftar ulang.", None

            if not cls._verify_password(password, stored_hash):
                return False, "Password user salah.", None

            status = str(existing_data.get("status", "") or "").strip().lower() or cls.USER_STATUS_ACTIVE
            if status == cls.USER_STATUS_PENDING:
                return False, "Akun Anda masih menunggu persetujuan admin.", None
            if status == cls.USER_STATUS_REJECTED:
                return False, "Akun Anda ditolak admin. Hubungi admin untuk pengajuan ulang.", None
            if status != cls.USER_STATUS_ACTIVE:
                return False, f"Status akun tidak diizinkan untuk login: {status}.", None

            role = str(existing_data.get("role", "") or "").strip().lower()
            if not role:
                role = cls.USER_ROLE_ADMIN if cls.is_admin_username(username) else cls.USER_ROLE_USER

            identity = LoginIdentity(
                full_name=str(existing_data.get("full_name", "") or "").strip(),
                username=str(existing_data.get("username", "") or "").strip().lower(),
                email=str(existing_data.get("email", "") or "").strip().lower(),
                unit=str(existing_data.get("unit", "") or "").strip(),
                role=role,
            )
            return True, "Kredensial user valid.", identity

        return cls._run_sheet_operation_with_queue(_operation)

    @classmethod
    def register_and_log_login(cls, identity: LoginIdentity) -> tuple[bool, str]:
        def _operation() -> tuple[bool, str]:
            spreadsheet = cls._open_spreadsheet()
            users_sheet = cls._get_or_create_worksheet(spreadsheet, cls.USERS_SHEET, cls.USER_HEADERS)
            access_log_sheet = cls._get_or_create_worksheet(spreadsheet, cls.ACCESS_LOG_SHEET, cls.ACCESS_LOG_HEADERS)

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            cls._upsert_user(users_sheet, identity=identity, login_time=now)

            access_log_sheet.append_row(
                [now, identity.full_name, identity.email, identity.unit, "login_success", ""],
                value_input_option="USER_ENTERED",
            )
            return True, "Registrasi & tracking login berhasil disimpan ke spreadsheet."

        return cls._run_sheet_operation_with_queue(_operation)

    @classmethod
    def _run_sheet_operation_with_queue(cls, operation: Any) -> Any:
        acquired = cls._sheet_operation_lock.acquire(timeout=cls.LOGIN_QUEUE_LOCK_TIMEOUT_SECONDS)
        if not acquired:
            raise TimeoutError(
                "Layanan login sedang antre. Silakan tunggu beberapa detik lalu coba lagi."
            )

        try:
            backoff_seconds = cls.API_INITIAL_BACKOFF_SECONDS
            for attempt in range(1, cls.API_MAX_RETRIES + 1):
                try:
                    return operation()
                except Exception as exc:  # noqa: BLE001
                    should_retry = cls._should_retry_spreadsheet_error(exc)
                    if (not should_retry) or attempt >= cls.API_MAX_RETRIES:
                        raise

                    jitter = random.uniform(0, cls.API_JITTER_SECONDS)
                    sleep_seconds = min(backoff_seconds, cls.API_MAX_BACKOFF_SECONDS) + jitter
                    time.sleep(sleep_seconds)
                    backoff_seconds = min(backoff_seconds * 2, cls.API_MAX_BACKOFF_SECONDS)
        finally:
            cls._sheet_operation_lock.release()

    @classmethod
    def _should_retry_spreadsheet_error(cls, exc: Exception) -> bool:
        if isinstance(exc, APIError):
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in {429, 500, 502, 503, 504}:
                return True

        text = str(exc).lower()
        retry_keywords = [
            "quota",
            "rate limit",
            "too many requests",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "internal error",
            "backend error",
            "try again",
        ]
        return any(keyword in text for keyword in retry_keywords)

    @classmethod
    def is_admin_username(cls, username: str) -> bool:
        raw = os.getenv(cls.ENV_ADMIN_USERNAMES, "")
        admins = {item.strip().lower() for item in raw.split(",") if item.strip()}
        return username.strip().lower() in admins

    @classmethod
    def _upsert_user(cls, worksheet: gspread.Worksheet, identity: LoginIdentity, login_time: str) -> None:
        existing_row_number, existing_data = cls._find_user_row_by_email(worksheet=worksheet, email=identity.email)

        if existing_row_number:
            status = str(existing_data.get("status", "") or "").strip().lower() or cls.USER_STATUS_ACTIVE
            role = str(existing_data.get("role", "") or "").strip().lower() or identity.role or cls.USER_ROLE_USER
            worksheet.update(
                f"A{existing_row_number}:K{existing_row_number}",
                [[
                    existing_data.get("registered_at", login_time),
                    login_time,
                    identity.full_name,
                    identity.username,
                    identity.email,
                    identity.unit,
                    status,
                    existing_data.get("password_hash", ""),
                    role,
                    existing_data.get("approved_by", ""),
                    existing_data.get("approved_at", ""),
                ]],
                value_input_option="USER_ENTERED",
            )
            return

        initial_status = cls.USER_STATUS_ACTIVE
        if identity.role != cls.USER_ROLE_ADMIN and not cls.is_admin_username(identity.username):
            initial_status = cls.USER_STATUS_PENDING

        initial_role = identity.role if identity.role else cls.USER_ROLE_USER
        worksheet.append_row(
            [
                login_time,
                login_time,
                identity.full_name,
                identity.username,
                identity.email,
                identity.unit,
                initial_status,
                "",
                initial_role,
                "",
                "",
            ],
            value_input_option="USER_ENTERED",
        )

    @classmethod
    def _hash_password(cls, raw_password: str) -> str:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt, cls.PASSWORD_HASH_ITERATIONS)
        salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii")
        dk_b64 = base64.urlsafe_b64encode(dk).decode("ascii")
        return f"{cls.PASSWORD_HASH_ALGO}${cls.PASSWORD_HASH_ITERATIONS}${salt_b64}${dk_b64}"

    @classmethod
    def _verify_password(cls, candidate_password: str, stored_hash: str) -> bool:
        if stored_hash.startswith(f"{cls.PASSWORD_HASH_ALGO}$"):
            try:
                _, raw_iterations, salt_b64, dk_b64 = stored_hash.split("$", 3)
                iterations = int(raw_iterations)
                salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
                expected = base64.urlsafe_b64decode(dk_b64.encode("ascii"))
            except Exception:
                return False

            computed = hashlib.pbkdf2_hmac(
                "sha256",
                candidate_password.encode("utf-8"),
                salt,
                max(iterations, 100000),
            )
            return hmac.compare_digest(computed, expected)

        legacy_hash = hashlib.sha256(candidate_password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, stored_hash)

    @classmethod
    def _find_user_row_by_email(cls, worksheet: gspread.Worksheet, email: str) -> tuple[int | None, dict]:
        records = worksheet.get_all_records()
        normalized_email = email.strip().lower()
        for index, row in enumerate(records, start=2):
            if str(row.get("email", "")).strip().lower() == normalized_email:
                return index, row
        return None, {}

    @classmethod
    def _find_user_row_by_username(cls, worksheet: gspread.Worksheet, username: str) -> tuple[int | None, dict]:
        records = worksheet.get_all_records()
        normalized_username = username.strip().lower()
        for index, row in enumerate(records, start=2):
            if str(row.get("username", "")).strip().lower() == normalized_username:
                return index, row
        return None, {}

    @classmethod
    def _open_spreadsheet(cls) -> gspread.Spreadsheet:
        cls._ensure_credentials_file()

        if not cls.CREDENTIALS_PATH.exists():
            raise FileNotFoundError("File credentials Google tidak ditemukan di static/credentials.json")

        gc = gspread.service_account(filename=str(cls.CREDENTIALS_PATH))

        spreadsheet_id = os.getenv(cls.ENV_SPREADSHEET_ID, cls.DEFAULT_SPREADSHEET_ID).strip()
        if spreadsheet_id:
            try:
                return gc.open_by_key(spreadsheet_id)
            except gspread.SpreadsheetNotFound as exc:
                raise PermissionError(
                    "Spreadsheet tidak ditemukan / tidak bisa diakses. "
                    "Pastikan Google Sheet sudah di-share ke service account pada static/credentials.json"
                ) from exc

        spreadsheet_name = os.getenv(cls.ENV_SPREADSHEET_NAME, cls.DEFAULT_SPREADSHEET_NAME).strip()
        try:
            return gc.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            return gc.create(spreadsheet_name)

    @classmethod
    def _ensure_credentials_file(cls) -> None:
        if cls.CREDENTIALS_PATH.exists():
            return

        raw_json = os.getenv(cls.ENV_GOOGLE_SERVICE_ACCOUNT_JSON, "").strip()
        if not raw_json:
            return

        try:
            payload = json.loads(raw_json)
            serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            serialized = raw_json

        cls.CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        cls.CREDENTIALS_PATH.write_text(serialized, encoding="utf-8")

    @classmethod
    def _get_or_create_worksheet(
        cls,
        spreadsheet: gspread.Spreadsheet,
        title: str,
        headers: list[str],
    ) -> gspread.Worksheet:
        try:
            worksheet = spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=20)

        current_values = worksheet.row_values(1)
        if current_values != headers:
            worksheet.update("A1", [headers], value_input_option="USER_ENTERED")
        return worksheet
