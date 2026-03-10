from dataclasses import dataclass

import streamlit as st


@dataclass
class HomeViewResult:
    open_locker: bool
    open_compressor: bool
    open_converter: bool
    open_split_merge: bool


class HomeView:
    def render(self) -> HomeViewResult:
        st.title("🛠️ Kumpulan Tools Dokumen")
        st.caption("Halaman utama berisi tombol ke tools singkat: File Locker, Kompresi, dan Konversi Dokumen.")
        
        st.markdown("---")
        
        # File Locker
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 🔐 File Locker")
            st.write("Enkripsi/dekripsi file apa pun menggunakan password.")
        with col2:
            open_locker = st.button("Buka File Locker", use_container_width=True, type="primary", key="btn_locker")
        
        st.markdown("---")
        
        # File Compressor
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 📦 Kompresi File")
            st.write("Kompres seluruh jenis file menjadi satu file ZIP.")
        with col2:
            open_compressor = st.button("Buka Kompresi", use_container_width=True, type="primary", key="btn_compressor")
        
        st.markdown("---")
        
        # File Converter
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 🔄 Konversi Dokumen")
            st.write("Konversi PDF ke Word/PPT dan sebaliknya Office/gambar ke PDF.")
        with col2:
            open_converter = st.button("Buka Konversi", use_container_width=True, type="primary", key="btn_converter")

        st.markdown("---")

        # Split Merge
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 🪄 Split & Gabung Dokumen")
            st.write("Pisahkan atau gabungkan PDF, Word, dan PowerPoint dengan pola halaman/slide.")
        with col2:
            open_split_merge = st.button("Buka Splitter", use_container_width=True, type="primary", key="btn_split_merge")

        return HomeViewResult(
            open_locker=open_locker,
            open_compressor=open_compressor,
            open_converter=open_converter,
            open_split_merge=open_split_merge,
        )
