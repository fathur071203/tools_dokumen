from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass
class ApprovalViewResult:
    go_home: bool
    refresh_clicked: bool
    action: dict[str, Any] | None


class ApprovalView:
    @staticmethod
    def _render_page_styles() -> None:
        st.markdown(
            """
            <style>
            .stApp {
                background-color: #ffffff !important;
                background-image:
                    radial-gradient(circle at 10% 92%, rgba(37, 99, 235, 0.13) 0%, rgba(37, 99, 235, 0.07) 24%, rgba(37, 99, 235, 0.00) 52%),
                    radial-gradient(circle at 92% 88%, rgba(37, 99, 235, 0.20) 0%, rgba(37, 99, 235, 0.11) 24%, rgba(37, 99, 235, 0.00) 56%) !important;
                background-repeat: no-repeat !important;
                background-attachment: fixed !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: #ffffff !important;
                border-radius: 18px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0px 12px 35px rgba(0, 0, 0, 0.18) !important;
                padding: 20px !important;
                margin-bottom: 20px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def render(
        self,
        pending_users: list[dict[str, Any]],
        load_error: str,
    ) -> ApprovalViewResult:
        self._render_page_styles()

        st.markdown(
            """
            <div class="td-page-intro-card">
                <p class="td-feature-title">✅ Approval Registrasi User</p>
                <p class="td-feature-desc">Halaman admin untuk approve/reject user baru yang melakukan registrasi.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            col_left, col_right = st.columns([1, 1])
            with col_left:
                go_home = st.button("← Kembali", use_container_width=True, key="btn_home_approval")
            with col_right:
                refresh_clicked = st.button("🔄 Refresh Data", use_container_width=True, key="btn_refresh_approval")

        if load_error:
            st.error(f"❌ Gagal memuat data pending: {load_error}")

        st.markdown(f"**Total pending:** {len(pending_users)} user")

        action: dict[str, Any] | None = None

        if not pending_users:
            st.info("Belum ada user dengan status pending approval.")
            return ApprovalViewResult(
                go_home=go_home,
                refresh_clicked=refresh_clicked,
                action=None,
            )

        for idx, user in enumerate(pending_users, start=1):
            username = str(user.get("username", "") or "").strip().lower()
            full_name = str(user.get("full_name", "") or "-")
            email = str(user.get("email", "") or "-")
            unit = str(user.get("unit", "") or "-")
            registered_at = str(user.get("registered_at", "") or "-")

            with st.expander(f"[{idx}] {full_name} ({username})", expanded=False):
                st.markdown(f"**Nama:** {full_name}")
                st.markdown(f"**Username:** {username}")
                st.markdown(f"**Email:** {email}")
                st.markdown(f"**Unit:** {unit}")
                st.caption(f"Registrasi: {registered_at}")

                col_approve, col_reject = st.columns([1, 1])
                with col_approve:
                    approve_clicked = st.button(
                        "✅ Approve",
                        use_container_width=True,
                        key=f"approve_user_{username}",
                    )
                with col_reject:
                    reject_clicked = st.button(
                        "⛔ Reject",
                        use_container_width=True,
                        key=f"reject_user_{username}",
                    )

                if approve_clicked:
                    action = {"username": username, "approve": True}
                if reject_clicked:
                    action = {"username": username, "approve": False}

        return ApprovalViewResult(
            go_home=go_home,
            refresh_clicked=refresh_clicked,
            action=action,
        )
