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
    selected_path_prefixes: list[str]
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
        st.markdown(
            """
            <style>
                /* Ruang bawah agar chat terakhir tidak ketutup input floating */
                .main .block-container {
                    padding-bottom: 7.5rem !important;
                }

                /* Input pertanyaan tetap terlihat saat scroll */
                div[data-testid="stChatInput"] {
                    position: fixed;
                    left: 50%;
                    transform: translateX(-50%);
                    bottom: 0.85rem;
                    width: min(1100px, calc(100vw - 3rem));
                    z-index: 999;
                    background: rgba(255, 255, 255, 0.96);
                    border: 1px solid rgba(148, 163, 184, 0.35);
                    border-radius: 14px;
                    box-shadow: 0 10px 24px rgba(2, 6, 23, 0.14);
                    backdrop-filter: blur(6px);
                    padding: 0.25rem 0.35rem;
                }

                html[data-theme="dark"] div[data-testid="stChatInput"],
                body[data-theme="dark"] div[data-testid="stChatInput"] {
                    background: rgba(15, 23, 42, 0.88);
                    border: 1px solid rgba(148, 163, 184, 0.35);
                    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.45);
                }

                @media (prefers-color-scheme: dark) {
                    div[data-testid="stChatInput"] {
                        background: rgba(15, 23, 42, 0.88);
                        border: 1px solid rgba(148, 163, 184, 0.35);
                        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.45);
                    }
                }

                @media (max-width: 900px) {
                    div[data-testid="stChatInput"] {
                        width: calc(100vw - 1.2rem);
                        bottom: 0.5rem;
                    }
                }

                .chatbot-shell-card {
                    background: rgba(255, 255, 255, 0.9);
                    border: 1px solid rgba(148, 163, 184, 0.3);
                    border-radius: 16px;
                    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
                    padding: 0.9rem 1rem;
                    margin-bottom: 0.8rem;
                }

                .chatbot-header-card {
                    padding-top: 1rem;
                }

                .chatbot-shell-card [data-testid="stButton"] > button,
                .chatbot-shell-card [data-testid="stFormSubmitButton"] > button {
                    background: rgba(248, 250, 252, 0.95);
                }

                html[data-theme="dark"] .chatbot-shell-card,
                body[data-theme="dark"] .chatbot-shell-card {
                    background: rgba(15, 23, 42, 0.78);
                    border: 1px solid rgba(148, 163, 184, 0.28);
                    box-shadow: 0 10px 22px rgba(2, 6, 23, 0.45);
                }

                @media (prefers-color-scheme: dark) {
                    .chatbot-shell-card {
                        background: rgba(15, 23, 42, 0.78);
                        border: 1px solid rgba(148, 163, 184, 0.28);
                        box-shadow: 0 10px 22px rgba(2, 6, 23, 0.45);
                    }
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="chatbot-shell-card chatbot-header-card">', unsafe_allow_html=True)
        st.markdown("## 🤖 Chatbot Peraturan")
        st.caption("Aplikasi chatbot terpisah untuk tanya jawab regulasi.")

        col_left, col_right = st.columns([1, 1])
        with col_left:
            go_home = st.button("↩️ Kembali ke Login", use_container_width=True, key="btn_home_chatbot")
        with col_right:
            clear_chat = st.button("🧹 Reset Chat", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if not is_configured:
            st.error(f"❌ {config_message}")

        selected_categories: list[str] = []
        selected_path_prefixes: list[str] = []
        selected_documents: list[str] = []
        top_k = 6
        question = ""
        ask_clicked = False

        tab_chat, tab_status = st.tabs(["💬 Tanya Jawab", "📚 Menu Status Peraturan"])

        with tab_chat:
            with st.expander("Opsi Lanjutan (Opsional)", expanded=False):
                if len(categories) <= 1 and categories:
                    selected_categories = list(categories)
                    st.caption(f"Kategori dokumen: **{categories[0]}**")
                else:
                    selected_categories = st.multiselect("Filter kategori dokumen", options=categories, default=[])

                selected_path_prefixes = self._render_dynamic_folder_filters(
                    regulation_file_statuses,
                    selected_categories,
                )

                document_options: list[str] = []
                document_label_map: dict[str, str] = {}
                for item in regulation_file_statuses:
                    if selected_categories and item.category not in selected_categories:
                        continue
                    if selected_path_prefixes and not any(
                        item.source_relative_path.startswith(f"{prefix}/") or item.source_relative_path == prefix
                        for prefix in selected_path_prefixes
                    ):
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
                elif selected_path_prefixes:
                    st.caption("Jumlah referensi konteks otomatis menyesuaikan subfolder yang dipilih.")
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
                                    document_status = str(item.get("document_status") or "diubah").strip().lower()
                                    document_status_label = str(item.get("document_status_label") or "Diubah")
                                    article_text = str(item.get("article_list") or "-")
                                    short_quote = str(item.get("short_quote") or "-")
                                    article_snippets = item.get("article_snippets") or []

                                    if document_status == "terbaru":
                                        status_badge = "🟢"
                                    elif document_status == "diubah":
                                        status_badge = "🔵"
                                    elif document_status == "dicabut":
                                        status_badge = "🔴"
                                    else:
                                        status_badge = "🟡"

                                    with st.expander(f"▸ [{idx}] {title} (hal. {page})", expanded=False):
                                        st.caption(
                                            f"{status_badge} Status: {document_status_label} | "
                                            f"{instrument_type} | {code} | Tanggal: {issued_date}"
                                        )
                                        if document_status == "dicabut":
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
                st.metric("🔵 Diubah", int(regulation_status_counts.get("Diubah", 0)))
            with col_d:
                st.metric("🔴 Dicabut", int(regulation_status_counts.get("Dicabut", 0)))
            with col_e:
                st.metric("✅ Aktif", int(regulation_status_counts.get("Aktif", 0)))

            st.caption(f"Tidak Aktif: **{int(regulation_status_counts.get('Tidak Aktif', 0))}**")

            status_filter = st.selectbox(
                "Filter status dokumen",
                options=["Semua", "Terbaru", "Diubah", "Dicabut", "Aktif", "Tidak Aktif"],
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
            selected_path_prefixes=selected_path_prefixes,
            selected_documents=selected_documents,
            top_k=top_k,
        )

    def _render_dynamic_folder_filters(
        self,
        items: list[RegulationFileStatus],
        selected_categories: list[str],
    ) -> list[str]:
        folder_tree, folder_doc_counts = self._build_folder_tree(items=items, selected_categories=selected_categories)
        if not folder_tree:
            self._clear_folder_filter_keys(start_level=0)
            st.caption("Tidak ada subfolder lanjutan untuk dipilih pada filter saat ini.")
            return []

        selected_parts: list[str] = []
        current_level_tree = folder_tree
        level = 0

        while current_level_tree:
            options = sorted(current_level_tree.keys(), key=lambda value: value.lower())
            if not options:
                break

            key = f"chatbot_dynamic_folder_level_{level}"
            default_label = "(Semua folder)"
            select_options = [default_label, *options]
            current_value = st.session_state.get(key, default_label)
            if current_value not in select_options:
                current_value = default_label

            selected_value = st.selectbox(
                f"Filter subfolder level {level + 1} (opsional)",
                options=select_options,
                index=select_options.index(current_value),
                key=key,
                format_func=lambda option: self._format_dynamic_folder_option(
                    option,
                    selected_parts,
                    folder_doc_counts,
                    default_label,
                ),
            )

            if selected_value == default_label:
                self._clear_folder_filter_keys(start_level=level + 1)
                break

            selected_parts.append(selected_value)
            current_level_tree = current_level_tree.get(selected_value, {})
            level += 1

        selected_prefix = "/".join(selected_parts).strip("/")
        if not selected_prefix:
            return []

        st.caption(f"Subfolder aktif: **{selected_prefix}**")
        return [selected_prefix]

    def _build_folder_tree(
        self,
        items: list[RegulationFileStatus],
        selected_categories: list[str],
    ) -> tuple[dict[str, Any], dict[str, int]]:
        tree: dict[str, Any] = {}
        folder_counts: dict[str, int] = {}

        for item in items:
            if selected_categories and item.category not in selected_categories:
                continue

            normalized_path = str(item.source_relative_path or "").replace("\\", "/")
            parts = [part.strip() for part in normalized_path.split("/") if part.strip()]
            folder_parts = parts[:-1]

            current_tree = tree
            for depth, folder_name in enumerate(folder_parts, start=1):
                current_prefix = "/".join(folder_parts[:depth])
                folder_counts[current_prefix] = folder_counts.get(current_prefix, 0) + 1
                current_tree = current_tree.setdefault(folder_name, {})

        return tree, folder_counts

    def _format_dynamic_folder_option(
        self,
        option: str,
        selected_parts: list[str],
        folder_doc_counts: dict[str, int],
        default_label: str,
    ) -> str:
        if option == default_label:
            return default_label

        prefix = "/".join([*selected_parts, option]).strip("/")
        count = folder_doc_counts.get(prefix, 0)
        return f"{option} ({count} dokumen)"

    def _clear_folder_filter_keys(self, start_level: int) -> None:
        level = max(0, int(start_level))
        while True:
            key = f"chatbot_dynamic_folder_level_{level}"
            if key not in st.session_state:
                break
            del st.session_state[key]
            level += 1

    def _filter_regulation_statuses(
        self,
        items: list[RegulationFileStatus],
        status_filter: str,
        keyword: str,
    ) -> list[RegulationFileStatus]:
        clean_keyword = keyword.strip().lower()
        filtered: list[RegulationFileStatus] = []
        for item in items:
            if status_filter != "Semua":
                document_status = str(item.document_status or "").strip().lower()
                if status_filter == "Aktif":
                    if document_status not in {"terbaru", "diubah"}:
                        continue
                elif status_filter == "Tidak Aktif":
                    if document_status != "dicabut":
                        continue
                elif item.document_status_label != status_filter:
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
        if clean == "diubah":
            return "🔵"
        if clean == "dicabut":
            return "🔴"
        return "🟡"
