import time

import streamlit as st


class SessionStateManager:
    KEY_AUTHENTICATED = "chatbot_authenticated"
    KEY_LAST_ACTIVITY_AT = "chatbot_last_activity_at"
    KEY_AUTH_NOTICE = "chatbot_auth_notice"
    KEY_AUTH_USER = "chatbot_auth_user"

    @classmethod
    def ensure_defaults(cls) -> None:
        if cls.KEY_AUTHENTICATED not in st.session_state:
            st.session_state[cls.KEY_AUTHENTICATED] = False
        if cls.KEY_LAST_ACTIVITY_AT not in st.session_state:
            st.session_state[cls.KEY_LAST_ACTIVITY_AT] = None
        if cls.KEY_AUTH_NOTICE not in st.session_state:
            st.session_state[cls.KEY_AUTH_NOTICE] = ""
        if cls.KEY_AUTH_USER not in st.session_state:
            st.session_state[cls.KEY_AUTH_USER] = {}

    @classmethod
    def is_authenticated(cls) -> bool:
        cls.ensure_defaults()
        return bool(st.session_state.get(cls.KEY_AUTHENTICATED, False))

    @classmethod
    def set_authenticated(cls, value: bool, user: dict | None = None) -> None:
        cls.ensure_defaults()
        st.session_state[cls.KEY_AUTHENTICATED] = value
        st.session_state[cls.KEY_LAST_ACTIVITY_AT] = time.time() if value else None
        st.session_state[cls.KEY_AUTH_USER] = user or {}

    @classmethod
    def get_authenticated_user(cls) -> dict:
        cls.ensure_defaults()
        return dict(st.session_state.get(cls.KEY_AUTH_USER, {}) or {})

    @classmethod
    def touch_activity(cls) -> None:
        if cls.is_authenticated():
            st.session_state[cls.KEY_LAST_ACTIVITY_AT] = time.time()

    @classmethod
    def is_session_expired(cls, timeout_seconds: int) -> bool:
        cls.ensure_defaults()
        if not cls.is_authenticated():
            return False
        last_activity = st.session_state.get(cls.KEY_LAST_ACTIVITY_AT)
        if not last_activity:
            return True
        return (time.time() - float(last_activity)) > timeout_seconds

    @classmethod
    def expire_session(cls, notice: str | None = None) -> None:
        cls.clear_transient_state()
        st.session_state[cls.KEY_AUTHENTICATED] = False
        st.session_state[cls.KEY_LAST_ACTIVITY_AT] = None
        st.session_state[cls.KEY_AUTH_NOTICE] = notice or ""
        st.session_state[cls.KEY_AUTH_USER] = {}
        st.rerun()

    @classmethod
    def consume_auth_notice(cls) -> str:
        cls.ensure_defaults()
        notice = str(st.session_state.get(cls.KEY_AUTH_NOTICE, "") or "")
        st.session_state[cls.KEY_AUTH_NOTICE] = ""
        return notice

    @classmethod
    def clear_transient_state(cls) -> None:
        cls.ensure_defaults()
        preserved_keys = {
            cls.KEY_AUTHENTICATED,
            cls.KEY_LAST_ACTIVITY_AT,
            cls.KEY_AUTH_NOTICE,
            cls.KEY_AUTH_USER,
        }
        for key in list(st.session_state.keys()):
            if key not in preserved_keys and not str(key).startswith("chatbot_"):
                del st.session_state[key]
