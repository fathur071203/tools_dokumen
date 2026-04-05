import zipfile
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, UnidentifiedImageError

from src.services.output_naming_service import OutputNamingService


class CompressService:
    """Service untuk mengkompres file dengan metode optimal"""

    MODE_SAFE = "safe"
    MODE_BALANCED = "balanced"
    MODE_AGGRESSIVE = "aggressive"

    PDF_METHOD_AUTO = "auto"
    PDF_METHOD_GHOSTSCRIPT = "ghostscript"
    PDF_METHOD_PYMUPDF = "pymupdf"

    COMPRESSED_EXTENSIONS = {
        ".zip", ".7z", ".rar", ".gz", ".bz2", ".xz",
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".mp4", ".mkv", ".avi", ".mov", ".mp3", ".aac",
    }
    TEXT_EXTENSIONS = {
        ".txt", ".csv", ".json", ".xml", ".html", ".htm", ".md", ".log",
        ".py", ".js", ".css", ".csv", ".ts", ".xml", ".yaml", ".yml",
    }
    OFFICE_EXTENSIONS = {
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    }

    GHOSTSCRIPT_EXECUTABLE_CANDIDATES = (
        "gswin64c.exe",
        "gswin32c.exe",
        "gs",
    )

    _last_pdf_method_used = "-"

    @staticmethod
    def estimate_compressed_size(files: list, compression_mode: str = MODE_BALANCED) -> tuple[int, int, int]:
        """Estimasi ukuran hasil kompresi (estimasi, bukan ukuran final)."""
        if not files:
            return 0, 0, 0

        total_size = 0
        estimated_size = 0.0

        for file in files:
            size = int(getattr(file, "size", 0) or 0)
            total_size += size
            ext = Path(getattr(file, "name", "")).suffix.lower()
            estimated_size += size * CompressService._estimate_ratio_for_extension(ext, compression_mode, len(files))

        # overhead archive / metadata
        overhead = max(int(total_size * 0.02), 12 * 1024)
        estimated_size += overhead

        low = int(estimated_size * 0.90)
        high = int(estimated_size * 1.10)
        return max(0, int(estimated_size)), max(0, low), max(0, high)

    @staticmethod
    def _estimate_ratio_for_extension(ext: str, compression_mode: str, file_count: int) -> float:
        mode = CompressService._normalize_mode(compression_mode)

        if mode == CompressService.MODE_SAFE:
            if ext in CompressService.COMPRESSED_EXTENSIONS:
                return 0.985
            if ext in CompressService.TEXT_EXTENSIONS:
                return 0.62
            if ext in CompressService.OFFICE_EXTENSIONS:
                return 0.92 if file_count == 1 else 0.88
            if ext in {".bmp", ".tif", ".tiff"}:
                return 0.78
            return 0.92

        if mode == CompressService.MODE_BALANCED:
            if ext in CompressService.COMPRESSED_EXTENSIONS:
                return 0.975
            if ext in CompressService.TEXT_EXTENSIONS:
                return 0.35
            if ext in CompressService.OFFICE_EXTENSIONS:
                if file_count == 1 and ext == ".pptx":
                    return 0.64
                if file_count == 1 and ext == ".pdf":
                    return 0.76
                return 0.68
            if ext in {".bmp", ".tif", ".tiff"}:
                return 0.56
            return 0.80

        # aggressive
        if ext in CompressService.COMPRESSED_EXTENSIONS:
            return 0.96
        if ext in CompressService.TEXT_EXTENSIONS:
            return 0.24
        if ext in CompressService.OFFICE_EXTENSIONS:
            if file_count == 1 and ext == ".pptx":
                return 0.48
            if file_count == 1 and ext == ".pdf":
                return 0.58
            return 0.56
        if ext in {".bmp", ".tif", ".tiff"}:
            return 0.42
        return 0.68

    @staticmethod
    def _normalize_mode(compression_mode: str) -> str:
        mode = str(compression_mode or CompressService.MODE_BALANCED).strip().lower()
        if mode not in {CompressService.MODE_SAFE, CompressService.MODE_BALANCED, CompressService.MODE_AGGRESSIVE}:
            return CompressService.MODE_BALANCED
        return mode

    @staticmethod
    def _classify_image_bytes(data: bytes) -> str:
        """Klasifikasikan gambar menjadi 'photo' atau 'graphic' berdasarkan karakteristik visual."""
        try:
            with Image.open(io.BytesIO(data)) as img:
                img = ImageOps.exif_transpose(img)
                width, height = img.size

                # Transparansi / palet warna / jumlah warna kecil -> cenderung grafik, diagram, atau teks
                if img.mode in {"1", "P", "LA", "RGBA"}:
                    return "graphic"

                if width * height <= 900_000:
                    sample = img.copy()
                    if sample.mode not in ("RGB", "RGBA"):
                        sample = sample.convert("RGB")
                    colors = sample.getcolors(maxcolors=512)
                    if colors is not None and len(colors) <= 64:
                        return "graphic"

                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                # Thumbnail kecil untuk cek kekayaan warna tanpa mahal
                thumb = img.copy()
                thumb.thumbnail((96, 96), Image.Resampling.BILINEAR)
                colors = thumb.getcolors(maxcolors=1024)
                if colors is not None and len(colors) <= 128:
                    return "graphic"

                return "photo"
        except Exception:
            return "photo"

    @staticmethod
    def _safe_image_save(
        img: Image.Image,
        source_ext: str,
    ) -> bytes:
        """Optimasi aman: pertahankan format sejauh mungkin, hanya compress/optimize."""
        out = io.BytesIO()
        ext = source_ext.lower().lstrip(".")

        if ext in {"jpg", "jpeg"}:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(out, format="JPEG", quality=95, optimize=True, progressive=True)
            return out.getvalue()

        if ext == "webp":
            img.save(out, format="WEBP", quality=92, method=6)
            return out.getvalue()

        # PNG dan lainnya: tetap PNG agar grafik/teks tetap aman
        if img.mode == "P":
            img = img.convert("RGBA")
        elif img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGBA")
        img.save(out, format="PNG", optimize=True, compress_level=9)
        return out.getvalue()

    @staticmethod
    def _adaptive_image_compress(
        data: bytes,
        source_ext: str,
        mode: str,
        max_dim: int,
        jpeg_quality: int,
    ) -> bytes:
        """Adaptive compression: grafik/text aman, foto boleh lossy."""
        try:
            with Image.open(io.BytesIO(data)) as img:
                img = ImageOps.exif_transpose(img)
                mode_norm = CompressService._normalize_mode(mode)
                image_kind = CompressService._classify_image_bytes(data)

                # Mode aman: jangan resize agresif, fokus pada optimasi format yang aman.
                if mode_norm == CompressService.MODE_SAFE:
                    if max(img.size) > 4096:
                        img.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
                    optimized = CompressService._safe_image_save(img, source_ext)
                    return optimized if optimized and len(optimized) < len(data) else data

                # Seimbang/aggressive: resize hanya jika perlu.
                if max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                out = io.BytesIO()

                if image_kind == "graphic":
                    # Grafik / text-like: pertahankan PNG/WEBP agar garis & teks tetap tajam.
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    if source_ext.lower().lstrip(".") == "webp":
                        img.save(out, format="WEBP", quality=92, method=6)
                    else:
                        img.save(out, format="PNG", optimize=True, compress_level=9)
                else:
                    # Foto: baru boleh lossy.
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    if source_ext.lower().lstrip(".") == "webp":
                        img.save(out, format="WEBP", quality=max(75, jpeg_quality), method=6)
                    else:
                        img.save(
                            out,
                            format="JPEG",
                            quality=jpeg_quality,
                            optimize=True,
                            progressive=True,
                        )

                optimized = out.getvalue()
                return optimized if optimized and len(optimized) < len(data) else data
        except (UnidentifiedImageError, OSError, ValueError):
            return data
    
    @staticmethod
    def compress_files(
        files: list,
        compression_mode: str = MODE_BALANCED,
        pdf_method: str = PDF_METHOD_AUTO,
        use_7z: bool = True,
    ) -> tuple[io.BytesIO, str, bool]:
        """
        Kompres file(s) menggunakan metode optimal.
        - Jika 1 file: tetap dikompres ke archive (7z/zip), bukan file asli
        - Jika > 1 file: return ZIP atau 7Z dengan semua file
        
        Args:
            files: List of uploaded files dari streamlit
            compression_level: Level kompres (1-9, default 9)
            use_7z: Gunakan 7z format (default True, lebih optimal)
            
        Returns:
            Tuple of (BytesIO object, filename, is_compressed)
        """
        if not files:
            raise ValueError("Tidak ada file untuk dikompres")

        mode = CompressService._normalize_mode(compression_mode)
        compression_level = {
            CompressService.MODE_SAFE: 3,
            CompressService.MODE_BALANCED: 6,
            CompressService.MODE_AGGRESSIVE: 9,
        }[mode]

        if len(files) == 1:
            single_name = getattr(files[0], "name", "file")

            # Metode khusus PPTX: kompres gambar di dalam PPT lalu pack ulang ke PPTX
            if single_name.lower().endswith(".pptx"):
                return CompressService._compress_single_pptx(files[0], compression_level, mode)
            
            # Metode khusus PDF: kompres gambar di dalam PDF lalu simpan kembali
            if single_name.lower().endswith(".pdf"):
                selected_pdf_method = CompressService._normalize_pdf_method(pdf_method)

                if selected_pdf_method == CompressService.PDF_METHOD_GHOSTSCRIPT:
                    gs_result = CompressService._compress_single_pdf_with_ghostscript(files[0], mode)
                    if gs_result is not None:
                        CompressService._last_pdf_method_used = CompressService.PDF_METHOD_GHOSTSCRIPT
                        return gs_result

                    # Fallback otomatis agar proses tetap jalan.
                    CompressService._last_pdf_method_used = CompressService.PDF_METHOD_PYMUPDF
                    return CompressService._compress_single_pdf(files[0], compression_level, mode)

                if selected_pdf_method == CompressService.PDF_METHOD_PYMUPDF:
                    CompressService._last_pdf_method_used = CompressService.PDF_METHOD_PYMUPDF
                    return CompressService._compress_single_pdf(files[0], compression_level, mode)

                # AUTO: Prioritas local production-grade Ghostscript, fallback ke PyMuPDF.
                gs_result = CompressService._compress_single_pdf_with_ghostscript(files[0], mode)
                if gs_result is not None:
                    CompressService._last_pdf_method_used = CompressService.PDF_METHOD_GHOSTSCRIPT
                    return gs_result

                CompressService._last_pdf_method_used = CompressService.PDF_METHOD_PYMUPDF
                return CompressService._compress_single_pdf(files[0], compression_level, mode)
        
        # Multiple files - create compressed archive
        try:
            # Try to use 7z format (much better compression)
            if use_7z:
                try:
                    import py7zr
                    return CompressService._compress_7z(files, compression_level, OutputNamingService.build_filename("compressed_archive", ".7z"))
                except ImportError:
                    # Fallback to ZIP if py7zr not available
                    return CompressService._compress_zip(files, compression_level, OutputNamingService.build_filename("compressed_archive", ".zip"))
            else:
                return CompressService._compress_zip(files, compression_level, OutputNamingService.build_filename("compressed_archive", ".zip"))
        except Exception as e:
            raise Exception(f"Gagal mengkompres: {str(e)}")

    @staticmethod
    def _compression_profile(level: int, mode: str = MODE_BALANCED) -> tuple[int, int]:
        """Map level 1-9 ke (max_dimension, jpeg_quality)."""
        lvl = max(1, min(9, int(level)))

        mode = CompressService._normalize_mode(mode)

        if mode == CompressService.MODE_SAFE:
            max_dims = {
                1: 4000,
                2: 4000,
                3: 3840,
                4: 3840,
                5: 3600,
                6: 3600,
                7: 3200,
                8: 3200,
                9: 3000,
            }
            jpeg_quality = {
                1: 96,
                2: 96,
                3: 96,
                4: 95,
                5: 95,
                6: 95,
                7: 94,
                8: 94,
                9: 92,
            }
            return max_dims[lvl], jpeg_quality[lvl]

        if mode == CompressService.MODE_BALANCED:
            max_dims = {
                1: 3000,
                2: 2800,
                3: 2600,
                4: 2400,
                5: 2200,
                6: 2000,
                7: 1800,
                8: 1600,
                9: 1400,
            }
            jpeg_quality = {
                1: 92,
                2: 90,
                3: 88,
                4: 86,
                5: 84,
                6: 82,
                7: 80,
                8: 78,
                9: 75,
            }
            return max_dims[lvl], jpeg_quality[lvl]

        max_dims = {
            1: 2560,
            2: 2240,
            3: 2048,
            4: 1920,
            5: 1760,
            6: 1600,
            7: 1440,
            8: 1280,
            9: 1152,
        }
        jpeg_quality = {
            1: 88,
            2: 84,
            3: 80,
            4: 76,
            5: 72,
            6: 68,
            7: 64,
            8: 60,
            9: 56,
        }
        return max_dims[lvl], jpeg_quality[lvl]

    @staticmethod
    def _normalize_pdf_method(pdf_method: str) -> str:
        method = str(pdf_method or CompressService.PDF_METHOD_AUTO).strip().lower()
        allowed = {
            CompressService.PDF_METHOD_AUTO,
            CompressService.PDF_METHOD_GHOSTSCRIPT,
            CompressService.PDF_METHOD_PYMUPDF,
        }
        return method if method in allowed else CompressService.PDF_METHOD_AUTO

    @staticmethod
    def get_last_pdf_method_used() -> str:
        return CompressService._last_pdf_method_used

    @staticmethod
    def is_ghostscript_available() -> bool:
        return CompressService._find_ghostscript_executable() is not None

    @staticmethod
    def _compress_single_pptx(file, compression_level: int, compression_mode: str = MODE_BALANCED) -> tuple[io.BytesIO, str, bool]:
        """Kompres PPTX dengan mengoptimasi gambar di folder ppt/media."""
        file.seek(0)
        input_bytes = file.read()
        input_buffer = io.BytesIO(input_bytes)
        output_buffer = io.BytesIO()

        max_dim, jpeg_quality = CompressService._compression_profile(compression_level, compression_mode)

        with zipfile.ZipFile(input_buffer, "r") as zin, zipfile.ZipFile(
            output_buffer,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename.startswith("ppt/media/"):
                    lowered = item.filename.lower()
                    if lowered.endswith((".jpg", ".jpeg", ".png", ".webp")):
                        data = CompressService._adaptive_image_compress(
                            data=data,
                            source_ext=Path(item.filename).suffix,
                            mode=compression_mode,
                            max_dim=max_dim,
                            jpeg_quality=jpeg_quality,
                        )

                zout.writestr(item, data)

        output_buffer.seek(0)

        output_name = OutputNamingService.build_filename("compressed_document", ".pptx")

        return output_buffer, output_name, True

    @staticmethod
    def _optimize_image_bytes(
        data: bytes,
        is_jpeg: bool,
        max_dim: int,
        jpeg_quality: int,
        compression_mode: str = MODE_BALANCED,
    ) -> bytes:
        """Adaptive compression wrapper untuk kompatibilitas pemanggil lama."""
        source_ext = ".jpg" if is_jpeg else ".png"
        return CompressService._adaptive_image_compress(
            data=data,
            source_ext=source_ext,
            mode=compression_mode,
            max_dim=max_dim,
            jpeg_quality=jpeg_quality,
        )
    
    @staticmethod
    def _compress_single_pdf(file, compression_level: int, compression_mode: str = MODE_BALANCED) -> tuple[io.BytesIO, str, bool]:
        """Kompres PDF dengan mengoptimasi gambar di dalamnya menggunakan PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF (fitz) tidak tersedia. Install dengan: pip install PyMuPDF"
            )
        
        file.seek(0)
        input_bytes = file.read()
        
        mode = CompressService._normalize_mode(compression_mode)
        max_dim, jpeg_quality = CompressService._compression_profile(compression_level, mode)
        
        # Buka PDF
        pdf_document = fitz.open(stream=input_bytes, filetype="pdf")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]  # xref number dari gambar
                
                # Extract gambar
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Optimize gambar (safe mode tidak mengganti isi gambar, hanya optimasi stream PDF)
                try:
                    if mode == CompressService.MODE_SAFE:
                        # Safe mode: hanya metadata/stream cleanup, jangan ubah visual image.
                        continue

                    compressed_bytes = CompressService._compress_pdf_image_bytes(
                        image_bytes=image_bytes,
                        image_ext=image_ext,
                        mode=mode,
                        max_dim=max_dim,
                        jpeg_quality=jpeg_quality,
                    )

                    if compressed_bytes and len(compressed_bytes) < len(image_bytes):
                        # Update stream langsung supaya layout tetap terjaga.
                        pdf_document.update_stream(xref, compressed_bytes)
                
                except Exception as e:
                    # Skip gambar yang gagal dioptimasi
                    continue
        
        # Save PDF hasil kompresi
        output_buffer = io.BytesIO()
        pdf_document.save(
            output_buffer,
            garbage=4,  # Maximum garbage collection
            deflate=True,  # Compress streams
            clean=True,  # Clean up
        )
        pdf_document.close()
        
        output_buffer.seek(0)
        
        output_name = OutputNamingService.build_filename("compressed_document", ".pdf")
        
        return output_buffer, output_name, True

    @staticmethod
    def _find_ghostscript_executable() -> str | None:
        """Cari executable Ghostscript untuk local run (Windows/Mac/Linux)."""
        env_path = os.environ.get("GHOSTSCRIPT_PATH", "").strip()
        if env_path and Path(env_path).exists():
            return env_path

        for candidate in CompressService.GHOSTSCRIPT_EXECUTABLE_CANDIDATES:
            located = shutil.which(candidate)
            if located:
                return located

        # Fallback pencarian umum di Windows jika PATH belum diset
        win_roots = [
            os.environ.get("ProgramW6432", ""),
            os.environ.get("ProgramFiles", ""),
            os.environ.get("ProgramFiles(x86)", ""),
        ]
        for root in win_roots:
            if not root:
                continue
            gs_root = Path(root) / "gs"
            if not gs_root.exists():
                continue
            for exe in gs_root.glob("**/bin/gswin64c.exe"):
                if exe.exists():
                    return str(exe)
            for exe in gs_root.glob("**/bin/gswin32c.exe"):
                if exe.exists():
                    return str(exe)

        return None

    @staticmethod
    def _ghostscript_pdf_setting_for_mode(compression_mode: str) -> str:
        """Map mode aplikasi ke Ghostscript PDFSETTINGS."""
        mode = CompressService._normalize_mode(compression_mode)
        if mode == CompressService.MODE_SAFE:
            return "/prepress"
        if mode == CompressService.MODE_BALANCED:
            return "/printer"
        return "/ebook"

    @staticmethod
    def _compress_single_pdf_with_ghostscript(file, compression_mode: str = MODE_BALANCED) -> tuple[io.BytesIO, str, bool] | None:
        """
        Kompres PDF pakai Ghostscript (local) jika tersedia.
        Return None jika Ghostscript tidak tersedia / gagal, agar caller fallback ke metode lain.
        """
        gs_exe = CompressService._find_ghostscript_executable()
        if not gs_exe:
            return None

        pdf_setting = CompressService._ghostscript_pdf_setting_for_mode(compression_mode)

        input_path = None
        output_path = None
        try:
            file.seek(0)
            input_bytes = file.read()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_in:
                temp_in.write(input_bytes)
                input_path = temp_in.name

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_out:
                output_path = temp_out.name

            command = [
                gs_exe,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-dPDFSETTINGS={pdf_setting}",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                "-dDetectDuplicateImages=true",
                "-dCompressFonts=true",
                f"-sOutputFile={output_path}",
                input_path,
            ]

            subprocess.run(command, check=True, timeout=300)

            with open(output_path, "rb") as f:
                optimized = f.read()

            # Kalau output tidak lebih kecil, anggap tidak optimal dan fallback ke metode lain
            if not optimized or len(optimized) >= len(input_bytes):
                return None

            output_buffer = io.BytesIO(optimized)
            output_buffer.seek(0)
            output_name = OutputNamingService.build_filename("compressed_document", ".pdf")
            return output_buffer, output_name, True
        except Exception:
            return None
        finally:
            for temp_path in (input_path, output_path):
                try:
                    if temp_path and Path(temp_path).exists():
                        Path(temp_path).unlink(missing_ok=True)
                except Exception:
                    pass

    @staticmethod
    def _compress_pdf_image_bytes(
        image_bytes: bytes,
        image_ext: str,
        mode: str,
        max_dim: int,
        jpeg_quality: int,
    ) -> bytes:
        """Kompresi adaptif khusus image yang diekstrak dari PDF."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = ImageOps.exif_transpose(img)
                image_kind = CompressService._classify_image_bytes(image_bytes)

                if mode == CompressService.MODE_AGGRESSIVE and max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                elif mode == CompressService.MODE_BALANCED and max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                out = io.BytesIO()
                ext = str(image_ext or "").lower().lstrip(".")

                if image_kind == "graphic":
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    if ext == "webp":
                        img.save(out, format="WEBP", quality=92, method=6)
                    else:
                        img.save(out, format="PNG", optimize=True, compress_level=9)
                else:
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    if ext == "webp":
                        img.save(out, format="WEBP", quality=max(75, jpeg_quality), method=6)
                    else:
                        img.save(
                            out,
                            format="JPEG",
                            quality=jpeg_quality if mode == CompressService.MODE_AGGRESSIVE else max(85, jpeg_quality),
                            optimize=True,
                            progressive=True,
                        )

                optimized = out.getvalue()
                return optimized if optimized and len(optimized) < len(image_bytes) else image_bytes
        except (UnidentifiedImageError, OSError, ValueError):
            return image_bytes
    
    @staticmethod
    def _compress_zip(files: list, compression_level: int, output_name: str) -> tuple[io.BytesIO, str, bool]:
        """Kompresi menggunakan ZIP format"""
        zip_buffer = io.BytesIO()
        anonymous_names = [
            OutputNamingService.build_filename("compressed_item", getattr(file, "name", "").rsplit(".", 1)[-1] if "." in getattr(file, "name", "") else ".bin", index=index)
            for index, file in enumerate(files, start=1)
        ]
        
        # Gunakan compression level yang tepat
        compress_type = zipfile.ZIP_DEFLATED if compression_level > 0 else zipfile.ZIP_STORED
        
        with zipfile.ZipFile(zip_buffer, 'w', compress_type) as zip_file:
            for file, anonymous_name in zip(files, anonymous_names):
                # Reset file pointer
                file.seek(0)
                # Read file content
                file_content = file.read()
                # Add to ZIP dengan compression
                if compression_level > 0:
                    zip_file.writestr(
                        anonymous_name,
                        file_content, 
                        compress_type=zipfile.ZIP_DEFLATED, 
                        compresslevel=compression_level
                    )
                else:
                    zip_file.writestr(anonymous_name, file_content)
        
        zip_buffer.seek(0)
        return zip_buffer, output_name, True
    
    @staticmethod
    def _compress_7z(files: list, compression_level: int, output_name: str) -> tuple[io.BytesIO, str, bool]:
        """Kompresi menggunakan 7z format (kompresi maksimal)"""
        import py7zr
        
        # Map level 1-9 ke 7z solid settings
        # 7z punya compression method yang lebih baik
        filters = [
            {"id": "LZMA2", "preset": compression_level},
        ]
        
        zip_buffer = io.BytesIO()
        
        with py7zr.SevenZipFile(zip_buffer, 'w', filters=filters) as archive:
            for index, file in enumerate(files, start=1):
                file.seek(0)
                file_content = file.read()
                # Write file to archive
                extension = file.name.rsplit('.', 1)[-1] if '.' in file.name else '.bin'
                anonymous_name = OutputNamingService.build_filename("compressed_item", extension, index=index)
                archive.writestr(file_content, arcname=anonymous_name)
        
        zip_buffer.seek(0)
        return zip_buffer, output_name, True
    
    @staticmethod
    def get_compression_ratio(original_size: int, compressed_size: int) -> float:
        """Hitung rasio kompresi"""
        if original_size == 0:
            return 0
        return (1 - compressed_size / original_size) * 100
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format bytes menjadi human readable"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

