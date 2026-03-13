import streamlit as st
from pathlib import Path

from src.models.file_locker_model import FileLockerModel
from src.presenters.file_locker_presenter import FileLockerPresenter
from src.presenters.file_compressor_presenter import FileCompressorPresenter
from src.presenters.file_converter_presenter import FileConverterPresenter
from src.presenters.file_watermark_presenter import FileWatermarkPresenter
from src.presenters.file_split_merge_presenter import FileSplitMergePresenter
from src.presenters.home_presenter import HomePresenter
from src.services.auth_service import AuthService
from src.services.crypto_service import CryptoService
from src.state.session_state import Page, SessionStateManager
from src.styles.theme import apply_custom_theme
from src.views.file_locker_decrypt_view import FileLockerDecryptView
from src.views.file_locker_encrypt_view import FileLockerEncryptView
from src.views.file_compressor_view import FileCompressorView
from src.views.file_converter_view import FileConverterView
from src.views.file_watermark_view import FileWatermarkView
from src.views.file_split_merge_view import FileSplitMergeView
from src.views.home_view import HomeView


class App:
    def __init__(self):
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

    def run(self) -> None:
        st.set_page_config(
            page_title="Tools Dokumen — Streamlit",
            page_icon="🛠️",
            layout="wide",
        )

        apply_custom_theme()
        
        # Display logo if available
        logo_path = Path("static/Logo.png")
        if logo_path.exists():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(str(logo_path), use_container_width=True)
        SessionStateManager.ensure_defaults()

        if SessionStateManager.is_session_expired(AuthService.get_session_timeout_seconds()):
            SessionStateManager.expire_session("Sesi berakhir karena tidak ada aktivitas. Silakan login kembali.")

        if not SessionStateManager.is_authenticated():
            self._render_login_page()
            return

        SessionStateManager.touch_activity()

        page = SessionStateManager.get_page()
        if page == Page.HOME:
            self.home_presenter.present()
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
        st.markdown("## 🔒 Masuk ke Tools Dokumen")
        st.caption("Masukkan password untuk mengakses seluruh fitur di aplikasi ini. Upload diproses di memori dan state sensitif akan dibersihkan saat sesi berakhir.")

        auth_notice = SessionStateManager.consume_auth_notice()
        if auth_notice:
            st.warning(auth_notice)

        with st.form("login_form", clear_on_submit=False):
            password = st.text_input("Password", type="password", placeholder="Masukkan password")
            submitted = st.form_submit_button("Masuk", use_container_width=True, type="primary")

        if AuthService.is_default_password_in_use():
            st.warning(
                "Aplikasi masih memakai password default. Demi keamanan, ganti segera lewat environment variable "
                "`TOOLS_DOKUMEN_PASSWORD` atau `app_password` di Streamlit secrets."
            )
        else:
            st.info(
                "Gunakan `TOOLS_DOKUMEN_PASSWORD` atau `app_password` di Streamlit secrets untuk mengelola password aplikasi."
            )

        if submitted:
            if AuthService.verify_password(password):
                SessionStateManager.set_authenticated(True)
                st.success("✅ Login berhasil.")
                st.rerun()
            else:
                st.error("❌ Password salah.")


def run() -> None:
    app = App()
    app.run()
