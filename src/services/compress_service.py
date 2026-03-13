import zipfile
import io
from PIL import Image, ImageOps, UnidentifiedImageError

from src.services.output_naming_service import OutputNamingService


class CompressService:
    """Service untuk mengkompres file dengan metode optimal"""
    
    @staticmethod
    def compress_files(files: list, compression_level: int = 9, use_7z: bool = True) -> tuple[io.BytesIO, str, bool]:
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

        if len(files) == 1:
            single_name = getattr(files[0], "name", "file")

            # Metode khusus PPTX: kompres gambar di dalam PPT lalu pack ulang ke PPTX
            if single_name.lower().endswith(".pptx"):
                return CompressService._compress_single_pptx(files[0], compression_level)
            
            # Metode khusus PDF: kompres gambar di dalam PDF lalu simpan kembali
            if single_name.lower().endswith(".pdf"):
                return CompressService._compress_single_pdf(files[0], compression_level)
        
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
    def _compression_profile(level: int) -> tuple[int, int]:
        """Map level 1-9 ke (max_dimension, jpeg_quality)."""
        lvl = max(1, min(9, int(level)))
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
    def _compress_single_pptx(file, compression_level: int) -> tuple[io.BytesIO, str, bool]:
        """Kompres PPTX dengan mengoptimasi gambar di folder ppt/media."""
        file.seek(0)
        input_bytes = file.read()
        input_buffer = io.BytesIO(input_bytes)
        output_buffer = io.BytesIO()

        max_dim, jpeg_quality = CompressService._compression_profile(compression_level)

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
                        data = CompressService._optimize_image_bytes(
                            data=data,
                            is_jpeg=lowered.endswith((".jpg", ".jpeg")),
                            max_dim=max_dim,
                            jpeg_quality=jpeg_quality,
                        )

                zout.writestr(item, data)

        output_buffer.seek(0)

        output_name = OutputNamingService.build_filename("compressed_document", ".pptx")

        return output_buffer, output_name, True

    @staticmethod
    def _optimize_image_bytes(data: bytes, is_jpeg: bool, max_dim: int, jpeg_quality: int) -> bytes:
        """Resize + recompress gambar. Jika gagal, kembalikan data asli."""
        try:
            with Image.open(io.BytesIO(data)) as img:
                img = ImageOps.exif_transpose(img)

                # Resize jika dimensi terlalu besar
                if max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                out = io.BytesIO()

                if is_jpeg:
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    img.save(
                        out,
                        format="JPEG",
                        quality=jpeg_quality,
                        optimize=True,
                        progressive=True,
                    )
                else:
                    # PNG/WEBP: tetap format lossless/lossy sesuai jenis awal, tapi dioptimasi
                    if img.mode == "P":
                        img = img.convert("RGBA")

                    # Simpan PNG sebagai PNG teroptimasi untuk kompatibilitas aman di PPT
                    img.save(
                        out,
                        format="PNG",
                        optimize=True,
                        compress_level=9,
                    )

                optimized = out.getvalue()
                if optimized and len(optimized) < len(data):
                    return optimized
                return data
        except (UnidentifiedImageError, OSError, ValueError):
            return data
    
    @staticmethod
    def _compress_single_pdf(file, compression_level: int) -> tuple[io.BytesIO, str, bool]:
        """Kompres PDF dengan mengoptimasi gambar di dalamnya menggunakan PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF (fitz) tidak tersedia. Install dengan: pip install PyMuPDF"
            )
        
        file.seek(0)
        input_bytes = file.read()
        
        max_dim, jpeg_quality = CompressService._compression_profile(compression_level)
        
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
                
                # Optimize gambar
                try:
                    with Image.open(io.BytesIO(image_bytes)) as img:
                        img = ImageOps.exif_transpose(img)
                        
                        # Resize jika terlalu besar
                        if max(img.size) > max_dim:
                            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                        
                        # Convert ke RGB untuk JPEG
                        if img.mode not in ("RGB", "L"):
                            img = img.convert("RGB")
                        
                        # Compress ke JPEG
                        compressed_img = io.BytesIO()
                        img.save(
                            compressed_img,
                            format="JPEG",
                            quality=jpeg_quality,
                            optimize=True,
                            progressive=True
                        )
                        compressed_bytes = compressed_img.getvalue()
                        
                        # Replace gambar di PDF jika lebih kecil
                        if len(compressed_bytes) < len(image_bytes):
                            # Get image rectangle
                            img_rects = page.get_image_rects(xref)
                            if img_rects:
                                rect = img_rects[0]  # Gunakan rectangle pertama
                                
                                # Insert compressed image
                                page.insert_image(
                                    rect,
                                    stream=compressed_bytes,
                                    keep_proportion=True
                                )
                                
                                # Delete original image reference
                                page.delete_image(xref)
                
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

