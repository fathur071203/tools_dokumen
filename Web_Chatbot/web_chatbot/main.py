from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path
from typing import Dict

import streamlit as st

from web_chatbot.presenters.chatbot_presenter import ChatbotPresenter
from web_chatbot.services.spreadsheet_tracking_service import LoginIdentity, SpreadsheetTrackingService
from web_chatbot.state.session_state import SessionStateManager
from web_chatbot.views.chatbot_view import ChatbotView


def apply_theme() -> None:
    bg_candidates = [
        Path(__file__).resolve().parents[1] / "static" / "bg.webp",
        Path(__file__).resolve().parents[2] / "static" / "bg.webp",
        Path(__file__).resolve().parents[1] / "static" / "bg.png",
    ]
    bg_path = next((path for path in bg_candidates if path.exists()), bg_candidates[0])
    bg_data_uri = ""
    if bg_path.exists():
        mime_type = "image/webp" if bg_path.suffix.lower() == ".webp" else "image/png"
        encoded = base64.b64encode(bg_path.read_bytes()).decode("utf-8")
        bg_data_uri = f"data:{mime_type};base64,{encoded}"

    background_layer = f"url('{bg_data_uri}')" if bg_data_uri else "none"

    css_theme = """
        <style>
                    .stApp {
                        background-image: __BACKGROUND_LAYER__;
                        background-size: cover;
                        background-position: center;
                        background-attachment: fixed;
                    }

                    .main .block-container {
                        background: rgba(255, 255, 255, 0.86);
                        border: 1px solid rgba(255, 255, 255, 0.7);
                        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.16);
                        border-radius: 18px;
                        padding: 1.5rem 1.5rem 1rem 1.5rem !important;
                    }

                    div[data-testid="stForm"],
                    div[data-testid="stExpander"] {
                        background: rgba(255, 255, 255, 0.92);
                        border: 1px solid rgba(148, 163, 184, 0.28);
                        border-radius: 14px;
                        padding: 0.65rem 0.75rem;
                    }

                    div[data-testid="stButton"] > button,
                    div[data-testid="stFormSubmitButton"] > button {
                        border-radius: 12px;
                        border: 1px solid rgba(148, 163, 184, 0.4);
                        backdrop-filter: blur(2px);
                    }

                    html[data-theme="dark"] .stApp,
                    body[data-theme="dark"] .stApp {
                        background-image: __BACKGROUND_LAYER__;
                    }

                    html[data-theme="dark"] .main .block-container,
                    body[data-theme="dark"] .main .block-container {
                        background: rgba(15, 23, 42, 0.78);
                        border: 1px solid rgba(148, 163, 184, 0.24);
                    }

                    html[data-theme="dark"] div[data-testid="stForm"],
                    html[data-theme="dark"] div[data-testid="stExpander"],
                    body[data-theme="dark"] div[data-testid="stForm"],
                    body[data-theme="dark"] div[data-testid="stExpander"] {
                        background: rgba(15, 23, 42, 0.82);
                        border: 1px solid rgba(148, 163, 184, 0.32);
                    }

                    @media (prefers-color-scheme: dark) {
                        .stApp {
                            background-image: __BACKGROUND_LAYER__;
                        }

                        .main .block-container {
                            background: rgba(15, 23, 42, 0.78);
                            border: 1px solid rgba(148, 163, 184, 0.24);
                        }

                        div[data-testid="stForm"],
                        div[data-testid="stExpander"] {
                            background: rgba(15, 23, 42, 0.82);
                            border: 1px solid rgba(148, 163, 184, 0.32);
                        }
                    }
        </style>
        """

    st.markdown(
        css_theme.replace("__BACKGROUND_LAYER__", background_layer),
        unsafe_allow_html=True,
    )


