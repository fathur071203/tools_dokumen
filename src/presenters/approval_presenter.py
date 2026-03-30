from __future__ import annotations

import streamlit as st

from src.services.spreadsheet_tracking_service import SpreadsheetTrackingService
from src.state.session_state import Page, SessionStateManager
from src.views.approval_view import ApprovalView


class ApprovalPresenter:
    KEY_FORCE_REFRESH = "approval_force_refresh"

    def __init__(self, view: ApprovalView):
        self.view = view

    def present(self) -> None:
        user = SessionStateManager.get_authenticated_user()
        admin_username = str(user.get("username", "") or "").strip().lower()
        role = str(user.get("role", "") or "").strip().lower()
        is_admin = role == SpreadsheetTrackingService.USER_ROLE_ADMIN or SpreadsheetTrackingService.is_admin_username(
            admin_username
        )

        if not is_admin:
            st.error("❌ Hanya admin yang dapat mengakses halaman approval.")
            if st.button("← Kembali ke Beranda", key="btn_back_home_from_approval_denied"):
                SessionStateManager.go(Page.HOME)
            return

        force_refresh = bool(st.session_state.get(self.KEY_FORCE_REFRESH, False))
        if force_refresh:
            st.session_state[self.KEY_FORCE_REFRESH] = False

        try:
            pending_users = SpreadsheetTrackingService.list_pending_users(force_refresh=force_refresh)
            load_error = ""
        except Exception as exc:  # noqa: BLE001
            pending_users = []
            load_error = str(exc)

        result = self.view.render(
            pending_users=pending_users,
            load_error=load_error,
        )

        if result.go_home:
            SessionStateManager.go(Page.HOME)

        if result.refresh_clicked:
            st.session_state[self.KEY_FORCE_REFRESH] = True
            st.rerun()

        if not result.action:
            return

        username = result.action.get("username", "").strip().lower()
        approve = bool(result.action.get("approve", False))
        if not username:
            st.warning("⚠️ Username target approval tidak valid.")
            return

        try:
            ok, message = SpreadsheetTrackingService.decide_user_approval(
                username=username,
                approve=approve,
                admin_username=admin_username,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"❌ Gagal memproses approval: {exc}")
            return

        if ok:
            st.success(f"✅ {message}")
        else:
            st.warning(f"⚠️ {message}")
        st.rerun()
