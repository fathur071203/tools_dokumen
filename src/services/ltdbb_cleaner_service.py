from __future__ import annotations

import io
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class CleanerResult:
    cleaned_csv: bytes
    download_name: str
    cleaned_df: pd.DataFrame
    variant: str | None
    summary: dict[str, Any]
    preview_df: pd.DataFrame
    top_dest_by_freq: pd.DataFrame
    top_dest_by_nominal: pd.DataFrame


class LTDBBCleanerService:
    VARIANT_OPTIONS = {
        "": "Auto",
        "G0001": "G0001 (Outgoing)",
        "G0002": "G0002 (Ingoing)",
        "G0003": "G0003 (Domestik)",
    }

    VARIANT_DESTINATION_COLUMN = {
        "G0001": "Negara Tujuan Pengiriman",
        "G0002": "Kota/Kab. Tujuan Pengiriman",
        "G0003": "Kota/Kab. Tujuan Pengiriman",
    }

    COLUMN_ALIASES = {
        "Frekuensi Pengiriman": [
            "frekuensi pengiriman",
            "frekuensi",
            "jumlah frekuensi",
            "jumlah pengiriman",
            "volume pengiriman",
        ],
        "Total Nominal Transaksi": [
            "total nominal transaksi",
            "nominal transaksi",
            "total nominal",
            "jumlah nominal transaksi",
            "nominal total transaksi",
        ],
        "Negara Tujuan Pengiriman": [
            "negara tujuan pengiriman",
            "negara tujuan",
            "tujuan pengiriman negara",
            "destination country",
        ],
        "Kota/Kab. Tujuan Pengiriman": [
            "kota kab tujuan pengiriman",
            "kota kab. tujuan pengiriman",
            "kota tujuan pengiriman",
            "kabupaten tujuan pengiriman",
            "kab kota tujuan pengiriman",
            "kota/kab. tujuan pengiriman",
        ],
    }

    @classmethod
    def process_upload(cls, upload: Any, variant_override: str | None = None) -> CleanerResult:
        if upload is None:
            raise ValueError("Tidak ada file yang dipilih.")

        filename = getattr(upload, "name", "data_ltdbb")
        raw_df = cls._read_input_table(upload, filename)
        cleaned_df = cls._clean_table(raw_df)
        cleaned_df = cls._normalize_columns(cleaned_df)

        variant = variant_override or cls._detect_variant(cleaned_df, raw_df)
        cleaned_df = cls._coerce_numeric_columns(cleaned_df)
        summary = cls._build_summary(cleaned_df, raw_df, filename, variant)
        top_dest_by_freq, top_dest_by_nominal = cls._build_top_destinations(cleaned_df, variant)
        preview_df = cleaned_df.head(10).copy()

        cleaned_csv = cleaned_df.to_csv(index=False, encoding="utf-8").encode("utf-8")
        download_name = f"cleaned_{Path(filename).stem}.csv"

        return CleanerResult(
            cleaned_csv=cleaned_csv,
            download_name=download_name,
            cleaned_df=cleaned_df,
            variant=variant,
            summary=summary,
            preview_df=preview_df,
            top_dest_by_freq=top_dest_by_freq,
            top_dest_by_nominal=top_dest_by_nominal,
        )

    @classmethod
    def _read_input_table(cls, upload: Any, filename: str) -> pd.DataFrame:
        suffix = Path(filename).suffix.lower()
        upload.seek(0)
        file_bytes = upload.read()
        buffer = io.BytesIO(file_bytes)

        if suffix == ".csv":
            for encoding in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    buffer.seek(0)
                    return pd.read_csv(buffer, header=None, dtype=object, sep=None, engine="python")
                except UnicodeDecodeError:
                    continue
                except Exception:
                    buffer.seek(0)
                    try:
                        return pd.read_csv(buffer, header=None, dtype=object, encoding=encoding)
                    except Exception:
                        continue
            raise ValueError("File CSV tidak dapat dibaca. Pastikan encoding dan delimiter valid.")

        if suffix == ".xlsx":
            return pd.read_excel(buffer, header=None, dtype=object, engine="openpyxl")
        if suffix == ".xls":
            return pd.read_excel(buffer, header=None, dtype=object, engine="xlrd")

        raise ValueError("Format file tidak didukung. Gunakan CSV, XLS, atau XLSX.")

    @classmethod
    def _clean_table(cls, raw_df: pd.DataFrame) -> pd.DataFrame:
        working_df = raw_df.copy()
        working_df = working_df.dropna(axis=1, how="all")
        if len(working_df) < 6:
            raise ValueError("Template terlalu pendek. Pastikan header LTDBB masih lengkap.")

        working_df = working_df.iloc[5:].reset_index(drop=True)
        if working_df.shape[1] > 2:
            working_df = working_df.iloc[:, 2:]
        working_df = working_df.dropna(axis=1, how="all")
        if working_df.empty:
            raise ValueError("Tidak ada data yang bisa diproses setelah baris header dibuang.")

        header_row = working_df.iloc[0].tolist()
        data_df = working_df.iloc[1:].copy()
        data_df.columns = cls._make_unique_headers(header_row)

        data_df = data_df.dropna(how="all")
        data_df = data_df.loc[:, [not str(column).startswith("Kolom_") or data_df[column].notna().any() for column in data_df.columns]]
        data_df = data_df[data_df.apply(lambda row: not cls._is_noise_row(row, data_df.columns), axis=1)]
        data_df = data_df.dropna(how="all").reset_index(drop=True)

        if data_df.empty:
            raise ValueError("Tidak ada baris data yang tersisa setelah proses cleaning.")

        return data_df

    @classmethod
    def _normalize_columns(cls, data_df: pd.DataFrame) -> pd.DataFrame:
        rename_map: dict[str, str] = {}
        taken_targets: set[str] = set()

        for column in data_df.columns:
            normalized_column = cls._normalize_text(column)
            best_target = None
            best_score = 0.0
            for target, aliases in cls.COLUMN_ALIASES.items():
                if target in taken_targets:
                    continue
                for alias in aliases:
                    score = SequenceMatcher(None, normalized_column, cls._normalize_text(alias)).ratio()
                    if normalized_column == cls._normalize_text(alias) or cls._normalize_text(alias) in normalized_column:
                        score = max(score, 0.98)
                    if score > best_score:
                        best_target = target
                        best_score = score

            if best_target and best_score >= 0.72:
                rename_map[column] = best_target
                taken_targets.add(best_target)

        normalized_df = data_df.rename(columns=rename_map)
        normalized_df.columns = [cls._clean_header_name(column, index) for index, column in enumerate(normalized_df.columns, start=1)]
        return normalized_df

    @classmethod
    def _coerce_numeric_columns(cls, data_df: pd.DataFrame) -> pd.DataFrame:
        numeric_columns = ["Frekuensi Pengiriman", "Total Nominal Transaksi"]
        output_df = data_df.copy()
        for column in numeric_columns:
            if column in output_df.columns:
                output_df[column] = output_df[column].apply(cls._parse_numeric)
        return output_df

    @classmethod
    def _build_summary(
        cls,
        cleaned_df: pd.DataFrame,
        raw_df: pd.DataFrame,
        filename: str,
        variant: str | None,
    ) -> dict[str, Any]:
        total_frekuensi = cleaned_df["Frekuensi Pengiriman"].sum() if "Frekuensi Pengiriman" in cleaned_df.columns else None
        total_nominal = cleaned_df["Total Nominal Transaksi"].sum() if "Total Nominal Transaksi" in cleaned_df.columns else None

        return {
            "source_file": filename,
            "variant": variant,
            "pjp_name": cls._extract_named_value(raw_df, ["nama pjp", "penyelenggara jasa pembayaran", "pjp"]),
            "pjp_sandi": cls._extract_named_value(raw_df, ["sandi pjp", "kode pjp"]),
            "periode_text": cls._extract_named_value(raw_df, ["periode", "perioda", "periode laporan"]) or cls._extract_period_from_top_rows(raw_df),
            "rows": len(cleaned_df),
            "columns": len(cleaned_df.columns),
            "total_frekuensi": int(total_frekuensi) if pd.notna(total_frekuensi) else None,
            "total_nominal": float(total_nominal) if pd.notna(total_nominal) else None,
        }

    @classmethod
    def _build_top_destinations(cls, cleaned_df: pd.DataFrame, variant: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
        destination_column = cls.VARIANT_DESTINATION_COLUMN.get(variant)
        if not destination_column or destination_column not in cleaned_df.columns:
            if "Negara Tujuan Pengiriman" in cleaned_df.columns:
                destination_column = "Negara Tujuan Pengiriman"
            elif "Kota/Kab. Tujuan Pengiriman" in cleaned_df.columns:
                destination_column = "Kota/Kab. Tujuan Pengiriman"

        if not destination_column or destination_column not in cleaned_df.columns:
            return pd.DataFrame(), pd.DataFrame()

        required_columns = {destination_column, "Frekuensi Pengiriman", "Total Nominal Transaksi"}
        if not required_columns.issubset(set(cleaned_df.columns)):
            return pd.DataFrame(), pd.DataFrame()

        grouped = (
            cleaned_df[[destination_column, "Frekuensi Pengiriman", "Total Nominal Transaksi"]]
            .dropna(subset=[destination_column])
            .groupby(destination_column, as_index=False)
            .agg({
                "Frekuensi Pengiriman": "sum",
                "Total Nominal Transaksi": "sum",
            })
        )

        if grouped.empty:
            return pd.DataFrame(), pd.DataFrame()

        freq_df = grouped.sort_values(["Frekuensi Pengiriman", "Total Nominal Transaksi"], ascending=[False, False]).head(10).reset_index(drop=True)
        nominal_df = grouped.sort_values(["Total Nominal Transaksi", "Frekuensi Pengiriman"], ascending=[False, False]).head(10).reset_index(drop=True)
        return freq_df, nominal_df

    @classmethod
    def _detect_variant(cls, cleaned_df: pd.DataFrame, raw_df: pd.DataFrame) -> str | None:
        top_text = " ".join(
            cls._normalize_text(value)
            for value in raw_df.head(10).fillna("").astype(str).values.flatten().tolist()
            if str(value).strip()
        )

        for variant in ("G0001", "G0002", "G0003"):
            if variant.lower() in top_text:
                return variant

        if "outgoing" in top_text or "luar negeri" in top_text:
            return "G0001"
        if "ingoing" in top_text:
            return "G0002"
        if "domestik" in top_text or "dalam negeri" in top_text:
            return "G0003"

        if "Negara Tujuan Pengiriman" in cleaned_df.columns:
            return "G0001"
        if "Kota/Kab. Tujuan Pengiriman" in cleaned_df.columns:
            return "G0002"
        return None

    @classmethod
    def _extract_named_value(cls, raw_df: pd.DataFrame, labels: list[str]) -> str | None:
        top_rows = raw_df.head(10).fillna("")
        for _, row in top_rows.iterrows():
            values = [str(value).strip() for value in row.tolist() if str(value).strip()]
            for index, value in enumerate(values):
                normalized_value = cls._normalize_text(value)
                for label in labels:
                    label_text = cls._normalize_text(label)
                    if label_text in normalized_value:
                        after_separator = re.split(r":", value, maxsplit=1)
                        if len(after_separator) == 2 and after_separator[1].strip():
                            return after_separator[1].strip()
                        if index + 1 < len(values):
                            return values[index + 1]
        return None

    @classmethod
    def _extract_period_from_top_rows(cls, raw_df: pd.DataFrame) -> str | None:
        top_text = " ".join(
            str(value).strip()
            for value in raw_df.head(10).fillna("").astype(str).values.flatten().tolist()
            if str(value).strip()
        )
        match = re.search(r"(20\d{2}|19\d{2}).{0,20}(jan|feb|mar|apr|mei|jun|jul|agu|sep|okt|nov|des)", top_text, re.IGNORECASE)
        if match:
            return match.group(0)
        return None

    @classmethod
    def _make_unique_headers(cls, header_row: list[Any]) -> list[str]:
        counts: dict[str, int] = {}
        headers: list[str] = []
        for index, value in enumerate(header_row, start=1):
            base_name = cls._clean_header_name(value, index)
            counts[base_name] = counts.get(base_name, 0) + 1
            if counts[base_name] > 1:
                headers.append(f"{base_name}_{counts[base_name]}")
            else:
                headers.append(base_name)
        return headers

    @classmethod
    def _clean_header_name(cls, value: Any, index: int) -> str:
        text = str(value).strip() if value is not None else ""
        if text.lower() in {"", "nan", "none"}:
            return f"Kolom_{index}"
        text = re.sub(r"\s+", " ", text)
        return text

    @classmethod
    def _is_noise_row(cls, row: pd.Series, columns: pd.Index) -> bool:
        values = [str(value).strip() for value in row.tolist() if str(value).strip() and str(value).strip().lower() not in {"nan", "none"}]
        if not values:
            return True

        row_text = " ".join(values)
        normalized_text = cls._normalize_text(row_text)
        footer_markers = [
            "total",
            "grand total",
            "keterangan",
            "catatan",
            "sumber data",
            "halaman",
            "generated",
        ]
        if len(values) <= 3 and any(marker in normalized_text for marker in footer_markers):
            return True

        normalized_values = {cls._normalize_text(value) for value in values}
        normalized_headers = {cls._normalize_text(column) for column in columns}
        if normalized_values and len(normalized_values.intersection(normalized_headers)) >= max(2, len(normalized_values) - 1):
            return True

        return False

    @staticmethod
    def _normalize_text(value: Any) -> str:
        text = str(value).strip().lower()
        text = text.replace("/", " ").replace("-", " ")
        text = re.sub(r"[^a-z0-9 ]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_numeric(value: Any) -> float | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if not text:
            return None

        text = re.sub(r"[^0-9,.-]", "", text)
        if not text:
            return None

        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif text.count(".") > 1:
            text = text.replace(".", "")
        elif text.count(",") > 1:
            text = text.replace(",", "")
        elif "." in text:
            dot_index = text.rfind(".")
            decimals = len(text) - dot_index - 1
            text = text.replace(".", "" if decimals == 3 else ".")
        elif "," in text:
            comma_index = text.rfind(",")
            decimals = len(text) - comma_index - 1
            text = text.replace(",", "" if decimals == 3 else ".")

        try:
            return float(text)
        except ValueError:
            return None