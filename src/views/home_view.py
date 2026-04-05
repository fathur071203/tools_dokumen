import base64
from dataclasses import dataclass
from pathlib import Path

import streamlit as st


@dataclass
class HomeViewResult:
    open_approval: bool
    open_locker: bool
    open_compressor: bool
    open_converter: bool
    open_watermark: bool
    open_split_merge: bool


class HomeView:
    def render(self, is_admin: bool, pending_count: int) -> HomeViewResult:
        bg_path = Path(__file__).resolve().parents[2] / "static" / "bg.webp"
        if not bg_path.exists():
            bg_path = Path(__file__).resolve().parents[2] / "static" / "bg.png"

        background_css = ""
        if bg_path.exists():
            mime_type = "image/webp" if bg_path.suffix.lower() == ".webp" else "image/png"
            encoded = base64.b64encode(bg_path.read_bytes()).decode("utf-8")
            background_css = f"background-image: url('data:{mime_type};base64,{encoded}') !important;"

        st.markdown(
            f"""
            <style>
            .stApp {{
                background-size: cover !important;
                background-position: center !important;
                background-attachment: fixed !important;
                {background_css}
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="td-page-intro-card">
                <p class="td-feature-title">🛠️ Kumpulan Tools Dokumen</p>
                <p class="td-feature-desc">Dashboard modular untuk proses enkripsi, kompresi, konversi, watermark, serta split &amp; merge dokumen.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Search box untuk filter tools
        search_query = st.text_input(
            "🔍 Cari tool",
            placeholder="Ketik nama atau deskripsi tool...",
            key="search_tools",
        ).strip().lower()

        cards: list[dict[str, str]] = [
            {
                "id": "locker",
                "icon": "🔐",
                "title": "File Locker",
                "desc": "Enkripsi/dekripsi file dengan password.",
            },
            {
                "id": "compressor",
                "icon": "📦",
                "title": "Kompresi File (Beta)",
                "desc": "[Beta] Kompres file jadi ZIP lebih ringkas.",
            },
            {
                "id": "converter",
                "icon": "🔄",
                "title": "Konversi Dokumen (Beta)",
                "desc": "[Beta] Konversi PDF, Office, dan gambar.",
            },
            {
                "id": "watermark",
                "icon": "💧",
                "title": "Watermark PDF",
                "desc": "Tambahkan watermark teks/gambar.",
            },
            {
                "id": "split_merge",
                "icon": "🪄",
                "title": "Split & Gabung",
                "desc": "Pisahkan atau gabungkan dokumen.",
            },
        ]

        if is_admin:
            cards.insert(
                0,
                {
                    "id": "approval",
                    "icon": "✅",
                    "title": "Approval Registrasi",
                    "desc": f"Pending saat ini: {pending_count} user.",
                },
            )

        # Filter cards berdasarkan search query
        filtered_cards = cards
        if search_query:
            filtered_cards = [
                card
                for card in cards
                if search_query in card["title"].lower()
                or search_query in card["desc"].lower()
            ]

        # Tampilkan hasil search
        if search_query:
            st.caption(f"📊 Ditemukan {len(filtered_cards)} tool")
            if not filtered_cards:
                st.warning("Tidak ada tool yang cocok dengan pencarian Anda.")
                return HomeViewResult(
                    open_approval=False,
                    open_locker=False,
                    open_compressor=False,
                    open_converter=False,
                    open_watermark=False,
                    open_split_merge=False,
                )

        clicked: dict[str, bool] = {item["id"]: False for item in cards}
        for start in range(0, len(filtered_cards), 4):
            cols = st.columns(4)
            row_cards = filtered_cards[start : start + 4]
            for col, card in zip(cols, row_cards):
                with col:
                    # Custom HTML card yang clickable
                    st.markdown(
                        f"""
                        <div class="td-nav-card-clickable" data-id="{card['id']}">
                            <div class="td-nav-icon">{card['icon']}</div>
                            <div class="td-nav-title">{card['title']}</div>
                            <div class="td-nav-desc">{card['desc']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    clicked[card["id"]] = st.button(
                        f"Buka {card['title']}",
                        use_container_width=True,
                        type="primary",
                        key=f"btn_nav_{card['id']}",
                    )

        return HomeViewResult(
            open_approval=clicked.get("approval", False),
            open_locker=clicked.get("locker", False),
            open_compressor=clicked.get("compressor", False),
            open_converter=clicked.get("converter", False),
            open_watermark=clicked.get("watermark", False),
            open_split_merge=clicked.get("split_merge", False),
        )
