from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    category: str
    title: str
    source_relative_path: str
    source_file_name: str
    instrument_type: str
    code: str
    number_year: str
    issued_date: str
    page: int
    text: str
    article_candidates: list[str]
    document_status: str
    document_status_label: str
    document_priority: int


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


@dataclass
class RegulationFileStatus:
    source_relative_path: str
    title: str
    category: str
    source_file_name: str
    document_status: str
    document_status_label: str
    document_priority: int


class ChatbotService:
    BASE_DIR = Path(__file__).resolve().parents[2]
    DATA_DIR = BASE_DIR / "static" / "data" / "structured_docs"

    ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
    ENV_GEMINI_CHAT_MODEL = "GEMINI_CHAT_MODEL"
    ENV_GEMINI_EMBEDDING_MODEL = "GEMINI_EMBEDDING_MODEL"

    DEFAULT_CHAT_MODEL = "gemini-2.5-flash-lite"
    DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2-preview"
    _env_loaded = False

    def __init__(self) -> None:
        self._client: Any | None = None

    def is_configured(self) -> tuple[bool, str]:
        self._load_env_file_once()
        api_key = os.getenv(self.ENV_GEMINI_API_KEY, "").strip()
        if not api_key:
            return False, "GEMINI_API_KEY belum di-set di environment/.env."

        if not self._is_sdk_available():
            return False, "Paket `google-genai` belum tersedia. Tambahkan dependency lalu install requirements."

        return True, "Konfigurasi Gemini siap digunakan."

    def get_categories(self) -> list[str]:
        return sorted({chunk.category for chunk in self._load_chunks() if chunk.category})

    def get_category_chunk_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for chunk in self._load_chunks():
            category = chunk.category or "Tanpa Kategori"
            counts[category] = counts.get(category, 0) + 1
        return counts

    def get_context_count(
        self,
        selected_categories: list[str] | None = None,
        selected_documents: list[str] | None = None,
    ) -> int:
        chunks = list(self._load_chunks())

        doc_selected = selected_documents or []
        doc_set = {item.strip().lower() for item in doc_selected if item and item.strip()}
        if doc_set:
            chunks = [chunk for chunk in chunks if chunk.source_relative_path.strip().lower() in doc_set]
            return len(chunks)

        selected = selected_categories or []
        if not selected:
            return len(chunks)

        selected_set = {item.strip().lower() for item in selected if item and item.strip()}
        if not selected_set:
            return len(chunks)

        return sum(1 for chunk in chunks if chunk.category.strip().lower() in selected_set)

    def get_regulation_file_statuses(self, selected_categories: list[str] | None = None) -> list[RegulationFileStatus]:
        chunks = list(self._load_chunks())
        selected = selected_categories or []
        if selected:
            selected_set = {item.strip().lower() for item in selected if item and item.strip()}
            if selected_set:
                chunks = [chunk for chunk in chunks if chunk.category.strip().lower() in selected_set]

        grouped: dict[str, RegulationFileStatus] = {}
        for chunk in chunks:
            key = chunk.source_relative_path.strip()
            if not key:
                continue

            current = grouped.get(key)
            candidate = RegulationFileStatus(
                source_relative_path=chunk.source_relative_path,
                title=chunk.title,
                category=chunk.category,
                source_file_name=chunk.source_file_name,
                document_status=chunk.document_status,
                document_status_label=chunk.document_status_label,
                document_priority=chunk.document_priority,
            )

            if current is None:
                grouped[key] = candidate
                continue

            if candidate.document_priority > current.document_priority:
                grouped[key] = candidate

        return sorted(
            grouped.values(),
            key=lambda item: (-item.document_priority, item.category.lower(), item.source_file_name.lower()),
        )

    def get_regulation_status_counts(self, selected_categories: list[str] | None = None) -> dict[str, int]:
        statuses = self.get_regulation_file_statuses(selected_categories=selected_categories)
        counts = {"Terbaru": 0, "Berlaku": 0, "Dicabut": 0, "Tidak Berlaku": 0}
        for item in statuses:
            label = item.document_status_label
            if label not in counts:
                counts[label] = 0
            counts[label] += 1
        return counts

    def answer_question(
        self,
        question: str,
        selected_categories: list[str] | None = None,
        selected_documents: list[str] | None = None,
        top_k: int = 6,
        chat_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[RetrievedChunk]]:
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Pertanyaan tidak boleh kosong.")

        chunks = self._retrieve_chunks(
            clean_question,
            selected_categories=selected_categories or [],
            selected_documents=selected_documents or [],
            top_k=top_k,
        )
        if not chunks:
            return (
                "Maaf, saya belum menemukan konteks yang relevan dari dokumen yang tersedia. "
                "Coba gunakan kata kunci yang lebih spesifik (misalnya kode regulasi atau nomor pasal).",
                [],
            )

        response_text = self._generate_answer_with_context(clean_question, chunks, chat_history=chat_history or [])
        return response_text, chunks

    @classmethod
    def _load_env_file_once(cls) -> None:
        if cls._env_loaded:
            return

        env_candidates = [
            Path(".env"),
            cls.BASE_DIR / ".env",
        ]

        for env_path in env_candidates:
            if not env_path.exists():
                continue
            for line in env_path.read_text(encoding="utf-8").splitlines():
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
                    continue

                key, raw_value = clean_line.split("=", 1)
                key = key.strip()
                if not key or key in os.environ:
                    continue

                value = raw_value.strip().strip('"').strip("'")
                os.environ[key] = value

        cls._env_loaded = True

    @classmethod
    @lru_cache(maxsize=1)
    def _load_chunks(cls) -> tuple[DocumentChunk, ...]:
        if not cls.DATA_DIR.exists():
            return tuple()

        chunks: list[DocumentChunk] = []
        for json_file in sorted(cls.DATA_DIR.rglob("*.json")):
            try:
                payload = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            category = str(payload.get("category") or json_file.parent.name).strip()
            title = str(payload.get("title") or json_file.stem).strip()
            relative_path = str(payload.get("source_relative_path") or json_file.name).strip()
            source_file_name = str(payload.get("source_file_name") or Path(relative_path).name).strip()
            instrument_type = str(payload.get("instrument_type") or "").strip()
            code = str(payload.get("code") or "").strip()
            number_year = str(payload.get("number_year") or "").strip()
            issued_date = str(payload.get("issued_date") or "").strip()
            document_status, status_label, document_priority = cls._infer_document_status(
                relative_path=relative_path,
                source_file_name=source_file_name,
            )
            pages = payload.get("pages") or []

            if isinstance(pages, list) and pages:
                for page_item in pages:
                    if not isinstance(page_item, dict):
                        continue
                    page_number = int(page_item.get("page") or 0)
                    text = str(page_item.get("text") or "").strip() or str(page_item.get("excerpt") or "").strip()
                    if not text:
                        continue

                    article_candidates = page_item.get("article_candidates") or []
                    if not isinstance(article_candidates, list):
                        article_candidates = []
                    article_candidates = [str(item).strip() for item in article_candidates if str(item).strip()]

                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{relative_path}#p{page_number}",
                            category=category or "Tanpa Kategori",
                            title=title or json_file.stem,
                            source_relative_path=relative_path,
                            source_file_name=source_file_name,
                            instrument_type=instrument_type,
                            code=code,
                            number_year=number_year,
                            issued_date=issued_date,
                            page=page_number,
                            text=cls._normalize_text(text),
                            article_candidates=article_candidates,
                            document_status=document_status,
                            document_status_label=status_label,
                            document_priority=document_priority,
                        )
                    )
                continue

            fallback_text = str(payload.get("text") or payload.get("content") or "").strip()
            if fallback_text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{relative_path}#full",
                        category=category or "Tanpa Kategori",
                        title=title or json_file.stem,
                        source_relative_path=relative_path,
                        source_file_name=source_file_name,
                        instrument_type=instrument_type,
                        code=code,
                        number_year=number_year,
                        issued_date=issued_date,
                        page=0,
                        text=cls._normalize_text(fallback_text),
                        article_candidates=[],
                        document_status=document_status,
                        document_status_label=status_label,
                        document_priority=document_priority,
                    )
                )

        return tuple(chunks)

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        return re.sub(r"\s+", " ", text.replace("\n", " ").replace("\r", " ")).strip()

    @classmethod
    def _tokenize(cls, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    @classmethod
    def _expand_query_tokens(cls, tokens: list[str]) -> set[str]:
        expanded = set(tokens)
        synonym_map: dict[str, list[str]] = {
            "threshold": ["batasan", "nilai", "pagu", "ambang"],
            "lelang": ["tender", "pemilihan", "pengadaan"],
            "tender": ["lelang", "pemilihan", "pengadaan"],
            "pengadaan": ["tender", "lelang", "nilai", "batasan"],
            "barang": ["jasa", "konstruksi"],
            "jasa": ["barang", "konsultansi", "konstruksi"],
            "nominal": ["nilai", "batasan", "rupiah", "rp"],
            "nilai": ["nominal", "batasan", "rp", "rupiah"],
        }

        for token in list(expanded):
            expanded.update(synonym_map.get(token, []))
        return expanded

    @classmethod
    def _infer_document_status(cls, relative_path: str, source_file_name: str) -> tuple[str, str, int]:
        joined = f"{relative_path} {source_file_name}".lower()

        if "terbaru_" in joined or "/terbaru_" in joined:
            return "terbaru", "Terbaru", 3
        if "dicabut" in joined or "sudah dicabut" in joined:
            return "dicabut", "Dicabut", 1
        if "tidak berlaku" in joined or "tidak_berlaku" in joined:
            return "tidak_berlaku", "Tidak Berlaku", 0
        return "berlaku", "Berlaku", 2

    @classmethod
    def _status_score_adjustment(cls, document_status: str) -> float:
        status_bonus_map = {
            "terbaru": 0.20,
            "berlaku": 0.08,
            "dicabut": -0.12,
            "tidak_berlaku": -0.18,
        }
        return float(status_bonus_map.get(document_status, 0.0))

    def _retrieve_chunks(
        self,
        question: str,
        selected_categories: list[str],
        selected_documents: list[str],
        top_k: int,
    ) -> list[RetrievedChunk]:
        chunks = list(self._load_chunks())

        selected_doc_set = {item.strip().lower() for item in selected_documents if item and item.strip()}
        if selected_doc_set:
            chunks = [chunk for chunk in chunks if chunk.source_relative_path.strip().lower() in selected_doc_set]

        if selected_categories and not selected_doc_set:
            selected = {item.strip().lower() for item in selected_categories if item.strip()}
            chunks = [chunk for chunk in chunks if chunk.category.strip().lower() in selected]

        if not chunks:
            return []

        lexical_top_n = min(max(top_k * 4, 40), len(chunks))
        lexical_ranked = self._rank_lexical(question, chunks, top_n=lexical_top_n)
        if not lexical_ranked:
            lexical_ranked = [RetrievedChunk(chunk=chunk, score=0.0) for chunk in chunks[: min(20, len(chunks))]]

        semantic_ranked = self._rerank_with_embeddings(question, lexical_ranked)
        ranked = semantic_ranked if semantic_ranked else lexical_ranked

        ranked_by_id = {item.chunk.chunk_id: item for item in ranked}
        for chunk in chunks:
            if chunk.chunk_id not in ranked_by_id:
                ranked.append(RetrievedChunk(chunk=chunk, score=0.0))

        for item in ranked:
            item.score += self._status_score_adjustment(item.chunk.document_status)

        has_current_regulation_match = any(
            item.score > 0
            and item.chunk.document_status in {"terbaru", "berlaku"}
            for item in ranked
        )
        if has_current_regulation_match:
            for item in ranked:
                if item.chunk.document_status in {"dicabut", "tidak_berlaku"}:
                    item.score -= 0.20

        ranked.sort(key=lambda item: item.score, reverse=True)
        effective_top_k = len(chunks) if top_k <= 0 else min(top_k, len(chunks))
        return ranked[:effective_top_k]

    def _rank_lexical(self, question: str, chunks: list[DocumentChunk], top_n: int) -> list[RetrievedChunk]:
        q_tokens = self._tokenize(question)
        if not q_tokens:
            return []

        q_token_set = self._expand_query_tokens(q_tokens)
        results: list[RetrievedChunk] = []
        for chunk in chunks:
            c_tokens = self._tokenize(chunk.text)
            if not c_tokens:
                continue

            overlap = q_token_set.intersection(set(c_tokens))
            if not overlap:
                continue

            overlap_score = len(overlap) / max(len(q_token_set), 1)
            density_score = len(overlap) / max(len(c_tokens), 1)
            score = (0.85 * overlap_score) + (0.15 * density_score)
            results.append(RetrievedChunk(chunk=chunk, score=score))

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_n]

    def _rerank_with_embeddings(self, question: str, lexical_ranked: list[RetrievedChunk]) -> list[RetrievedChunk]:
        is_ready, _ = self.is_configured()
        if not is_ready:
            return []

        client = self._get_client()
        if client is None:
            return []

        model = os.getenv(self.ENV_GEMINI_EMBEDDING_MODEL, self.DEFAULT_EMBEDDING_MODEL).strip()
        if not model:
            return []

        try:
            query_vector = self._embed_text(client, model, question)
            doc_vectors = self._embed_texts(client, model, [item.chunk.text[:6000] for item in lexical_ranked])
        except Exception:
            return []

        if not query_vector or not doc_vectors:
            return []

        reranked: list[RetrievedChunk] = []
        for item, vector in zip(lexical_ranked, doc_vectors):
            similarity = self._cosine_similarity(query_vector, vector)
            blended_score = (0.8 * similarity) + (0.2 * item.score)
            reranked.append(RetrievedChunk(chunk=item.chunk, score=blended_score))
        return reranked

    def _generate_answer_with_context(
        self,
        question: str,
        retrieved: list[RetrievedChunk],
        chat_history: list[dict[str, str]],
    ) -> str:
        is_ready, message = self.is_configured()
        if not is_ready:
            raise RuntimeError(message)

        client = self._get_client()
        if client is None:
            raise RuntimeError("Client Gemini tidak tersedia.")

        chat_model = os.getenv(self.ENV_GEMINI_CHAT_MODEL, self.DEFAULT_CHAT_MODEL).strip()
        if not chat_model:
            raise RuntimeError("GEMINI_CHAT_MODEL belum di-set.")

        context_blocks: list[str] = []
        for idx, item in enumerate(retrieved, start=1):
            chunk = item.chunk
            article_text = ", ".join(chunk.article_candidates[:5]) if chunk.article_candidates else "-"
            context_blocks.append(
                (
                    f"[{idx}] Dokumen: {chunk.title} | Kategori: {chunk.category} | "
                    f"Sumber: {chunk.source_relative_path} | Halaman: {chunk.page}\n"
                    f"Metadata: Instrumen: {chunk.instrument_type or '-'} | Kode: {chunk.code or chunk.number_year or '-'} | "
                    f"Tanggal: {chunk.issued_date or '-'} | Status Dokumen: {chunk.document_status_label} | Kandidat Pasal: {article_text}\n"
                    f"Isi: {chunk.text}"
                )
            )

        history_lines: list[str] = []
        for item in chat_history[-6:]:
            role = str(item.get("role") or "").strip().lower()
            content = str(item.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                role_label = "Pengguna" if role == "user" else "Asisten"
                history_lines.append(f"- {role_label}: {content[:450]}")

        history_block = "\n".join(history_lines) if history_lines else "(tidak ada riwayat)"

        prompt = (
            "Anda adalah asisten ahli regulasi pengadaan Bank Indonesia. "
            "Jawaban WAJIB berbasis konteks, analitis, dan dapat dipertanggungjawabkan. "
            "DILARANG membuat referensi regulasi yang tidak ada di konteks. "
            "Jika data tidak cukup, katakan secara eksplisit bahwa dasar belum memadai.\n\n"
            "FORMAT WAJIB OUTPUT (Markdown, gunakan heading persis):\n"
            "### Penjelasan Naratif\n"
            "### Kutipan Regulasi\n"
            "### Kesimpulan\n\n"
            "ATURAN VISUAL/FORMAT (WAJIB):\n"
            "- Gunakan **bold** untuk istilah kunci, keputusan akhir, dan frasa normatif penting.\n"
            "- Gunakan *italic* hanya untuk istilah asing/penekanan singkat, jangan berlebihan.\n"
            "- Gunakan bullet agar mudah dipindai (skimmable).\n"
            "- Hindari paragraf terlalu panjang; pecah jadi 2-4 paragraf ringkas atau bullet.\n\n"
            "ATURAN BAGIAN 1 - Penjelasan Naratif:\n"
            "- Jelaskan apakah istilah/objek pada pertanyaan disebut secara eksplisit atau tidak dalam konteks.\n"
            "- Jika tidak eksplisit, gunakan frasa: 'tidak disebut secara eksplisit, namun secara interpretatif termasuk dalam ...'.\n"
            "- Gunakan alur top-down: definisi -> cakupan aturan -> kesimpulan logis.\n"
            "- Tambahkan subbagian **Analisis Istilah Kunci** (1-3 bullet) untuk mencegah multi-tafsir istilah.\n"
            "- Prioritaskan presisi istilah regulasi literal dari sumber.\n"
            "- Hindari repetisi kalimat yang sama antara narasi dan kesimpulan.\n"
            "- Setiap klaim penting harus menyertakan sitasi [n] pada kalimat yang sama.\n\n"
            "ATURAN BAGIAN 2 - Kutipan Regulasi:\n"
            "- Hanya tampilkan kutipan literal (verbatim) dari konteks, jangan parafrase.\n"
            "- Untuk setiap kutipan, gunakan format bullet berikut:\n"
            "  - **Sumber [n]:** [Nama Dokumen], **Pasal/BAB:** [isi jika ada], **Halaman:** [nomor jika ada]\n"
            "    > \"<kutipan literal dari konteks>\"\n"
            "- Jika Pasal/BAB tidak tersedia di konteks, tulis: 'Pasal/BAB: tidak tersedia pada konteks'.\n\n"
            "ATURAN BAGIAN 3 - Kesimpulan:\n"
            "- Tulis verdict tegas dalam format **VERDICT: DAPAT DILAKUKAN / TIDAK DAPAT DILAKUKAN / BERSYARAT**.\n"
            "- Ringkas dalam 2-4 bullet yang konsisten dengan Penjelasan Naratif dan Kutipan Regulasi.\n\n"
            f"RIWAYAT CHAT (untuk konteks follow-up):\n{history_block}\n\n"
            f"PERTANYAAN:\n{question}\n\n"
            f"KONTEKS DOKUMEN BERNOMOR:\n{chr(10).join(context_blocks)}"
        )

        try:
            response = client.models.generate_content(model=chat_model, contents=prompt)
        except Exception as exc:
            raise RuntimeError(f"Gagal memanggil Gemini Chat Model: {exc}") from exc

        text = self._extract_response_text(response)
        if not text:
            raise RuntimeError("Respons model kosong. Coba ulangi pertanyaan dengan kata lain.")
        return text.strip()

    @staticmethod
    def build_source_preview(chunk: DocumentChunk) -> dict[str, Any]:
        article_part = ", ".join(chunk.article_candidates[:4]) if chunk.article_candidates else "-"
        quote = ChatbotService._extract_representative_sentence(chunk.text)
        article_snippets = ChatbotService._extract_article_snippets(chunk.text, chunk.article_candidates, max_items=4)
        return {
            "short_quote": quote,
            "article_list": article_part,
            "article_snippets": article_snippets,
            "document_status": chunk.document_status,
            "document_status_label": chunk.document_status_label,
        }

    @staticmethod
    def _extract_representative_sentence(text: str) -> str:
        if not text:
            return "-"
        sentences = re.split(r"(?<=[.!?;])\s+", text)
        for sentence in sentences:
            clean = sentence.strip()
            if len(clean) >= 80:
                return clean[:350]
        clean_text = text.strip()
        return clean_text[:350] if clean_text else "-"

    @staticmethod
    def _extract_article_snippets(text: str, article_candidates: list[str], max_items: int = 4) -> list[str]:
        if not text:
            return []

        snippets: list[str] = []
        seen: set[str] = set()
        for article in article_candidates[:max_items]:
            label = str(article).strip()
            if not label:
                continue

            match = re.compile(re.escape(label), flags=re.IGNORECASE).search(text)
            if match:
                start = max(match.start() - 40, 0)
                end = min(match.end() + 220, len(text))
                snippet = text[start:end].strip()
            else:
                snippet = ChatbotService._extract_representative_sentence(text)

            normalized_snippet = re.sub(r"\s+", " ", snippet)
            entry = f"{label}: {normalized_snippet[:260]}"
            if entry not in seen:
                seen.add(entry)
                snippets.append(entry)

        if not snippets:
            snippets.append(ChatbotService._extract_representative_sentence(text))
        return snippets

    def _get_client(self) -> Any | None:
        if self._client is not None:
            return self._client

        if not self._is_sdk_available():
            return None

        api_key = os.getenv(self.ENV_GEMINI_API_KEY, "").strip()
        if not api_key:
            return None

        from google import genai  # type: ignore

        self._client = genai.Client(api_key=api_key)
        return self._client

    @staticmethod
    def _is_sdk_available() -> bool:
        try:
            from google import genai  # type: ignore  # noqa: F401

            return True
        except Exception:
            return False

    def _embed_text(self, client: Any, model: str, text: str) -> list[float]:
        vectors = self._embed_texts(client, model, [text])
        return vectors[0] if vectors else []

    def _embed_texts(self, client: Any, model: str, texts: list[str]) -> list[list[float]]:
        response = client.models.embed_content(model=model, contents=texts)

        embeddings = getattr(response, "embeddings", None)
        if embeddings is None:
            embedding = getattr(response, "embedding", None)
            if embedding is not None:
                values = getattr(embedding, "values", None)
                if values:
                    return [list(values)]
            return []

        vectors: list[list[float]] = []
        for item in embeddings:
            values = getattr(item, "values", None)
            if values:
                vectors.append(list(values))
        return vectors

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        direct_text = getattr(response, "text", None)
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", None) or []
            texts: list[str] = []
            for part in parts:
                text = getattr(part, "text", None)
                if text:
                    texts.append(str(text))
            if texts:
                return "\n".join(texts)
        return ""
