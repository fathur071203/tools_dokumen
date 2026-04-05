import base64

import streamlit as st
from pathlib import Path
from typing import Dict
import json
import os
import re
import time

from src.models.file_locker_model import FileLockerModel
from src.presenters.file_locker_presenter import FileLockerPresenter
from src.presenters.file_compressor_presenter import FileCompressorPresenter
from src.presenters.file_converter_presenter import FileConverterPresenter
from src.presenters.file_watermark_presenter import FileWatermarkPresenter
from src.presenters.file_split_merge_presenter import FileSplitMergePresenter
from src.presenters.home_presenter import HomePresenter
from src.presenters.approval_presenter import ApprovalPresenter
from src.services.crypto_service import CryptoService
from src.services.spreadsheet_tracking_service import (
    LoginIdentity,
    SpreadsheetTrackingService,
)
from src.state.session_state import Page, SessionStateManager
from src.styles.theme import apply_custom_theme
from src.views.file_locker_decrypt_view import FileLockerDecryptView
from src.views.file_locker_encrypt_view import FileLockerEncryptView
from src.views.file_compressor_view import FileCompressorView
from src.views.file_converter_view import FileConverterView
from src.views.file_watermark_view import FileWatermarkView
from src.views.file_split_merge_view import FileSplitMergeView
from src.views.home_view import HomeView
from src.views.approval_view import ApprovalView