class ChatbotApp:
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_LOCK_SECONDS = 10 * 60
    KEY_LOGIN_FAILED_ATTEMPTS = "chatbot_login_failed_attempts"
    KEY_LOGIN_LOCK_UNTIL = "chatbot_login_lock_until"

    def __init__(self) -> None:
        self._load_env_file()
        self._load_streamlit_secrets()
        self.chatbot_presenter = ChatbotPresenter(view=ChatbotView())

    @staticmethod
    def _load_env_file() -> None:
        env_candidates = [Path(".env"), Path(__file__).resolve().parents[1] / ".env"]
        for env_path in env_candidates:
            if not env_path.exists():
                continue
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
        try:
            secret_map = dict(st.secrets)
        except Exception:
            secret_map = {}

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
            value = secret_map.get(key)
            if value is not None and str(value).strip():
                os.environ[key] = str(value).strip()

        credentials_path = Path(__file__).resolve().parents[1] / "static" / "credentials.json"
        if credentials_path.exists():
            return

        credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        if not credentials_json:
            secret_json = secret_map.get("GOOGLE_SERVICE_ACCOUNT_JSON")
            credentials_json = str(secret_json).strip() if secret_json is not None else ""

        if isinstance(credentials_json, str) and credentials_json.strip():
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            credentials_path.write_text(credentials_json.strip(), encoding="utf-8")
            return

        gcp_sa = secret_map.get("gcp_service_account")
        if gcp_sa is not None:
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            credentials_path.write_text(json.dumps(dict(gcp_sa), ensure_ascii=False, indent=2), encoding="utf-8")

    def run(self) -> None:
        st.set_page_config(page_title="Web Chatbot Regulasi", page_icon="🤖", layout="wide")
        apply_theme()

        logo_path = Path(__file__).resolve().parents[1] / "static" / "Logo.png"
        if logo_path.exists():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(str(logo_path), use_container_width=True)

        SessionStateManager.ensure_defaults()

        if SessionStateManager.is_session_expired(15 * 60):
            SessionStateManager.expire_session("Sesi berakhir karena tidak ada aktivitas. Silakan login kembali.")

        if not SessionStateManager.is_authenticated():
            self._render_login_page()
            return

        self._render_user_session_panel()
        SessionStateManager.touch_activity()
        self.chatbot_presenter.present()

    def _render_login_page(self) -> None:
        st.markdown("## 🔒 Masuk ke Web Chatbot Regulasi")
        st.caption("Login menggunakan username dan password yang sama dengan sistem Tools Dokumen.")

        lock_active, remaining_seconds = self._is_login_temporarily_locked()
        if lock_active:
            st.error(f"⛔ Terlalu banyak percobaan login gagal. Coba lagi dalam {max(remaining_seconds // 60, 1)} menit.")

        auth_notice = SessionStateManager.consume_auth_notice()
        if auth_notice:
            st.warning(auth_notice)

        with st.form("chatbot_login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="contoh: fathur.mrhmn")
            password = st.text_input("Password User", type="password", placeholder="Masukkan password user")
            submitted = st.form_submit_button("Masuk", use_container_width=True, type="primary")

        with st.expander("➕ Registrasi user baru"):
            st.caption("User akan berstatus pending dan menunggu approval admin.")
            with st.form("chatbot_register_user_form", clear_on_submit=True):
                reg_full_name = st.text_input("Nama Lengkap User", placeholder="Contoh: Siti Aisyah")
                reg_email = st.text_input("Email User", placeholder="siti.aisyah@domain.com")
                reg_username = st.text_input("Username User", placeholder="contoh: siti.aisyah")
                reg_unit = st.text_input("Unit / Divisi User", placeholder="Contoh: Divisi Umum")
                reg_password = st.text_input("Password User", type="password", placeholder="Minimal 10 karakter")
                reg_confirm_password = st.text_input(
                    "Konfirmasi Password User", type="password", placeholder="Ulangi password user"
                )
                reg_submitted = st.form_submit_button("Daftarkan User", use_container_width=True)

            if reg_submitted:
                reg_identity = self._validate_login_identity(reg_full_name, reg_username, reg_email, reg_unit)
                if reg_identity is not None:
                    password_ok, password_message = self._validate_registration_password(reg_password, reg_confirm_password)
                    if not password_ok:
                        st.error(f"❌ {password_message}")
                        return
                    try:
                        created, message = SpreadsheetTrackingService.register_user(reg_identity, reg_password)
                        if created:
                            st.success(f"✅ {message}")
                        else:
                            st.warning(f"⚠️ {message}")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"❌ Registrasi user gagal: {exc}")

        st.info("Jika belum punya akun, daftar dulu lewat form Registrasi user baru.")

        if not submitted:
            return

        lock_active, remaining_seconds = self._is_login_temporarily_locked()
        if lock_active:
            st.error(f"⛔ Login dikunci sementara. Coba lagi dalam {max(remaining_seconds // 60, 1)} menit.")
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
            st.info("Pastikan static/credentials.json valid dan spreadsheet sudah dishare ke service account.")
            return

        if not valid or identity is None:
            self._record_login_failure()
            st.error(f"❌ {message or 'Username atau password tidak valid.'}")
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

    def _validate_login_identity(self, full_name: str, username: str, email: str, unit: str) -> LoginIdentity | None:
        clean_name = full_name.strip()
        clean_username = username.strip().lower()
        clean_email = email.strip().lower()
        clean_unit = unit.strip()

        if not clean_name:
            st.error("❌ Nama lengkap wajib diisi.")
            return None
        if not clean_username or len(clean_username) < 4:
            st.error("❌ Username minimal 4 karakter.")
            return None
        if not clean_email or "@" not in clean_email:
            st.error("❌ Email tidak valid.")
            return None
        if not clean_unit:
            st.error("❌ Unit/Divisi wajib diisi.")
            return None

        return LoginIdentity(full_name=clean_name, username=clean_username, email=clean_email, unit=clean_unit)

    def _validate_registration_password(self, password: str, confirm_password: str) -> tuple[bool, str]:
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

    def _render_user_session_panel(self) -> None:
        user = SessionStateManager.get_authenticated_user()
        with st.sidebar:
            st.markdown("### 👤 Sesi Login")
            st.caption(f"Nama: {user.get('full_name', '-')}")
            st.caption(f"Username: {user.get('username', '-')}")
            st.caption(f"Email: {user.get('email', '-')}")
            st.caption(f"Unit: {user.get('unit', '-')}")
            st.caption(f"Role: {user.get('role', 'user')}")
            st.markdown("---")
            if st.button("Logout", use_container_width=True, type="primary"):
                SessionStateManager.expire_session("Anda berhasil logout.")


def run() -> None:
    app = ChatbotApp()
    app.run()
