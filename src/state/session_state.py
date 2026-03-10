from enum import Enum

import streamlit as st


class Page(str, Enum):
    HOME = "home"
    LOCKER = "locker"
    DECRYPT = "decrypt"
    COMPRESSOR = "compressor"
    CONVERTER = "converter"
    SPLIT_MERGE = "split_merge"


class SessionStateManager:
    KEY_PAGE = "page"

    @classmethod
    def ensure_defaults(cls) -> None:
        if cls.KEY_PAGE not in st.session_state:
            st.session_state[cls.KEY_PAGE] = Page.HOME.value

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
