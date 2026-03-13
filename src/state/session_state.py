from enum import Enum
import time

import streamlit as st


class Page(str, Enum):
    HOME = "home"
    LOCKER = "locker"
    DECRYPT = "decrypt"
    COMPRESSOR = "compressor"
    CONVERTER = "converter"
    WATERMARK = "watermark"
    SPLIT_MERGE = "split_merge"


class SessionStateManager:
    KEY_PAGE = "page"
    KEY_AUTHENTICATED = "authenticated"
    KEY_LAST_ACTIVITY_AT = "last_activity_at"
    KEY_AUTH_NOTICE = "auth_notice"

    @classmethod
    def ensure_defaults(cls) -> None:
        if cls.KEY_PAGE not in st.session_state:
            st.session_state[cls.KEY_PAGE] = Page.HOME.value
        if cls.KEY_AUTHENTICATED not in st.session_state:
            st.session_state[cls.KEY_AUTHENTICATED] = False
        if cls.KEY_LAST_ACTIVITY_AT not in st.session_state:
            st.session_state[cls.KEY_LAST_ACTIVITY_AT] = None
        if cls.KEY_AUTH_NOTICE not in st.session_state:
            st.session_state[cls.KEY_AUTH_NOTICE] = ""

    @classmethod
    def get_page(cls) -> Page:
        cls.ensure_defaults()
        raw = st.session_state.get(cls.KEY_PAGE, Page.HOME.value)
        try:
            return Page(raw)
        except ValueError:
            return Page.HOME

    @classmethod
    def go(cls, page: Page) -> None:
        st.session_state[cls.KEY_PAGE] = page.value
        st.rerun()

    @classmethod
    def is_authenticated(cls) -> bool:
        cls.ensure_defaults()
        return bool(st.session_state.get(cls.KEY_AUTHENTICATED, False))

    @classmethod
    def set_authenticated(cls, value: bool) -> None:
        st.session_state[cls.KEY_AUTHENTICATED] = value
        st.session_state[cls.KEY_LAST_ACTIVITY_AT] = time.time() if value else None

    @classmethod
    def logout(cls) -> None:
        cls.expire_session()

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
        st.session_state[cls.KEY_PAGE] = Page.HOME.value
        st.session_state[cls.KEY_AUTHENTICATED] = False
        st.session_state[cls.KEY_LAST_ACTIVITY_AT] = None
        st.session_state[cls.KEY_AUTH_NOTICE] = notice or ""
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
            cls.KEY_PAGE,
            cls.KEY_AUTHENTICATED,
            cls.KEY_LAST_ACTIVITY_AT,
            cls.KEY_AUTH_NOTICE,
        }
        for key in list(st.session_state.keys()):
            if key not in preserved_keys:
                del st.session_state[key]
