from __future__ import annotations

import io
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import fitz
from PIL import Image
from pptx import Presentation
from pptx.util import Emu
from pdf2docx import Converter

from src.services.output_naming_service import OutputNamingService


class ConvertService:
    SUPPORTED_OPTIONS: dict[str, list[str]] = {
        ".pdf": ["docx", "pptx", "xlsx"],
        ".doc": ["pdf"],
        ".docx": ["pdf"],
        ".xls": ["pdf"],
        ".xlsx": ["pdf"],
        ".ppt": ["pdf"],
        ".pptx": ["pdf"],
        ".png": ["pdf"],
        ".jpg": ["pdf"],
        ".jpeg": ["pdf"],
        ".bmp": ["pdf"],
        ".webp": ["pdf"],
    }

    MIME_BY_EXT = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    @staticmethod
    def supports_office_to_pdf() -> bool:
        return sys.platform.startswith("win")

    @classmethod
    def get_available_targets(cls, filename: str) -> list[str]:
        source_ext = Path(filename).suffix.lower()
        targets = list(cls.SUPPORTED_OPTIONS.get(source_ext, []))
        if source_ext in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"} and not cls.supports_office_to_pdf():
            return []
        return targets

    @classmethod
    def get_available_targets_for_uploads(cls, uploads: list[Any]) -> list[str]:
        if not uploads:
            return []

        if len(uploads) == 1:
            return cls.get_available_targets(uploads[0].name)

        if any(Path(getattr(upload, "name", "")).suffix.lower() == ".pdf" for upload in uploads):
            return []

        common_targets = set(cls.get_available_targets(uploads[0].name))
        for upload in uploads[1:]:
            common_targets &= set(cls.get_available_targets(upload.name))

        if "pdf" in common_targets:
            return ["pdf"]
        return []

    @classmethod
    def convert_files(
        cls,
        uploads: list[Any],
        target_format: str,
        pdf_output_mode: str = "merge",
    ) -> tuple[io.BytesIO, str, str, str]:
        if not uploads:
            raise ValueError("Tidak ada file untuk dikonversi")

        if len(uploads) == 1:
            return cls.convert_file(uploads[0], target_format)

        target_format = target_format.lower()
        if target_format != "pdf":
            raise ValueError("Konversi multi-file saat ini hanya mendukung output PDF")
        if pdf_output_mode not in {"merge", "separate"}:
            raise ValueError("Mode output PDF tidak valid")

        outputs: list[tuple[str, bytes]] = []
        for upload in uploads:
            output, filename, _, _ = cls.convert_file(upload, target_format)
            outputs.append((filename, output.getvalue()))

        if pdf_output_mode == "merge":
            return cls._merge_pdf_outputs(outputs)
        return cls._package_pdf_outputs(outputs)

    @classmethod
    def convert_file(cls, upload: Any, target_format: str) -> tuple[io.BytesIO, str, str, str]:
        source_name = getattr(upload, "name", "document")
        source_ext = Path(source_name).suffix.lower()
        target_format = target_format.lower()

        if target_format not in cls.get_available_targets(source_name):
            raise ValueError(f"Konversi dari {source_ext or 'file ini'} ke {target_format.upper()} belum didukung")

        upload.seek(0)
        file_bytes = upload.read()

        if source_ext == ".pdf" and target_format == "docx":
            return cls._pdf_to_docx(file_bytes, source_name)
        if source_ext == ".pdf" and target_format == "pptx":
            return cls._pdf_to_pptx(file_bytes, source_name)
        if source_ext == ".pdf" and target_format == "xlsx":
            return cls._pdf_to_excel(file_bytes)
        if target_format == "pdf":
            return cls._convert_to_pdf(file_bytes, source_name)

        raise ValueError("Kombinasi konversi belum tersedia")

    @classmethod
    def _convert_to_pdf(cls, file_bytes: bytes, source_name: str) -> tuple[io.BytesIO, str, str, str]:
        source_ext = Path(source_name).suffix.lower()
        if source_ext in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}:
            return cls._office_to_pdf(file_bytes, source_name)
        if source_ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
            return cls._image_to_pdf(file_bytes, source_name)
        raise ValueError(f"Konversi dari {source_ext or 'file ini'} ke PDF belum didukung")

    @classmethod
    def _pdf_to_docx(cls, file_bytes: bytes, source_name: str) -> tuple[io.BytesIO, str, str, str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pdf_path = temp_path / source_name
            docx_path = temp_path / f"{Path(source_name).stem}.docx"
            pdf_path.write_bytes(file_bytes)

            converter = Converter(str(pdf_path))
            try:
                converter.convert(str(docx_path))
            finally:
                converter.close()

            output = io.BytesIO(docx_path.read_bytes())
            output.seek(0)
            return output, OutputNamingService.build_filename("converted_document", ".docx"), cls.MIME_BY_EXT["docx"], "PDF berhasil dikonversi ke Word (DOCX)."

    @classmethod
    def _pdf_to_pptx(cls, file_bytes: bytes, source_name: str) -> tuple[io.BytesIO, str, str, str]:
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        presentation = Presentation()
        presentation.slide_width = Emu(9144000)
        presentation.slide_height = Emu(5143500)

        blank_layout = presentation.slide_layouts[6]

        for page in pdf:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image_stream = io.BytesIO(pix.tobytes("png"))
            slide = presentation.slides.add_slide(blank_layout)
            slide.shapes.add_picture(
                image_stream,
                0,
                0,
                width=presentation.slide_width,
                height=presentation.slide_height,
            )

        if len(presentation.slides) > len(pdf):
            first_slide_id = presentation.slides._sldIdLst[0]
            presentation.slides._sldIdLst.remove(first_slide_id)

        output = io.BytesIO()
        presentation.save(output)
        output.seek(0)
        pdf.close()
        filename = OutputNamingService.build_filename("converted_document", ".pptx")
        return output, filename, cls.MIME_BY_EXT["pptx"], "PDF berhasil dikonversi ke PowerPoint (setiap halaman menjadi slide)."

    @classmethod
    def _image_to_pdf(cls, file_bytes: bytes, source_name: str) -> tuple[io.BytesIO, str, str, str]:
        with Image.open(io.BytesIO(file_bytes)) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="PDF", resolution=150.0)
            output.seek(0)
            filename = OutputNamingService.build_filename("converted_document", ".pdf")
            return output, filename, cls.MIME_BY_EXT["pdf"], "Gambar berhasil dikonversi ke PDF."

    @classmethod
    def _pdf_to_excel(cls, file_bytes: bytes) -> tuple[io.BytesIO, str, str, str]:
        import pandas as pd

        output = io.BytesIO()
        pdf = fitz.open(stream=file_bytes, filetype="pdf")

        try:
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                sheet_index = 1
                has_written_content = False

                for page_number, page in enumerate(pdf, start=1):
                    try:
                        table_finder = page.find_tables()
                        tables = table_finder.tables if table_finder else []
                    except Exception:
                        tables = []

                    for table in tables:
                        table_rows = table.extract() or []
                        cleaned_rows = [row for row in table_rows if any((cell or "").strip() for cell in row)]
                        if not cleaned_rows:
                            continue

                        header = [str(col).strip() if col is not None else "" for col in cleaned_rows[0]]
                        data_rows = cleaned_rows[1:] if len(cleaned_rows) > 1 else []
                        dataframe = pd.DataFrame(data_rows, columns=header)

                        sheet_name = f"Halaman_{page_number}_{sheet_index}"
                        dataframe.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                        sheet_index += 1
                        has_written_content = True

                if not has_written_content:
                    fallback_rows: list[dict[str, str]] = []
                    for page_number, page in enumerate(pdf, start=1):
                        text = page.get_text("text") or ""
                        lines = [line.strip() for line in text.splitlines() if line.strip()]
                        for line_number, line in enumerate(lines, start=1):
                            fallback_rows.append(
                                {
                                    "halaman": str(page_number),
                                    "baris": str(line_number),
                                    "teks": line,
                                }
                            )

                    fallback_df = pd.DataFrame(fallback_rows or [{"halaman": "", "baris": "", "teks": ""}])
                    fallback_df.to_excel(writer, sheet_name="PDF_Text", index=False)
        finally:
            pdf.close()

        output.seek(0)
        filename = OutputNamingService.build_filename("converted_document", ".xlsx")
        return (
            output,
            filename,
            cls.MIME_BY_EXT["xlsx"],
            "PDF berhasil dikonversi ke Excel (tabel terdeteksi otomatis; jika tidak ada tabel, teks diekspor).",
        )

    @classmethod
    def _office_to_pdf(cls, file_bytes: bytes, source_name: str) -> tuple[io.BytesIO, str, str, str]:
        if not cls.supports_office_to_pdf():
            raise RuntimeError("Konversi Office ke PDF hanya tersedia di Windows yang memiliki Microsoft Office desktop.")

        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise ImportError("Dependensi Windows untuk konversi Office belum tersedia.") from exc

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / source_name
            output_path = temp_path / f"{Path(source_name).stem}.pdf"
            source_path.write_bytes(file_bytes)
            source_ext = source_path.suffix.lower()

            pythoncom.CoInitialize()
            try:
                if source_ext in {".doc", ".docx"}:
                    cls._word_to_pdf(source_path, output_path, win32com.client)
                elif source_ext in {".xls", ".xlsx"}:
                    cls._excel_to_pdf(source_path, output_path, win32com.client)
                elif source_ext in {".ppt", ".pptx"}:
                    cls._powerpoint_to_pdf(source_path, output_path, win32com.client)
                else:
                    raise ValueError("Format Office belum didukung")
            except Exception as exc:
                raise RuntimeError(
                    "Konversi Office ke PDF membutuhkan Microsoft Office desktop terpasang di Windows."
                ) from exc
            finally:
                pythoncom.CoUninitialize()

            output = io.BytesIO(output_path.read_bytes())
            output.seek(0)
            return output, OutputNamingService.build_filename("converted_document", ".pdf"), cls.MIME_BY_EXT["pdf"], "File Office berhasil dikonversi ke PDF."

    @classmethod
    def _merge_pdf_outputs(cls, outputs: list[tuple[str, bytes]]) -> tuple[io.BytesIO, str, str, str]:
        merged_pdf = fitz.open()
        try:
            for _, pdf_bytes in outputs:
                source_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
                try:
                    merged_pdf.insert_pdf(source_pdf)
                finally:
                    source_pdf.close()

            output = io.BytesIO(merged_pdf.tobytes())
            output.seek(0)
            return (
                output,
                OutputNamingService.build_filename("converted_document", ".pdf"),
                cls.MIME_BY_EXT["pdf"],
                f"{len(outputs)} file berhasil dikonversi dan digabung menjadi 1 PDF.",
            )
        finally:
            merged_pdf.close()

    @classmethod
    def _package_pdf_outputs(cls, outputs: list[tuple[str, bytes]]) -> tuple[io.BytesIO, str, str, str]:
        outputs = OutputNamingService.anonymize_named_payloads(outputs, "converted_document", ".pdf")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for filename, file_bytes in outputs:
                archive.writestr(filename, file_bytes)
        zip_buffer.seek(0)
        return (
            zip_buffer,
            OutputNamingService.build_filename("converted_documents", ".zip"),
            "application/zip",
            f"{len(outputs)} file berhasil dikonversi menjadi PDF terpisah.",
        )

    @staticmethod
    def _word_to_pdf(source_path: Path, output_path: Path, client_module: Any) -> None:
        word = client_module.DispatchEx("Word.Application")
        word.Visible = False
        document = None
        try:
            document = word.Documents.Open(str(source_path))
            document.SaveAs(str(output_path), FileFormat=17)
        finally:
            if document is not None:
                document.Close(False)
            word.Quit()

    @staticmethod
    def _excel_to_pdf(source_path: Path, output_path: Path, client_module: Any) -> None:
        excel = client_module.DispatchEx("Excel.Application")
        excel.Visible = False
        workbook = None
        try:
            workbook = excel.Workbooks.Open(str(source_path))
            workbook.ExportAsFixedFormat(0, str(output_path))
        finally:
            if workbook is not None:
                workbook.Close(False)
            excel.Quit()

    @staticmethod
    def _powerpoint_to_pdf(source_path: Path, output_path: Path, client_module: Any) -> None:
        powerpoint = client_module.DispatchEx("PowerPoint.Application")
        presentation = None
        try:
            presentation = powerpoint.Presentations.Open(str(source_path), WithWindow=False)
            presentation.SaveAs(str(output_path), 32)
        finally:
            if presentation is not None:
                presentation.Close()
            powerpoint.Quit()
