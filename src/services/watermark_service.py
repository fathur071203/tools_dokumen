from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from src.services.output_naming_service import OutputNamingService


class WatermarkService:
    POSITION_OPTIONS = {
        "center": "Tengah",
        "top_left": "Kiri Atas",
        "top_right": "Kanan Atas",
        "bottom_left": "Kiri Bawah",
        "bottom_right": "Kanan Bawah",
    }

    ORIENTATION_OPTIONS = {
        "straight": "Lurus",
        "tilted": "Miring",
    }

    TEMPLATE_OPTIONS = {
        "BPK": "DIBERIKAN OLEH BANK INDONESIA\nTERBATAS UNTUK BPK RI",
        "DAI": "DIBERIKAN OLEH BANK INDONESIA\nTERBATAS UNTUK DAI",
        "PENYELENGGARA": "PENYELENGGARA",
        "ARSIP": "ARSIP",
        "PPATK": "PPATK",
    }

    @classmethod
    def add_watermark(
        cls,
        pdf_upload: Any,
        watermark_mode: str,
        text: str,
        template_name: str,
        image_upload: Any,
        text_color: str,
        use_bezel: bool,
        position: str,
        orientation: str,
        opacity: float,
        size_ratio: float,
    ) -> tuple[io.BytesIO, str, str, str]:
        if pdf_upload is None:
            raise ValueError("File PDF wajib diupload.")

        if Path(getattr(pdf_upload, "name", "")).suffix.lower() != ".pdf":
            raise ValueError("File yang diupload harus berformat PDF.")

        if watermark_mode == "text" and not text.strip():
            raise ValueError("Teks watermark tidak boleh kosong.")

        if watermark_mode == "template" and template_name not in cls.TEMPLATE_OPTIONS:
            raise ValueError("Template watermark tidak valid.")

        if watermark_mode == "image" and image_upload is None:
            raise ValueError("Silakan upload gambar PNG untuk watermark.")

        pdf_upload.seek(0)
        pdf_bytes = pdf_upload.read()
        document = fitz.open(stream=pdf_bytes, filetype="pdf")

        try:
            image_bytes = None
            if watermark_mode == "image":
                image_upload.seek(0)
                image_bytes = image_upload.read()

            for page in document:
                overlay = cls._build_overlay_for_page(
                    page=page,
                    watermark_mode=watermark_mode,
                    text=text,
                    template_name=template_name,
                    image_bytes=image_bytes,
                    text_color=text_color,
                    use_bezel=use_bezel,
                    position=position,
                    orientation=orientation,
                    opacity=opacity,
                    size_ratio=size_ratio,
                )
                page.insert_image(overlay["rect"], stream=overlay["image_bytes"], overlay=True, keep_proportion=True)

            output = io.BytesIO(document.tobytes(garbage=4, deflate=True))
            output.seek(0)
            filename = OutputNamingService.build_filename("watermarked_document", ".pdf")
            message = "Watermark berhasil ditambahkan ke PDF."
            return output, filename, "application/pdf", message
        finally:
            document.close()

    @classmethod
    def _build_overlay_for_page(
        cls,
        page: fitz.Page,
        watermark_mode: str,
        text: str,
        template_name: str,
        image_bytes: bytes | None,
        text_color: str,
        use_bezel: bool,
        position: str,
        orientation: str,
        opacity: float,
        size_ratio: float,
    ) -> dict[str, Any]:
        page_width = max(int(page.rect.width), 1)
        page_height = max(int(page.rect.height), 1)

        if watermark_mode in {"text", "template"}:
            resolved_text = cls._resolve_text(watermark_mode, text, template_name)
            overlay_image = cls._build_text_image(
                text=resolved_text,
                page_width=page_width,
                page_height=page_height,
                opacity=opacity,
                size_ratio=size_ratio,
                orientation=orientation,
                text_color=text_color,
                is_template=watermark_mode == "template",
                use_bezel=use_bezel,
            )
        else:
            overlay_image = cls._build_png_image(
                image_bytes=image_bytes,
                page_width=page_width,
                page_height=page_height,
                opacity=opacity,
                size_ratio=size_ratio,
                orientation=orientation,
                use_bezel=use_bezel,
                bezel_color=text_color,
            )

        rect = cls._build_target_rect(page.rect, overlay_image.size[0], overlay_image.size[1], position)

        image_buffer = io.BytesIO()
        overlay_image.save(image_buffer, format="PNG")
        return {
            "rect": rect,
            "image_bytes": image_buffer.getvalue(),
        }

    @classmethod
    def _build_text_image(
        cls,
        text: str,
        page_width: int,
        page_height: int,
        opacity: float,
        size_ratio: float,
        orientation: str,
        text_color: str,
        is_template: bool,
        use_bezel: bool,
    ) -> Image.Image:
        max_width = max(int(page_width * max(size_ratio, 0.15)), 120)
        line_count = max(len(text.splitlines()), 1)
        font_size = max(int(min(page_width, page_height) * (0.09 if is_template else 0.08) * max(size_ratio, 0.35)), 16)
        font = cls._load_font(font_size, bold=is_template)
        display_text = text.upper() if is_template else text

        temp_image = Image.new("RGBA", (max_width, max(page_height, 100)), (255, 255, 255, 0))
        draw = ImageDraw.Draw(temp_image)

        while font_size > 14:
            bbox = draw.multiline_textbbox((0, 0), display_text, font=font, spacing=10 if is_template else 8, align="center")
            text_width = bbox[2] - bbox[0]
            if text_width <= max_width:
                break
            font_size -= 2
            font = cls._load_font(font_size, bold=is_template)

        bbox = draw.multiline_textbbox((0, 0), display_text, font=font, spacing=10 if is_template else 8, align="center")
        text_width = max(int(bbox[2] - bbox[0]), 1)
        text_height = max(int(bbox[3] - bbox[1]), 1)
        padding_x = max(int(text_width * 0.18), 20)
        padding_y = max(int(text_height * (0.18 if is_template else 0.22)), 18)

        canvas = Image.new("RGBA", (text_width + padding_x * 2, text_height + padding_y * 2), (255, 255, 255, 0))
        draw = ImageDraw.Draw(canvas)
        alpha = max(20, min(255, int(opacity * 255)))

        red, green, blue = cls._hex_to_rgb(text_color)
        if use_bezel:
            draw.rounded_rectangle(
                (0, 0, canvas.width - 1, canvas.height - 1),
                radius=18,
                fill=(255, 255, 255, max(8, int(alpha * (0.14 if is_template else 0.16)))),
                outline=(red, green, blue, max(18, int(alpha * 0.30))),
                width=2,
            )

        draw.multiline_text(
            (padding_x, padding_y),
            display_text,
            font=font,
            fill=(red, green, blue, alpha),
            align="center",
            spacing=10 if is_template else 8,
        )

        if orientation == "tilted":
            canvas = canvas.rotate(32, expand=True, resample=Image.Resampling.BICUBIC)

        return canvas

    @classmethod
    def _build_png_image(
        cls,
        image_bytes: bytes | None,
        page_width: int,
        page_height: int,
        opacity: float,
        size_ratio: float,
        orientation: str,
        use_bezel: bool,
        bezel_color: str,
    ) -> Image.Image:
        if not image_bytes:
            raise ValueError("File PNG watermark tidak tersedia.")

        with Image.open(io.BytesIO(image_bytes)) as source_image:
            image = source_image.convert("RGBA")

        target_width = max(int(page_width * max(size_ratio, 0.12)), 80)
        scale_factor = min(target_width / max(image.width, 1), (page_height * 0.35) / max(image.height, 1))
        resized = image.resize(
            (
                max(1, int(image.width * scale_factor)),
                max(1, int(image.height * scale_factor)),
            ),
            Image.Resampling.LANCZOS,
        )

        alpha_channel = resized.getchannel("A")
        alpha_channel = ImageEnhance.Brightness(alpha_channel).enhance(max(min(opacity, 1.0), 0.05))
        resized.putalpha(alpha_channel)

        if orientation == "tilted":
            resized = resized.rotate(32, expand=True, resample=Image.Resampling.BICUBIC)

        if use_bezel:
            resized = cls._wrap_with_bezel(resized, bezel_color, opacity)

        return resized

    @classmethod
    def _build_target_rect(cls, page_rect: fitz.Rect, image_width: int, image_height: int, position: str) -> fitz.Rect:
        margin_x = max(page_rect.width * 0.04, 20)
        margin_y = max(page_rect.height * 0.04, 20)

        if position == "top_left":
            x0 = page_rect.x0 + margin_x
            y0 = page_rect.y0 + margin_y
        elif position == "top_right":
            x0 = page_rect.x1 - margin_x - image_width
            y0 = page_rect.y0 + margin_y
        elif position == "bottom_left":
            x0 = page_rect.x0 + margin_x
            y0 = page_rect.y1 - margin_y - image_height
        elif position == "bottom_right":
            x0 = page_rect.x1 - margin_x - image_width
            y0 = page_rect.y1 - margin_y - image_height
        else:
            x0 = page_rect.x0 + (page_rect.width - image_width) / 2
            y0 = page_rect.y0 + (page_rect.height - image_height) / 2

        x0 = max(page_rect.x0, min(x0, page_rect.x1 - image_width))
        y0 = max(page_rect.y0, min(y0, page_rect.y1 - image_height))
        return fitz.Rect(x0, y0, x0 + image_width, y0 + image_height)

    @staticmethod
    def _load_font(font_size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        font_candidates = [
            "arialbd.ttf" if bold else "arial.ttf",
            "calibrib.ttf" if bold else "calibri.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        ]
        for font_name in font_candidates:
            try:
                return ImageFont.truetype(font_name, font_size)
            except OSError:
                continue
        return ImageFont.load_default()

    @classmethod
    def _resolve_text(cls, watermark_mode: str, text: str, template_name: str) -> str:
        if watermark_mode == "template":
            return cls.TEMPLATE_OPTIONS[template_name]
        return text.strip()

    @staticmethod
    def _hex_to_rgb(color_hex: str) -> tuple[int, int, int]:
        color = color_hex.strip().lstrip("#")
        if len(color) != 6:
            return 180, 0, 0
        try:
            return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))
        except ValueError:
            return 180, 0, 0

    @classmethod
    def _wrap_with_bezel(cls, image: Image.Image, bezel_color: str, opacity: float) -> Image.Image:
        red, green, blue = cls._hex_to_rgb(bezel_color)
        pad_x = max(int(image.width * 0.10), 18)
        pad_y = max(int(image.height * 0.12), 18)
        canvas = Image.new("RGBA", (image.width + pad_x * 2, image.height + pad_y * 2), (255, 255, 255, 0))
        draw = ImageDraw.Draw(canvas)
        alpha = max(20, min(255, int(opacity * 255)))
        draw.rounded_rectangle(
            (0, 0, canvas.width - 1, canvas.height - 1),
            radius=18,
            fill=(255, 255, 255, max(8, int(alpha * 0.14))),
            outline=(red, green, blue, max(18, int(alpha * 0.30))),
            width=2,
        )
        canvas.paste(image, (pad_x, pad_y), image)
        return canvas