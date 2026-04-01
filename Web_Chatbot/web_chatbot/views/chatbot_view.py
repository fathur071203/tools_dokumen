from dataclasses import dataclass
from typing import Any

import streamlit as st

from web_chatbot.services.chatbot_service import RegulationFileStatus


@dataclass
class ChatbotViewResult:
    go_home: bool
    clear_chat: bool
    ask_clicked: bool
    question: str
    selected_categories: list[str]
    selected_documents: list[str]
    top_k: int


class ChatbotView:
    def render(
        self,
        messages: list[dict[str, Any]],
        categories: list[str],
        category_chunk_counts: dict[str, int],
        total_context_count: int,
        regulation_file_statuses: list[RegulationFileStatus],
        regulation_status_counts: dict[str, int],
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
        selected_documents: list[str] = []
        top_k = 6
        question = ""
        ask_clicked = False

        tab_chat, tab_status = st.tabs(["💬 Tanya Jawab", "📚 Menu Status Peraturan"])

        with tab_chat:
            with st.expander("Opsi Lanjutan (Opsional)", expanded=False):
                selected_categories = st.multiselect("Filter kategori dokumen", options=categories, default=[])

                document_options: list[str] = []
                document_label_map: dict[str, str] = {}
                for item in regulation_file_statuses:
                    if selected_categories and item.category not in selected_categories:
                        continue
                    path = item.source_relative_path
                    label = f"[{item.document_status_label}] {item.source_file_name} — {path}"
                    document_options.append(path)
                    document_label_map[path] = label

                selected_documents = st.multiselect(
                    "Filter dokumen spesifik (opsional)",
                    options=document_options,
                    default=[],
                    format_func=lambda opt: document_label_map.get(opt, opt),
                )

                doc_selected_count = len(selected_documents)
                if doc_selected_count:
                    st.caption(f"Dokumen dipilih: **{doc_selected_count}** file. Pencarian hanya pada file ini.")

                if selected_documents:
                    st.caption("Jumlah referensi konteks otomatis menyesuaikan dokumen yang dipilih.")
                elif selected_categories:
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
                                    document_status = str(item.get("document_status") or "berlaku").strip().lower()
                                    document_status_label = str(item.get("document_status_label") or "Berlaku")
                                    article_text = str(item.get("article_list") or "-")
                                    short_quote = str(item.get("short_quote") or "-")
                                    article_snippets = item.get("article_snippets") or []

                                    if document_status == "terbaru":
                                        status_badge = "🟢"
                                    elif document_status in {"dicabut", "tidak_berlaku"}:
                                        status_badge = "🔴"
                                    else:
                                        status_badge = "🟡"

                                    with st.expander(f"▸ [{idx}] {title} (hal. {page})", expanded=False):
                                        st.caption(
                                            f"{status_badge} Status: {document_status_label} | "
                                            f"{instrument_type} | {code} | Tanggal: {issued_date}"
                                        )
                                        if document_status in {"dicabut", "tidak_berlaku"}:
                                            st.warning("Dokumen ini berstatus tidak berlaku/dicabut. Gunakan sebagai referensi historis.")
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

        with tab_status:
            total_docs = len(regulation_file_statuses)
            col_a, col_b, col_c, col_d, col_e = st.columns(5)
            with col_a:
                st.metric("Total Dokumen", total_docs)
            with col_b:
                st.metric("🟢 Terbaru", int(regulation_status_counts.get("Terbaru", 0)))
            with col_c:
                st.metric("🟡 Berlaku", int(regulation_status_counts.get("Berlaku", 0)))
            with col_d:
                st.metric("🔴 Dicabut", int(regulation_status_counts.get("Dicabut", 0)))
            with col_e:
                st.metric("⚫ Tidak Berlaku", int(regulation_status_counts.get("Tidak Berlaku", 0)))

            status_filter = st.selectbox(
                "Filter status dokumen",
                options=["Semua", "Terbaru", "Berlaku", "Dicabut", "Tidak Berlaku"],
                index=0,
                key="chatbot_status_filter",
            )
            path_keyword = st.text_input(
                "Cari path/folder/dokumen",
                value="",
                placeholder="Contoh: 02. Manajemen Logistik atau PADGI No. 34",
                key="chatbot_status_path_search",
            )

            filtered_items = self._filter_regulation_statuses(
                regulation_file_statuses,
                status_filter=status_filter,
                keyword=path_keyword,
            )

            st.markdown("#### Hierarki Folder & Dokumen")
            self._render_regulation_tree(filtered_items)

            rows: list[dict[str, str]] = []
            for item in filtered_items:
                rows.append(
                    {
                        "Status": item.document_status_label,
                        "Kategori": item.category,
                        "Nama File": item.source_file_name,
                        "Path": item.source_relative_path,
                    }
                )

            if rows:
                st.markdown("#### Tabel Detail Dokumen")
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("Tidak ada dokumen pada filter status tersebut.")

        return ChatbotViewResult(
            go_home=go_home,
            clear_chat=clear_chat,
            ask_clicked=ask_clicked,
            question=question,
            selected_categories=selected_categories,
            selected_documents=selected_documents,
            top_k=top_k,
        )

    def _filter_regulation_statuses(
        self,
        items: list[RegulationFileStatus],
        status_filter: str,
        keyword: str,
    ) -> list[RegulationFileStatus]:
        clean_keyword = keyword.strip().lower()
        filtered: list[RegulationFileStatus] = []
        for item in items:
            if status_filter != "Semua" and item.document_status_label != status_filter:
                continue

            if clean_keyword:
                haystack = f"{item.source_relative_path} {item.source_file_name} {item.category}".lower()
                if clean_keyword not in haystack:
                    continue

            filtered.append(item)
        return filtered

    def _render_regulation_tree(self, items: list[RegulationFileStatus]) -> None:
        tree: dict[str, Any] = {"folders": {}, "docs": []}

        for item in items:
            parts = [part.strip() for part in item.source_relative_path.split("/") if part.strip()]
            if not parts:
                parts = [item.source_file_name]

            folders = parts[:-1]
            file_name = parts[-1]

            cursor = tree
            for folder in folders:
                cursor = cursor["folders"].setdefault(folder, {"folders": {}, "docs": []})
            cursor["docs"].append((file_name, item))

        root_folders = tree["folders"]
        if not root_folders and not tree["docs"]:
            st.info("Tidak ada dokumen untuk ditampilkan.")
            return

        for folder_name in sorted(root_folders.keys()):
            self._render_tree_node(folder_name, root_folders[folder_name], level=0)

        for file_name, item in sorted(tree["docs"], key=lambda x: x[0].lower()):
            badge = self._status_badge(item.document_status)
            st.markdown(f"- {badge} **{file_name}** — {item.document_status_label}")

    def _render_tree_node(self, folder_name: str, node: dict[str, Any], level: int) -> None:
        doc_count = self._count_docs(node)
        icon = "📁" if level == 0 else "🗂️"
        with st.expander(f"{icon} {folder_name} ({doc_count} dokumen)", expanded=False):
            for child_name in sorted(node["folders"].keys()):
                self._render_tree_node(child_name, node["folders"][child_name], level=level + 1)

            for file_name, item in sorted(node["docs"], key=lambda x: x[0].lower()):
                badge = self._status_badge(item.document_status)
                st.markdown(f"- {badge} **{file_name}** — {item.document_status_label}")

    def _count_docs(self, node: dict[str, Any]) -> int:
        total = len(node.get("docs", []))
        for child in node.get("folders", {}).values():
            total += self._count_docs(child)
        return total

    def _status_badge(self, status: str) -> str:
        clean = str(status).strip().lower()
        if clean == "terbaru":
            return "🟢"
        if clean in {"dicabut", "tidak_berlaku"}:
            return "🔴"
        return "🟡"
