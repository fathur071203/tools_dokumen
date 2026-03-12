from __future__ import annotations

import hmac
import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


class AuthService:
    DEFAULT_PASSWORD = "dokumen123"
    ENV_PASSWORD_KEY = "TOOLS_DOKUMEN_PASSWORD"
    SECRET_PASSWORD_KEY = "app_password"

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