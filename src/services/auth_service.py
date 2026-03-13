from __future__ import annotations

import hmac
import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


class AuthService:
    DEFAULT_PASSWORD = "dokumen123"
    ENV_PASSWORD_KEY = "TOOLS_DOKUMEN_PASSWORD"
    SECRET_PASSWORD_KEY = "app_password"
    SESSION_TIMEOUT_MINUTES = 15
    ENV_SESSION_TIMEOUT_KEY = "TOOLS_DOKUMEN_SESSION_TIMEOUT_MINUTES"

    @classmethod
    def get_configured_password(cls) -> str:
        try:
            secret_password = st.secrets.get(cls.SECRET_PASSWORD_KEY)
        except StreamlitSecretNotFoundError:
            secret_password = None
        if secret_password:
            return str(secret_password)

        env_password = os.getenv(cls.ENV_PASSWORD_KEY)
        if env_password:
            return env_password

        return cls.DEFAULT_PASSWORD

    @classmethod
    def verify_password(cls, candidate: str) -> bool:
        configured_password = cls.get_configured_password()
        return hmac.compare_digest(candidate, configured_password)

    @classmethod
    def is_default_password_in_use(cls) -> bool:
        return cls.get_configured_password() == cls.DEFAULT_PASSWORD

    @classmethod
    def get_session_timeout_seconds(cls) -> int:
        raw_value = os.getenv(cls.ENV_SESSION_TIMEOUT_KEY, str(cls.SESSION_TIMEOUT_MINUTES))
        try:
            minutes = max(int(raw_value), 1)
        except ValueError:
            minutes = cls.SESSION_TIMEOUT_MINUTES
        return minutes * 60