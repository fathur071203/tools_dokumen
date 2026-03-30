from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass
class ChatbotViewResult:
    go_home: bool
    clear_chat: bool
    ask_clicked: bool
    question: str
    selected_categories: list[str]
    top_k: int


class ChatbotView:
    def render(
        self,
        messages: list[dict[str, Any]],
        categories: list[str],
        category_chunk_counts: dict[str, int],
        total_context_count: int,
        is_configured: bool,
        config_message: str,
    ) -> ChatbotViewResult:
        st.markdown("## 🤖 Chatbot Peraturan")
        st.caption("Aplikasi chatbot terpisah untuk tanya jawab regulasi.")

        col_left, col_right = st.columns([1, 1])
        with col_left:
            go_home = st.button("↩️ Kembali ke Login", use_container_width=True, key="btn_home_chatbot")
        with col_right:
            clear_chat = st.button("🧹 Reset Chat", use_container_width=True)

        if not is_configured:
            st.error(f"❌ {config_message}")

        selected_categories: list[str] = []
        top_k = 6

        with st.expander("Opsi Lanjutan (Opsional)", expanded=False):
            selected_categories = st.multiselect("Filter kategori dokumen", options=categories, default=[])

            if selected_categories:
                selected_context_count = sum(category_chunk_counts.get(category, 0) for category in selected_categories)
                top_k = max(1, selected_context_count)
                st.caption(
                    f"Jumlah referensi konteks otomatis: **{top_k}** (semua konteks dari folder/kategori terpilih)."
                )
            else:
                top_k = max(1, total_context_count)
                st.caption(
                    f"Jumlah referensi konteks otomatis: **{top_k}** (semua konteks dari seluruh folder)."
                )

        for message in messages:
            role = "assistant" if message.get("role") == "assistant" else "user"
            with st.chat_message(role):
                st.markdown(str(message.get("content") or ""))
                if role == "assistant":
                    sources = message.get("sources") or []
                    if sources:
                        with st.expander(f"📎 Sitasi ({len(sources)})", expanded=False):
                            for idx, item in enumerate(sources, start=1):
                                source = str(item.get("source") or "-")
                                title = str(item.get("title") or "Dokumen")
                                page = item.get("page")
                                instrument_type = str(item.get("instrument_type") or "-")
                                code = str(item.get("code") or item.get("number_year") or "-")
                                issued_date = str(item.get("issued_date") or "-")
                                article_text = str(item.get("article_list") or "-")
                                short_quote = str(item.get("short_quote") or "-")
                                article_snippets = item.get("article_snippets") or []

                                with st.expander(f"▸ [{idx}] {title} (hal. {page})", expanded=False):
                                    st.caption(f"{instrument_type} | {code} | Tanggal: {issued_date}")
                                    st.markdown(f"**Pasal terkait:** {article_text}")
                                    st.markdown("**Frasa ringkas:**")
                                    st.info(short_quote)
                                    if article_snippets:
                                        st.markdown("**Potongan per pasal:**")
                                        for snippet in article_snippets:
                                            st.markdown(f"- {snippet}")
                                    st.caption(f"Sumber: {source}")

        question = st.chat_input("Tulis pertanyaan tentang peraturan...") or ""
        ask_clicked = bool(question.strip()) and is_configured

        return ChatbotViewResult(
            go_home=go_home,
            clear_chat=clear_chat,
            ask_clicked=ask_clicked,
            question=question,
            selected_categories=selected_categories,
            top_k=top_k,
        )
