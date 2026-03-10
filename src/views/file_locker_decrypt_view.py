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
            st.write("Dekripsi file yang sebelumnya dienkripsi dengan File Locker.")

        encrypted_file = st.file_uploader(
            "Upload file terenkripsi",
            accept_multiple_files=False,
            type=None,
            help="Utamakan file dengan ekstensi .encrypted",
        )

        if encrypted_file and not encrypted_file.name.endswith(".encrypted"):
            st.warning("File tidak berakhiran .encrypted. Tetap dicoba selama format internal valid.")

        password = st.text_input("Password dekripsi (minimal 8 karakter)", type="password")
        decrypt_clicked = st.button("🔓 Dekripsi", type="primary")

        return DecryptViewResult(
            go_back=go_back,
            decrypt_clicked=decrypt_clicked,
            encrypted_file=encrypted_file,
            password=password,
        )
