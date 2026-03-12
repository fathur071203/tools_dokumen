from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass
class DecryptViewResult:
    go_back: bool
    decrypt_clicked: bool
    encrypted_file: Any | None
    password: str


class FileLockerDecryptView:
    def render(self) -> DecryptViewResult:
        col_a, col_b = st.columns([1, 8])
        with col_a:
            go_back = st.button("← Kembali")
        with col_b:
            st.subheader("🔓 Dekripsi File")
            st.write("Buka file `.encrypted` dari File Locker atau lepas password dari file PDF yang diproteksi. Khusus file Office yang dikunci, hasil dekripsi akan berupa arsip ZIP.")

        encrypted_file = st.file_uploader(
            "Upload file terenkripsi",
            accept_multiple_files=False,
            type=None,
            help="Bisa file .encrypted atau file PDF yang diproteksi password.",
        )

        if encrypted_file and not (
            encrypted_file.name.endswith(".encrypted") or encrypted_file.name.lower().endswith(".pdf")
        ):
            st.warning("File bukan .encrypted atau .pdf. Tetap dicoba selama format internal valid.")

        password = st.text_input("Password dekripsi (minimal 8 karakter)", type="password")
        decrypt_clicked = st.button("🔓 Dekripsi", type="primary")

        return DecryptViewResult(
            go_back=go_back,
            decrypt_clicked=decrypt_clicked,
            encrypted_file=encrypted_file,
            password=password,
        )