class App:
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_LOCK_SECONDS = 10 * 60
    KEY_LOGIN_FAILED_ATTEMPTS = "login_failed_attempts"
    KEY_LOGIN_LOCK_UNTIL = "login_lock_until"

    def __init__(self):
        self._load_env_file(Path(".env"))
        self._load_streamlit_secrets()

        crypto_service = CryptoService()
        locker_model = FileLockerModel(crypto_service=crypto_service)

        self.home_presenter = HomePresenter(view=HomeView())
        self.file_locker_presenter = FileLockerPresenter(
            model=locker_model,
            encrypt_view=FileLockerEncryptView(),
            decrypt_view=FileLockerDecryptView(),
        )
        self.file_compressor_presenter = FileCompressorPresenter(
            view=FileCompressorView()
        )
        self.file_converter_presenter = FileConverterPresenter(
            view=FileConverterView()
        )
        self.file_watermark_presenter = FileWatermarkPresenter(
            view=FileWatermarkView()
        )
        self.file_split_merge_presenter = FileSplitMergePresenter(
            view=FileSplitMergeView()
        )
        self.approval_presenter = ApprovalPresenter(
            view=ApprovalView()
        )

    @staticmethod
    def _load_env_file(env_path: Path) -> None:
        if not env_path.exists():
            return

        for line in env_path.read_text(encoding="utf-8").splitlines():
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
                continue

            key, raw_value = clean_line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue

            value = raw_value.strip().strip('"').strip("'")
            os.environ[key] = value

    @staticmethod
    def _load_streamlit_secrets() -> None:
        def _get_secret_value(key: str):
            try:
                return st.secrets.get(key)
            except Exception:
                return None

        env_keys = [
            "GEMINI_API_KEY",
            "GEMINI_CHAT_MODEL",
            "GEMINI_EMBEDDING_MODEL",
            "TOOLS_DOKUMEN_SPREADSHEET_ID",
            "TOOLS_DOKUMEN_SPREADSHEET_NAME",
            "TOOLS_DOKUMEN_ADMIN_USERNAMES",
            "TOOLS_DOKUMEN_DLP_ENABLED",
            "GOOGLE_SERVICE_ACCOUNT_JSON",
        ]

        for key in env_keys:
            if key in os.environ:
                continue
            value = _get_secret_value(key)
            if value is not None and str(value).strip():
                os.environ[key] = str(value).strip()

        credentials_path = Path("static") / "credentials.json"
        if credentials_path.exists():
            return

        credentials_json = _get_secret_value("GOOGLE_SERVICE_ACCOUNT_JSON")
        if isinstance(credentials_json, str) and credentials_json.strip():
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            credentials_path.write_text(credentials_json.strip(), encoding="utf-8")
            return

        gcp_sa = _get_secret_value("gcp_service_account")
        if gcp_sa is not None:
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            credentials_path.write_text(
                json.dumps(dict(gcp_sa), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def run(self) -> None:
        st.set_page_config(
            page_title="Tools Dokumen — Streamlit",
            page_icon="🛠️",
            layout="wide",
        )

        apply_custom_theme()

        SessionStateManager.ensure_defaults()

        if SessionStateManager.is_session_expired(15 * 60):
            SessionStateManager.expire_session("Sesi berakhir karena tidak ada aktivitas. Silakan login kembali.")

        if not SessionStateManager.is_authenticated():
            self._render_login_page()
            return

        self._render_user_session_panel()
        SessionStateManager.touch_activity()

        page = SessionStateManager.get_page()
        if page == Page.HOME:
            self.home_presenter.present(
                is_admin=self._is_current_user_admin(),
                pending_count=self._get_pending_count_safe(),
            )
        elif page == Page.APPROVAL:
            self.approval_presenter.present()
        elif page == Page.LOCKER:
            self.file_locker_presenter.present_encrypt_page()
        elif page == Page.DECRYPT:
            self.file_locker_presenter.present_decrypt_page()
        elif page == Page.COMPRESSOR:
            self.file_compressor_presenter.present()
        elif page == Page.CONVERTER:
            self.file_converter_presenter.present()
        elif page == Page.WATERMARK:
            self.file_watermark_presenter.present()
        elif page == Page.SPLIT_MERGE:
            self.file_split_merge_presenter.present()
        else:
            self.home_presenter.present()

    def _render_login_page(self) -> None:
        # Apply minimal styling - card removed, low-opacity background
        bg_path = Path(__file__).resolve().parents[2] / "static" / "bg.webp"
        if not bg_path.exists():
            bg_path = Path(__file__).resolve().parents[2] / "static" / "bg.png"

        background_css = ""
        if bg_path.exists():
            mime_type = "image/webp" if bg_path.suffix.lower() == ".webp" else "image/png"
            encoded = base64.b64encode(bg_path.read_bytes()).decode("utf-8")
            background_css = f"background-image: url('data:{mime_type};base64,{encoded}') !important;"

        logo_html = ""
        logo_path = Path("static/BI_Logo.png")
        if not logo_path.exists():
            logo_path = Path("static/Logo.png")
        if logo_path.exists():
            logo_mime = "image/png" if logo_path.suffix.lower() == ".png" else "image/webp"
            logo_encoded = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
            logo_html = (
                "<div class='login-logo-wrap'>"
                f"<img class='login-logo' src='data:{logo_mime};base64,{logo_encoded}' alt='BI Logo' />"
                "</div>"
            )

        st.markdown(
            """
            <style>
            /* Login background: plain white only */
            .stApp {
                background-color: #ffffff !important;
                background-image: none !important;
            }

            h2 {
                color: #1f4e79 !important;
                margin-top: 0 !important;
                margin-bottom: 12px !important;
                font-size: 1.8rem !important;
                text-align: center !important;
                font-weight: 700 !important;
                background: none !important;
            }

            .login-subtitle {
                text-align: center !important;
                color: #475569 !important;
                font-size: 0.9rem !important;
                margin-bottom: 28px !important;
                line-height: 1.4 !important;
                background: none !important;
            }

            .login-logo-wrap {
                display: flex;
                justify-content: center;
                align-items: center;
                margin-bottom: 10px;
            }

            .login-logo {
                width: clamp(120px, 24vw, 260px);
                max-width: 80%;
                height: auto;
                object-fit: contain;
            }

            @media (max-width: 640px) {
                .login-logo {
                    width: clamp(120px, 42vw, 220px);
                    max-width: 92%;
                }
            }

            /* Input field styling - fokus banget */
            input {
                border-radius: 10px !important;
                border: 1.5px solid #dbe4ec !important;
                padding: 11px 14px !important;
                font-size: 0.9rem !important;
                background: white !important;
                color: #0f172a !important;
                transition: all 0.2s ease !important;
            }

            input::placeholder {
                color: #94a3b8 !important;
            }

            input:focus {
                border-color: #2bb3c0 !important;
                box-shadow: 0 0 0 4px rgba(43, 179, 192, 0.2) !important;
                outline: none !important;
            }

            /* Expander styling */
            [data-testid="stExpander"] {
                border: 1px solid #e2e8f0 !important;
                border-radius: 10px !important;
                background: rgba(245, 247, 250, 0.5) !important;
            }

            /* Dark mode support */
            html[data-theme="dark"] h2,
            body[data-theme="dark"] h2 {
                color: #e0f2fe !important;
            }

            html[data-theme="dark"] .login-subtitle,
            body[data-theme="dark"] .login-subtitle {
                color: #cbd5e1 !important;
            }

            html[data-theme="dark"] input,
            body[data-theme="dark"] input {
                background: #0f172a !important;
                color: #e0f2fe !important;
                border-color: #475569 !important;
            }

            html[data-theme="dark"] input::placeholder,
            body[data-theme="dark"] input::placeholder {
                color: #94a3b8 !important;
            }

            html[data-theme="dark"] input:focus,
            body[data-theme="dark"] input:focus {
                border-color: #2bb3c0 !important;
                box-shadow: 0 0 0 4px rgba(43, 179, 192, 0.25) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Center layout using Streamlit columns
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            if logo_html:
                st.markdown(logo_html, unsafe_allow_html=True)

            st.markdown("## 🔐 Masuk ke Tools Dokumen")
            st.markdown(
                '<p class="login-subtitle">Login menggunakan username dan password user masing-masing.</p>',
                unsafe_allow_html=True,
            )

            lock_active, remaining_seconds = self._is_login_temporarily_locked()
            if lock_active:
                st.error(
                    f"⛔ Terlalu banyak percobaan login gagal. Coba lagi dalam {max(remaining_seconds // 60, 1)} menit."
                )

            auth_notice = SessionStateManager.consume_auth_notice()
            if auth_notice:
                st.warning(auth_notice)

            # LOGIN FORM
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="contoh: fathur.mrhmn")
                password = st.text_input("Password", type="password", placeholder="Masukkan password")
                submitted = st.form_submit_button("Masuk", use_container_width=True)

            # REGISTRASI SECTION
            with st.expander("➕ Registrasi user baru"):
                st.caption("Gunakan form ini untuk menambahkan user baru ke daftar spreadsheet.")
                with st.form("register_user_form", clear_on_submit=True):
                    reg_full_name = st.text_input(
                        "Nama Lengkap User",
                        placeholder="Contoh: Siti Aisyah",
                    )
                    reg_email = st.text_input(
                        "Email User",
                        placeholder="siti.aisyah@domain.com",
                    )
                    reg_username = st.text_input(
                        "Username User",
                        placeholder="contoh: siti.aisyah",
                    )
                    reg_unit = st.text_input(
                        "Unit / Divisi User",
                        placeholder="Contoh: Divisi Umum",
                    )
                    reg_password = st.text_input(
                        "Password User",
                        type="password",
                        placeholder="Minimal 8 karakter",
                    )
                    reg_confirm_password = st.text_input(
                        "Konfirmasi Password User",
                        type="password",
                        placeholder="Ulangi password user",
                    )
                    reg_submitted = st.form_submit_button(
                        "Daftarkan User",
                        use_container_width=True,
                    )

                if reg_submitted:
                    reg_identity = self._validate_login_identity(
                        full_name=reg_full_name,
                        username=reg_username,
                        email=reg_email,
                        unit=reg_unit,
                    )
                    if reg_identity is not None:
                        password_ok, password_message = self._validate_registration_password(
                            password=reg_password,
                            confirm_password=reg_confirm_password,
                        )
                        if not password_ok:
                            st.error(f"❌ {password_message}")
                            return

                        try:
                            created, register_message = SpreadsheetTrackingService.register_user(
                                reg_identity,
                                reg_password,
                            )
                            if created:
                                st.success(f"✅ {register_message}")
                            else:
                                st.warning(f"⚠️ {register_message}")
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"❌ Registrasi user gagal: {exc}")

        if submitted:
            lock_active, remaining_seconds = self._is_login_temporarily_locked()
            if lock_active:
                st.error(
                    f"⛔ Login dikunci sementara. Coba lagi dalam {max(remaining_seconds // 60, 1)} menit."
                )
                return

            clean_username = username.strip().lower()
            if not clean_username:
                st.error("❌ Username wajib diisi.")
                return
            if not password:
                st.error("❌ Password wajib diisi.")
                return

            try:
                valid, message, identity = SpreadsheetTrackingService.verify_user_credentials(
                    username=clean_username,
                    password=password,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"❌ Gagal akses spreadsheet: {exc}")
                st.info(
                    "Pastikan `static/credentials.json` valid dan spreadsheet sudah dishare ke service account."
                )
                return

            if not valid or identity is None:
                self._record_login_failure()
                st.error("❌ Username atau password tidak valid.")
                return

            self._clear_login_failures()

            sync_ok, sync_message = self._sync_user_to_spreadsheet(identity)
            SessionStateManager.set_authenticated(True, user=self._identity_to_user_dict(identity))
            if sync_ok:
                st.success("✅ Login berhasil.")
            else:
                st.success("✅ Login berhasil.")
                st.warning(f"Tracking spreadsheet belum tersimpan: {sync_message}")
            st.rerun()

    def _validate_login_identity(
        self,
        full_name: str,
        username: str,
        email: str,
        unit: str,
    ) -> LoginIdentity | None:
        clean_name = full_name.strip()
        clean_username = username.strip().lower()
        clean_email = email.strip().lower()
        clean_unit = unit.strip()

        if not clean_name:
            st.error("❌ Nama lengkap wajib diisi.")
            return None
        if not clean_username:
            st.error("❌ Username wajib diisi.")
            return None
        if len(clean_username) < 4:
            st.error("❌ Username minimal 4 karakter.")
            return None
        if not clean_email or "@" not in clean_email:
            st.error("❌ Email tidak valid.")
            return None
        if not clean_unit:
            st.error("❌ Unit/Divisi wajib diisi.")
            return None

        return LoginIdentity(
            full_name=clean_name,
            username=clean_username,
            email=clean_email,
            unit=clean_unit,
        )

    def _validate_registration_password(
        self,
        password: str,
        confirm_password: str,
    ) -> tuple[bool, str]:
        if len(password) < 10:
            return False, "Password minimal 10 karakter."
        if not re.search(r"[A-Z]", password):
            return False, "Password wajib mengandung minimal 1 huruf besar."
        if not re.search(r"[a-z]", password):
            return False, "Password wajib mengandung minimal 1 huruf kecil."
        if not re.search(r"\d", password):
            return False, "Password wajib mengandung minimal 1 angka."
        if not re.search(r"[^A-Za-z0-9]", password):
            return False, "Password wajib mengandung minimal 1 karakter khusus."
        if password != confirm_password:
            return False, "Konfirmasi password tidak sama."
        return True, "OK"

    def _is_login_temporarily_locked(self) -> tuple[bool, int]:
        lock_until = float(st.session_state.get(self.KEY_LOGIN_LOCK_UNTIL, 0) or 0)
        now = time.time()
        if lock_until > now:
            return True, int(lock_until - now)
        return False, 0

    def _record_login_failure(self) -> None:
        attempts = int(st.session_state.get(self.KEY_LOGIN_FAILED_ATTEMPTS, 0) or 0) + 1
        st.session_state[self.KEY_LOGIN_FAILED_ATTEMPTS] = attempts
        if attempts >= self.LOGIN_MAX_ATTEMPTS:
            st.session_state[self.KEY_LOGIN_LOCK_UNTIL] = time.time() + self.LOGIN_LOCK_SECONDS
            st.session_state[self.KEY_LOGIN_FAILED_ATTEMPTS] = 0

    def _clear_login_failures(self) -> None:
        st.session_state[self.KEY_LOGIN_FAILED_ATTEMPTS] = 0
        st.session_state[self.KEY_LOGIN_LOCK_UNTIL] = 0

    def _sync_user_to_spreadsheet(self, identity: LoginIdentity) -> tuple[bool, str]:
        try:
            return SpreadsheetTrackingService.register_and_log_login(identity)
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _identity_to_user_dict(self, identity: LoginIdentity) -> Dict[str, str]:
        return {
            "full_name": identity.full_name,
            "username": identity.username,
            "email": identity.email,
            "unit": identity.unit,
            "role": identity.role,
        }

    def _is_current_user_admin(self) -> bool:
        user = SessionStateManager.get_authenticated_user()
        username = str(user.get("username", "") or "").strip().lower()
        role = str(user.get("role", "") or "").strip().lower()
        return role == SpreadsheetTrackingService.USER_ROLE_ADMIN or SpreadsheetTrackingService.is_admin_username(
            username
        )

    def _get_pending_count_safe(self) -> int:
        if not self._is_current_user_admin():
            return 0
        try:
            return len(SpreadsheetTrackingService.list_pending_users())
        except Exception:
            return 0

    def _render_user_session_panel(self) -> None:
        user = SessionStateManager.get_authenticated_user()
        is_admin = self._is_current_user_admin()
        role = str(user.get("role", "") or "").strip().lower() or "user"

        with st.sidebar:
            st.markdown("### 👤 Sesi Login")
            st.caption(f"Nama: {user.get('full_name', '-')}")
            st.caption(f"Username: {user.get('username', '-')}")
            st.caption(f"Email: {user.get('email', '-')}")
            st.caption(f"Unit: {user.get('unit', '-')}")
            st.caption(f"Role: {role}")

            if is_admin:
                pending_count = self._get_pending_count_safe()
                st.markdown("---")
                st.markdown("### ✅ Admin")
                st.caption(f"Pending approval: {pending_count}")
                if st.button("Buka Approval User", use_container_width=True, key="btn_sidebar_approval"):
                    SessionStateManager.go(Page.APPROVAL)

            st.markdown("---")
            if st.button("Logout", use_container_width=True, type="primary"):
                SessionStateManager.expire_session("Anda berhasil logout.")


def run() -> None:
    app = App()
    app.run()
