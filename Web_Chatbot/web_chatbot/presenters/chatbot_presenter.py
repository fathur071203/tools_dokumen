from __future__ import annotations

from typing import Any

import streamlit as st

from web_chatbot.services.chatbot_service import ChatbotService, RetrievedChunk
from web_chatbot.services.dlp_service import DLPService
from web_chatbot.state.session_state import SessionStateManager
from web_chatbot.views.chatbot_view import ChatbotView


class ChatbotPresenter:
    KEY_MESSAGES = "chatbot_messages"
    KEY_MESSAGES_BY_USER = "chatbot_messages_by_user"

    def __init__(self, view: ChatbotView):
        self.view = view
        self.chatbot_service = ChatbotService()

    def present(self) -> None:
        self._ensure_user_history_bucket()
        self._migrate_legacy_messages_if_needed()

        is_configured, config_message = self.chatbot_service.is_configured()
        categories = self.chatbot_service.get_categories()
        category_chunk_counts = self.chatbot_service.get_category_chunk_counts()
        total_context_count = self.chatbot_service.get_context_count()
        regulation_file_statuses = self.chatbot_service.get_regulation_file_statuses()
        regulation_status_counts = self.chatbot_service.get_regulation_status_counts()

        result = self.view.render(
            messages=self._get_messages(),
            categories=categories,
            category_chunk_counts=category_chunk_counts,
            total_context_count=total_context_count,
            regulation_file_statuses=regulation_file_statuses,
            regulation_status_counts=regulation_status_counts,
            is_configured=is_configured,
            config_message=config_message,
        )

        if result.go_home:
            SessionStateManager.expire_session("Silakan login kembali.")

        if result.clear_chat:
            self._set_messages([])
            st.rerun()

        if not result.ask_clicked:
            return

        clean_question = result.question.strip()

        allowed, dlp_message = DLPService.validate_question(clean_question)
        if not allowed:
            self._append_message(role="user", content=clean_question)
            self._append_message(role="assistant", content=f"❌ {dlp_message}")
            st.rerun()

        self._append_message(role="user", content=clean_question)
        chat_history = self._build_history_for_model()

        with st.spinner("🔎 Mencari konteks dokumen dan menyiapkan jawaban..."):
            try:
                effective_top_k = max(
                    1,
                    self.chatbot_service.get_context_count(
                        selected_categories=result.selected_categories,
                        selected_documents=result.selected_documents,
                    ),
                )
                answer, sources = self.chatbot_service.answer_question(
                    clean_question,
                    selected_categories=result.selected_categories,
                    selected_documents=result.selected_documents,
                    top_k=effective_top_k,
                    chat_history=chat_history,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"❌ Gagal menjawab pertanyaan: {exc}")
                return

        safe_answer, findings = DLPService.redact_text(answer, max_length=5000)
        dlp_notice = DLPService.build_dlp_notice(findings)
        final_answer = f"{safe_answer}\n\n{dlp_notice}" if dlp_notice else safe_answer

        self._append_message(role="assistant", content=final_answer, sources=self._serialize_sources(sources))
        st.rerun()

    def _get_messages(self) -> list[dict[str, Any]]:
        bucket = st.session_state.get(self.KEY_MESSAGES_BY_USER, {})
        if not isinstance(bucket, dict):
            return []
        return list(bucket.get(self._get_user_history_key(), []))

    def _set_messages(self, messages: list[dict[str, Any]]) -> None:
        bucket = st.session_state.get(self.KEY_MESSAGES_BY_USER, {})
        if not isinstance(bucket, dict):
            bucket = {}
        bucket[self._get_user_history_key()] = list(messages)
        st.session_state[self.KEY_MESSAGES_BY_USER] = bucket

    def _append_message(self, role: str, content: str, sources: list[dict[str, Any]] | None = None) -> None:
        messages = self._get_messages()
        messages.append({"role": role, "content": content, "sources": sources or []})
        self._set_messages(messages)

    def _serialize_sources(self, sources: list[RetrievedChunk]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for item in sources:
            chunk = item.chunk
            preview = ChatbotService.build_source_preview(chunk)
            safe_quote, _ = DLPService.redact_text(str(preview.get("short_quote") or "-"), max_length=320)
            raw_snippets = list(preview.get("article_snippets") or [])
            safe_snippets: list[str] = []
            for snippet in raw_snippets:
                sanitized, _ = DLPService.redact_text(str(snippet), max_length=280)
                safe_snippets.append(sanitized)
            serialized.append(
                {
                    "title": chunk.title,
                    "source": DLPService.sanitize_source_label(chunk.source_relative_path),
                    "source_file_name": chunk.source_file_name,
                    "document_status": chunk.document_status,
                    "document_status_label": chunk.document_status_label,
                    "page": chunk.page,
                    "instrument_type": chunk.instrument_type,
                    "code": chunk.code,
                    "number_year": chunk.number_year,
                    "issued_date": chunk.issued_date,
                    "article_candidates": chunk.article_candidates,
                    "short_quote": safe_quote,
                    "article_list": str(preview.get("article_list") or "-"),
                    "article_snippets": safe_snippets,
                }
            )
        return serialized

    def _build_history_for_model(self) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for msg in self._get_messages()[-8:]:
            role = str(msg.get("role") or "").strip().lower()
            content = str(msg.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                history.append({"role": role, "content": content})
        return history

    def _ensure_user_history_bucket(self) -> None:
        if self.KEY_MESSAGES_BY_USER not in st.session_state or not isinstance(st.session_state.get(self.KEY_MESSAGES_BY_USER), dict):
            st.session_state[self.KEY_MESSAGES_BY_USER] = {}

        bucket = st.session_state[self.KEY_MESSAGES_BY_USER]
        user_key = self._get_user_history_key()
        if user_key not in bucket or not isinstance(bucket.get(user_key), list):
            bucket[user_key] = []
            st.session_state[self.KEY_MESSAGES_BY_USER] = bucket

    def _migrate_legacy_messages_if_needed(self) -> None:
        legacy_messages = st.session_state.get(self.KEY_MESSAGES)
        if not isinstance(legacy_messages, list) or not legacy_messages:
            return

        current_messages = self._get_messages()
        if not current_messages:
            self._set_messages(legacy_messages)
        del st.session_state[self.KEY_MESSAGES]

    def _get_user_history_key(self) -> str:
        user = SessionStateManager.get_authenticated_user()
        username = str(user.get("username", "") or "").strip().lower()
        email = str(user.get("email", "") or "").strip().lower()
        if username:
            return f"user:{username}"
        if email:
            return f"email:{email}"
        return "user:anonymous"
