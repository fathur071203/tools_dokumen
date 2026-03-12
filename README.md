
# Tools Dokumen (Streamlit)

Aplikasi Streamlit dengan halaman utama berisi kumpulan tools.

## Arsitektur (rapih + OOP MVP)

Project sekarang dipisah dengan konsep **MVP (Model-View-Presenter)**:

- `Model`: logika data/domain File Locker.
- `View`: komponen tampilan Streamlit (input, tombol, uploader).
- `Presenter`: penghubung View ↔ Model + validasi alur.

Struktur folder:

```text
tools_dokumen/
├─ app.py
├─ requirements.txt
├─ README.md
└─ src/
  ├─ main.py
  ├─ models/
  │  └─ file_locker_model.py
  ├─ presenters/
  │  ├─ home_presenter.py
  │  └─ file_locker_presenter.py
  ├─ services/
  │  └─ crypto_service.py
  ├─ state/
  │  └─ session_state.py
  ├─ styles/
  │  └─ theme.py
  └─ views/
    ├─ home_view.py
    ├─ file_locker_encrypt_view.py
    └─ file_locker_decrypt_view.py
```

## Fitur yang sudah jadi (fase awal)
- Halaman utama dengan tombol tool.
- **File Locker**:
  - Enkripsi semua tipe file.
  - Mode password:
    - 1 password untuk semua file.
    - Password berbeda per file.
  - Output:
    - 1 file -> download langsung `.encrypted`.
    - Banyak file -> download ZIP.
- **File Locker Decrypt**:
  - Dekripsi file `.encrypted` dengan password.
  - Download file asli.
- **Konversi Dokumen**:
  - PDF ke Word/PPT.
  - Word/Excel/PPT dan gambar ke PDF.
- **Watermark PDF**:
  - Watermark teks custom.
  - Pilihan posisi watermark.
  - Orientasi lurus atau miring.
  - Upload gambar PNG sebagai watermark.
- **Cleaner LTDBB**:
  - Bersihkan template LTDBB CSV/XLS/XLSX.
  - Buang baris 1–5, pakai baris ke-6 sebagai header, dan hapus kolom A/B.
  - Normalisasi kolom penting otomatis.
  - Preview 10 baris, ringkasan, dan top destinasi berdasarkan frekuensi/nominal.
- **Split & Gabung Dokumen**:
  - Split PDF/Word/PPT berdasarkan pola.
  - Gabungkan dokumen dengan tipe yang sama.

## Menjalankan
1. Install dependency:
   - `pip install -r requirements.txt`
2. Jalankan Streamlit:
   - `streamlit run app.py`

## Password Masuk Aplikasi
- Aplikasi sekarang memakai password sebelum user bisa masuk ke halaman tools.
- Password default: `dokumen123`
- Disarankan segera ganti password lewat environment variable `TOOLS_DOKUMEN_PASSWORD`
- Alternatif lain, jika memakai Streamlit secrets, tambahkan `app_password`

Contoh PowerShell:

```powershell
$env:TOOLS_DOKUMEN_PASSWORD = "password-baru-anda"
streamlit run app.py
```
