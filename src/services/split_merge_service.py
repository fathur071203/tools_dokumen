from __future__ import annotations

import io
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import fitz
from pypdf import PdfReader, PdfWriter

from src.services.output_naming_service import OutputNamingService


class SplitMergeService:
    @staticmethod
    def supports_office_automation() -> bool:
        return sys.platform.startswith("win")

    @staticmethod
    def get_family(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return "pdf"
        if ext in {".doc", ".docx"}:
            return "word"
        if ext in {".ppt", ".pptx"}:
            return "ppt"
        return "unsupported"

    @classmethod
    def get_supported_modes(cls, uploads: list[Any]) -> list[str]:
        if not uploads:
            return []
        if len(uploads) == 1:
            family = cls.get_family(uploads[0].name)
            if family in {"word", "ppt"} and not cls.supports_office_automation():
                return []
            return ["split"] if family in {"pdf", "word", "ppt"} else []

        families = {cls.get_family(upload.name) for upload in uploads}
        if len(families) == 1:
            family = next(iter(families))
            if family in {"word", "ppt"} and not cls.supports_office_automation():
                return []
            if family in {"pdf", "word", "ppt"}:
                return ["merge"]
        return []

    @staticmethod
    def parse_groups(pattern_text: str) -> list[list[int]]:
        groups: list[list[int]] = []
        lines = [line.strip() for line in pattern_text.splitlines() if line.strip()]
        if not lines:
            raise ValueError("Pola halaman/slides belum diisi")

        for line in lines:
            pages: list[int] = []
            for token in [item.strip() for item in line.split(",") if item.strip()]:
                if "-" in token:
                    start_text, end_text = token.split("-", 1)
                    start_num = int(start_text)
                    end_num = int(end_text)
                    if start_num > end_num:
                        raise ValueError(f"Range tidak valid: {token}")
                    pages.extend(range(start_num, end_num + 1))
                else:
                    pages.append(int(token))
            if not pages:
                raise ValueError(f"Baris tidak valid: {line}")
            groups.append(pages)
        return groups

    @staticmethod
    def build_generated_groups(
        master_start: int,
        master_end: int,
        variable_start: int,
        variable_end: int,
        pages_per_output: int = 1,
        step: int = 1,
    ) -> list[list[int]]:
        if master_start < 1 or master_end < 1 or variable_start < 1 or variable_end < 1:
            raise ValueError("Nomor halaman/slide harus dimulai dari 1")
        if master_start > master_end:
            raise ValueError("Range master tidak valid")
        if variable_start > variable_end:
            raise ValueError("Range tambahan tidak valid")
        if pages_per_output < 1:
            raise ValueError("Jumlah halaman tambahan per output minimal 1")
        if step < 1:
            raise ValueError("Step minimal 1")

        master_pages = list(range(master_start, master_end + 1))
        variable_pages = list(range(variable_start, variable_end + 1))
        groups: list[list[int]] = []

        start_index = 0
        while start_index < len(variable_pages):
            chunk = variable_pages[start_index:start_index + pages_per_output]
            if not chunk:
                break
            groups.append(master_pages + chunk)
            start_index += step

        if not groups:
            raise ValueError("Generator tidak menghasilkan pola apa pun")
        return groups

    @staticmethod
    def groups_to_text(groups: list[list[int]]) -> str:
        return "\n".join(",".join(str(page) for page in group) for group in groups)

    @classmethod
    def estimate_total_units(cls, upload: Any) -> tuple[int, str]:
        family = cls.get_family(upload.name)
        if family == "pdf":
            upload.seek(0)
            reader = PdfReader(io.BytesIO(upload.read()))
            return len(reader.pages), "halaman"
        if family == "word":
            return cls._word_page_count(upload), "halaman"
        if family == "ppt":
            return cls._ppt_slide_count(upload), "slide"
        raise ValueError("Format file belum didukung untuk estimasi")

    @staticmethod
    def build_output_preview(groups: list[list[int]], output_names: list[str] | None = None) -> list[dict[str, str | int]]:
        preview_rows: list[dict[str, str | int]] = []
        output_names = output_names or []
        for index, group in enumerate(groups, start=1):
            suggested_name = output_names[index - 1] if index - 1 < len(output_names) else f"part_{index}"
            preview_rows.append(
                {
                    "No": index,
                    "Isi Halaman": ", ".join(str(page) for page in group),
                    "Jumlah Halaman": len(group),
                    "Nama Output": suggested_name,
                }
            )
        return preview_rows

    @classmethod
    def split_document(
        cls,
        upload: Any,
        pattern_text: str,
        output_names: list[str] | None = None,
    ) -> tuple[io.BytesIO, str, str, str]:
        family = cls.get_family(upload.name)
        groups = cls.parse_groups(pattern_text)
        if family == "pdf":
            return cls._split_pdf(upload, groups, output_names)
        if family == "word":
            return cls._split_word_to_pdf(upload, groups, output_names)
        if family == "ppt":
            return cls._split_ppt(upload, groups, output_names)
        raise ValueError("Format file belum didukung untuk split")

    def merge_documents(
        cls,
        uploads: list[Any],
        merge_page_rules: list[str] | None = None,
    ) -> tuple[io.BytesIO, str, str, str]:
        if len(uploads) < 2:
            raise ValueError("Gabung dokumen membutuhkan minimal 2 file")
        family = cls.get_family(uploads[0].name)
        if any(cls.get_family(upload.name) != family for upload in uploads):
            raise ValueError("Semua file harus bertipe sama untuk digabung")

        if family == "pdf":
            return cls._merge_pdf(uploads, merge_page_rules)
        if family == "word":
            return cls._merge_word(uploads)
        if family == "ppt":
            return cls._merge_ppt(uploads)
        raise ValueError("Format file belum didukung untuk merge")

    @staticmethod
    def parse_page_selection_rule(total_pages: int, rule_text: str | None) -> list[int]:
        if total_pages < 1:
            return []

        raw = (rule_text or "").strip().lower()
        if not raw or raw in {"all", "*", "semua"}:
            return list(range(1, total_pages + 1))

        pages: list[int] = []
        seen: set[int] = set()
        tokens = [token.strip() for token in raw.split(",") if token.strip()]
        if not tokens:
            raise ValueError("Rule halaman kosong")

        for token in tokens:
            if "-" in token:
                start_text, end_text = token.split("-", 1)
                start = int(start_text)
                end = int(end_text)
                if start > end:
                    raise ValueError(f"Range tidak valid: {token}")
                for number in range(start, end + 1):
                    if number < 1 or number > total_pages:
                        raise ValueError(f"Halaman {number} di luar total halaman ({total_pages})")
                    if number not in seen:
                        seen.add(number)
                        pages.append(number)
            else:
                number = int(token)
                if number < 1 or number > total_pages:
                    raise ValueError(f"Halaman {number} di luar total halaman ({total_pages})")
                if number not in seen:
                    seen.add(number)
                    pages.append(number)

        if not pages:
            raise ValueError("Tidak ada halaman yang dipilih untuk merge")
        return pages

    @staticmethod
    def _split_pdf(upload: Any, groups: list[list[int]], output_names: list[str] | None = None) -> tuple[io.BytesIO, str, str, str]:
        upload.seek(0)
        reader = PdfReader(io.BytesIO(upload.read()))
        total_pages = len(reader.pages)
        outputs: list[tuple[str, bytes]] = []
        base_name = Path(upload.name).stem

        for index, group in enumerate(groups, start=1):
            writer = PdfWriter()
            for page_num in group:
                if page_num < 1 or page_num > total_pages:
                    raise ValueError(f"Halaman {page_num} di luar total halaman PDF ({total_pages})")
                writer.add_page(reader.pages[page_num - 1])
            out = io.BytesIO()
            writer.write(out)
            outputs.append((SplitMergeService._build_output_filename(base_name, index, output_names, ".pdf"), out.getvalue()))

        return SplitMergeService._package_outputs(outputs, f"{base_name}_split", "PDF berhasil di-split.")

    @staticmethod
    def _merge_pdf(
        uploads: list[Any],
        merge_page_rules: list[str] | None = None,
    ) -> tuple[io.BytesIO, str, str, str]:
        writer = PdfWriter()
        selected_summary: list[str] = []

        for index, upload in enumerate(uploads):
            upload.seek(0)
            reader = PdfReader(io.BytesIO(upload.read()))
            total_pages = len(reader.pages)
            rule = merge_page_rules[index] if merge_page_rules and index < len(merge_page_rules) else "all"
            selected_pages = SplitMergeService.parse_page_selection_rule(total_pages, rule)

            for page_number in selected_pages:
                writer.add_page(reader.pages[page_number - 1])

            selected_summary.append(f"{Path(upload.name).name}: {len(selected_pages)}/{total_pages} halaman")

        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        return (
            out,
            OutputNamingService.build_filename("merged_document", ".pdf"),
            "application/pdf",
            "PDF berhasil digabung. " + " | ".join(selected_summary),
        )

    @staticmethod
    def _split_word_to_pdf(upload: Any, groups: list[list[int]], output_names: list[str] | None = None) -> tuple[io.BytesIO, str, str, str]:
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise ImportError("pywin32 belum tersedia untuk proses Word") from exc

        base_name = Path(upload.name).stem
        outputs: list[tuple[str, bytes]] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / upload.name
            upload.seek(0)
            source_path.write_bytes(upload.read())

            pythoncom.CoInitialize()
            word = None
            document = None
            try:
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                document = word.Documents.Open(str(source_path))

                for index, group in enumerate(groups, start=1):
                    page_pdf_paths: list[Path] = []
                    for page_num in group:
                        page_pdf_path = temp_path / f"tmp_{index}_{page_num}.pdf"
                        document.ExportAsFixedFormat(
                            OutputFileName=str(page_pdf_path),
                            ExportFormat=17,
                            OpenAfterExport=False,
                            OptimizeFor=0,
                            Range=3,
                            From=page_num,
                            To=page_num,
                            Item=0,
                            IncludeDocProps=True,
                            KeepIRM=True,
                            CreateBookmarks=0,
                            DocStructureTags=True,
                            BitmapMissingFonts=True,
                            UseISO19005_1=False,
                        )
                        if not page_pdf_path.exists():
                            raise ValueError(f"Halaman {page_num} tidak ditemukan pada dokumen Word")
                        page_pdf_paths.append(page_pdf_path)

                    writer = PdfWriter()
                    for page_pdf_path in page_pdf_paths:
                        reader = PdfReader(str(page_pdf_path))
                        for page in reader.pages:
                            writer.add_page(page)
                    out = io.BytesIO()
                    writer.write(out)
                    outputs.append((SplitMergeService._build_output_filename(base_name, index, output_names, ".pdf"), out.getvalue()))
            finally:
                if document is not None:
                    document.Close(False)
                if word is not None:
                    word.Quit()
                pythoncom.CoUninitialize()

        return SplitMergeService._package_outputs(
            outputs,
            f"{base_name}_split",
            "Dokumen Word berhasil di-split ke PDF per pola halaman."
        )

    @staticmethod
    def _merge_word(uploads: list[Any]) -> tuple[io.BytesIO, str, str, str]:
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise ImportError("pywin32 belum tersedia untuk proses Word") from exc

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_paths: list[Path] = []
            for upload in uploads:
                source_path = temp_path / upload.name
                upload.seek(0)
                source_path.write_bytes(upload.read())
                source_paths.append(source_path)

            output_path = temp_path / "merged_document.docx"

            pythoncom.CoInitialize()
            word = None
            document = None
            try:
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                document = word.Documents.Open(str(source_paths[0]))
                selection = word.Selection
                selection.EndKey(Unit=6)
                for path in source_paths[1:]:
                    selection.InsertBreak()
                    selection.InsertFile(str(path))
                    selection.EndKey(Unit=6)
                document.SaveAs2(str(output_path), FileFormat=16)
            finally:
                if document is not None:
                    document.Close(False)
                if word is not None:
                    word.Quit()
                pythoncom.CoUninitialize()

            output = io.BytesIO(output_path.read_bytes())
            output.seek(0)
            return output, OutputNamingService.build_filename("merged_document", ".docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Dokumen Word berhasil digabung."

    @staticmethod
    def _split_ppt(upload: Any, groups: list[list[int]], output_names: list[str] | None = None) -> tuple[io.BytesIO, str, str, str]:
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise ImportError("pywin32 belum tersedia untuk proses PowerPoint") from exc

        base_name = Path(upload.name).stem
        outputs: list[tuple[str, bytes]] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / upload.name
            upload.seek(0)
            source_path.write_bytes(upload.read())

            pythoncom.CoInitialize()
            app = None
            source_presentation = None
            try:
                app = win32com.client.DispatchEx("PowerPoint.Application")
                source_presentation = app.Presentations.Open(str(source_path), WithWindow=False)
                total_slides = source_presentation.Slides.Count

                for index, group in enumerate(groups, start=1):
                    target = app.Presentations.Add()
                    try:
                        for slide_num in group:
                            if slide_num < 1 or slide_num > total_slides:
                                raise ValueError(f"Slide {slide_num} di luar total slide PPT ({total_slides})")
                            target.Slides.InsertFromFile(str(source_path), target.Slides.Count, slide_num, slide_num)
                        output_filename = SplitMergeService._build_output_filename(base_name, index, output_names, ".pptx")
                        output_path = temp_path / output_filename
                        target.SaveAs(str(output_path), 24)
                        outputs.append((output_path.name, output_path.read_bytes()))
                    finally:
                        target.Close()
            finally:
                if source_presentation is not None:
                    source_presentation.Close()
                if app is not None:
                    app.Quit()
                pythoncom.CoUninitialize()

        return SplitMergeService._package_outputs(outputs, f"{base_name}_split", "PowerPoint berhasil di-split per pola slide.")

    @staticmethod
    def _merge_ppt(uploads: list[Any]) -> tuple[io.BytesIO, str, str, str]:
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise ImportError("pywin32 belum tersedia untuk proses PowerPoint") from exc

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_paths: list[Path] = []
            for upload in uploads:
                source_path = temp_path / upload.name
                upload.seek(0)
                source_path.write_bytes(upload.read())
                source_paths.append(source_path)

            output_path = temp_path / "merged_presentation.pptx"

            pythoncom.CoInitialize()
            app = None
            target = None
            try:
                app = win32com.client.DispatchEx("PowerPoint.Application")
                target = app.Presentations.Add()
                for source_path in source_paths:
                    probe = app.Presentations.Open(str(source_path), WithWindow=False)
                    try:
                        slide_count = probe.Slides.Count
                    finally:
                        probe.Close()
                    if slide_count > 0:
                        target.Slides.InsertFromFile(str(source_path), target.Slides.Count, 1, slide_count)
                target.SaveAs(str(output_path), 24)
            finally:
                if target is not None:
                    target.Close()
                if app is not None:
                    app.Quit()
                pythoncom.CoUninitialize()

            output = io.BytesIO(output_path.read_bytes())
            output.seek(0)
            return output, OutputNamingService.build_filename("merged_presentation", ".pptx"), "application/vnd.openxmlformats-officedocument.presentationml.presentation", "PowerPoint berhasil digabung."

    @staticmethod
    def _package_outputs(outputs: list[tuple[str, bytes]], base_name: str, success_message: str) -> tuple[io.BytesIO, str, str, str]:
        outputs = SplitMergeService._dedupe_output_names(outputs)
        if len(outputs) == 1:
            filename, file_bytes = outputs[0]
            buffer = io.BytesIO(file_bytes)
            buffer.seek(0)
            mime = SplitMergeService._mime_for_filename(filename)
            return buffer, filename, mime, success_message

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for filename, file_bytes in outputs:
                archive.writestr(filename, file_bytes)
        zip_buffer.seek(0)
        return zip_buffer, OutputNamingService.build_filename("processed_parts", ".zip"), "application/zip", success_message

    @staticmethod
    def _mime_for_filename(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return "application/pdf"
        if ext == ".docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if ext == ".pptx":
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        return "application/octet-stream"

    @staticmethod
    def _sanitize_name(name: str) -> str:
        sanitized = "".join(char for char in name.strip() if char not in '<>:"/\\|?*')
        return sanitized or "output"

    @classmethod
    def _build_output_filename(
        cls,
        base_name: str,
        index: int,
        output_names: list[str] | None,
        extension: str,
    ) -> str:
        extension = extension if extension.startswith(".") else f".{extension}"
        if output_names and index - 1 < len(output_names):
            candidate = cls._sanitize_name(str(output_names[index - 1] or "").strip())
            if candidate and candidate != "output":
                if candidate.lower().endswith(extension.lower()):
                    return candidate
                return f"{candidate}{extension}"

        return OutputNamingService.build_filename(base_name, extension, index=index)

    @classmethod
    def _dedupe_output_names(cls, outputs: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
        used_names: set[str] = set()
        deduped: list[tuple[str, bytes]] = []

        for filename, file_bytes in outputs:
            candidate = cls._sanitize_name(Path(filename).stem)
            extension = Path(filename).suffix or ".bin"
            final_name = f"{candidate}{extension}"
            suffix = 2
            while final_name.lower() in used_names:
                final_name = f"{candidate}_{suffix}{extension}"
                suffix += 1
            used_names.add(final_name.lower())
            deduped.append((final_name, file_bytes))

        return deduped

    @staticmethod
    def _word_page_count(upload: Any) -> int:
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise ImportError("pywin32 belum tersedia untuk estimasi Word") from exc

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / upload.name
            upload.seek(0)
            source_path.write_bytes(upload.read())

            pythoncom.CoInitialize()
            word = None
            document = None
            try:
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                document = word.Documents.Open(str(source_path))
                document.Repaginate()
                return int(document.ComputeStatistics(2))
            finally:
                if document is not None:
                    document.Close(False)
                if word is not None:
                    word.Quit()
                pythoncom.CoUninitialize()

    @staticmethod
    def _ppt_slide_count(upload: Any) -> int:
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise ImportError("pywin32 belum tersedia untuk estimasi PowerPoint") from exc

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / upload.name
            upload.seek(0)
            source_path.write_bytes(upload.read())

            pythoncom.CoInitialize()
            app = None
            presentation = None
            try:
                app = win32com.client.DispatchEx("PowerPoint.Application")
                presentation = app.Presentations.Open(str(source_path), WithWindow=False)
                return int(presentation.Slides.Count)
            finally:
                if presentation is not None:
                    presentation.Close()
                if app is not None:
                    app.Quit()
                pythoncom.CoUninitialize()

    @classmethod
    def build_pdf_preview_images(
        cls,
        upload: Any,
        max_pages: int = 3,
        zoom: float = 1.1,
    ) -> list[bytes]:
        """Render preview halaman PDF sebagai PNG agar stabil di browser (tanpa iframe PDF embed)."""
        if max_pages < 1:
            return []
        if cls.get_family(getattr(upload, "name", "")) != "pdf":
            return []

        upload.seek(0)
        pdf_bytes = upload.read()
        if not pdf_bytes:
            return []

        previews: list[bytes] = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            matrix = fitz.Matrix(zoom, zoom)
            page_count = min(max_pages, doc.page_count)
            for page_index in range(page_count):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                previews.append(pix.tobytes("png"))
            return previews
        finally:
            doc.close()

    @classmethod
    def build_pdf_input_page_preview_image(
        cls,
        upload: Any,
        page_number: int,
        zoom: float = 1.15,
    ) -> bytes | None:
        """Render satu halaman PDF input sebagai PNG untuk preview merge."""
        if cls.get_family(getattr(upload, "name", "")) != "pdf":
            return None
        if page_number < 1:
            return None

        upload.seek(0)
        pdf_bytes = upload.read()
        if not pdf_bytes:
            return None

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            if page_number > doc.page_count:
                return None
            page = doc.load_page(page_number - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            return pix.tobytes("png")
        finally:
            doc.close()

    @classmethod
    def build_pdf_merge_preview_images(
        cls,
        uploads: list[Any],
        merge_page_rules: list[str] | None = None,
        zoom: float = 1.15,
        max_pages: int = 12,
    ) -> list[tuple[str, int, bytes]]:
        """Render preview output merge PDF sesuai urutan hasil gabungan."""
        if max_pages < 1:
            return []

        previews: list[tuple[str, int, bytes]] = []
        for index, upload in enumerate(uploads):
            if len(previews) >= max_pages:
                break
            if cls.get_family(getattr(upload, "name", "")) != "pdf":
                return []

            upload.seek(0)
            pdf_bytes = upload.read()
            if not pdf_bytes:
                continue

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            try:
                total_pages = doc.page_count
                rule = merge_page_rules[index] if merge_page_rules and index < len(merge_page_rules) else "all"
                selected_pages = cls.parse_page_selection_rule(total_pages, rule)

                for page_number in selected_pages:
                    if len(previews) >= max_pages:
                        break
                    if page_number < 1 or page_number > total_pages:
                        continue
                    page = doc.load_page(page_number - 1)
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                    previews.append((Path(upload.name).name, page_number, pix.tobytes("png")))
            finally:
                doc.close()

        return previews

    @classmethod
    def build_pdf_split_output_preview_images(
        cls,
        upload: Any,
        group: list[int],
        zoom: float = 1.15,
    ) -> list[tuple[int, bytes]]:
        """Render preview per halaman untuk satu output split PDF tertentu."""
        if cls.get_family(getattr(upload, "name", "")) != "pdf":
            return []
        if not group:
            return []

        upload.seek(0)
        pdf_bytes = upload.read()
        if not pdf_bytes:
            return []

        previews: list[tuple[int, bytes]] = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            matrix = fitz.Matrix(zoom, zoom)
            for page_num in group:
                if page_num < 1 or page_num > doc.page_count:
                    continue
                page = doc.load_page(page_num - 1)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                previews.append((page_num, pix.tobytes("png")))
            return previews
        finally:
            doc.close()
