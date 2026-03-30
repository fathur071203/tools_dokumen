
# Tools Dokumen (Streamlit)

Aplikasi Streamlit dengan halaman utama berisi kumpulan tools.

Panduan keamanan lengkap untuk pengguna umum tersedia di: **README_KEAMANAN.md**

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
- Login + registrasi singkat (nama, email, unit/divisi) sebelum akses aplikasi.
- Form **Registrasi user baru** di halaman login untuk menambahkan user ke sheet `users`.
- Tracking siapa yang masuk ke aplikasi ke Google Spreadsheet (`users` + `access_log`).
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
  - PDF ke Word/PPT/Excel.
  - Word/Excel/PPT dan gambar ke PDF.
- **Watermark PDF**:
  - Watermark teks custom.
  - Pilihan posisi watermark.
  - Orientasi lurus atau miring.
  - Upload gambar PNG sebagai watermark.
- **Split & Gabung Dokumen**:
  - Split PDF/Word/PPT berdasarkan pola.
  - Gabungkan dokumen dengan tipe yang sama.

## Menjalankan
1. Install dependency:
   - `pip install -r requirements.txt`
2. Jalankan aplikasi sesuai kebutuhan:
  - **Tools Dokumen utama (tanpa chatbot):** `streamlit run app.py`
  - **Chatbot Regulasi terpisah:** `streamlit run Web_Chatbot/app.py` (lihat panduan di `Web_Chatbot/README.md`)

## Login Aplikasi
- Aplikasi memakai **username + password per user** (bukan password global/default).
- User baru dibuat lewat form **Registrasi user baru** di halaman login.
- Password user disimpan dalam bentuk hash (`SHA-256`) di sheet `users`.

Contoh PowerShell:

```powershell
streamlit run app.py
```

## Chatbot Dipisah ke Web_Chatbot
Seluruh fitur chatbot sudah dipisahkan penuh ke folder `Web_Chatbot` dan tidak lagi menjadi bagian aplikasi utama.
Untuk konfigurasi/jalankan chatbot, ikuti panduan di `Web_Chatbot/README.md`.

## Hardening Keamanan (Sudah Diimplementasikan)
- Login protection:
  - Lock sementara setelah 5 kali gagal login (10 menit).
  - Pesan login dibuat generik agar tidak membuka informasi akun.
- Password user:
  - Penyimpanan password menggunakan salted PBKDF2-SHA256 (`pbkdf2_sha256$...`).
  - Tetap kompatibel dengan hash lama SHA-256 (legacy).
  - Registrasi mewajibkan password kuat: minimal 10 karakter + huruf besar + huruf kecil + angka + simbol.
- Upload security:
  - Validasi jumlah file, ukuran per file, total ukuran upload.
  - Blokir ekstensi berbahaya (`.exe`, `.dll`, `.bat`, `.ps1`, dll).
  - Validasi ekstensi ketat untuk fitur tertentu (mis. watermark PDF/PNG, split-merge tipe dokumen yang didukung).
- DLP (Data Leakage Prevention) chatbot:
  - Mencegah prompt yang mencoba meminta dump dokumen mentah/kredensial.
  - Menyamarkan otomatis data sensitif pada jawaban (email, nomor telepon, NIK/NPWP, API key, dan nomor panjang).
  - Menampilkan path sumber dokumen dalam format minim (tidak menampilkan struktur path penuh).
- Enkripsi dokumen:
  - Fitur File Locker tetap menggunakan enkripsi kuat berbasis password.
  - PDF terenkripsi tetap berformat PDF berpassword; non-PDF memakai format `.encrypted`.

### Konfigurasi Limit Upload via `.env` (opsional)
```dotenv
TOOLS_DOKUMEN_MAX_FILES=25
TOOLS_DOKUMEN_MAX_FILE_MB=50
TOOLS_DOKUMEN_MAX_TOTAL_MB=250
TOOLS_DOKUMEN_DLP_ENABLED=true
```

## Tracking Login ke Spreadsheet (pakai `static/credentials.json` atau Streamlit Secrets)
1. Pilih salah satu cara credential Google Service Account:
  - simpan file di `static/credentials.json`, atau
  - isi secret `GOOGLE_SERVICE_ACCOUNT_JSON` (lihat contoh di `.streamlit/secrets.toml.example`).
2. Share spreadsheet ke email service account pada file JSON.
3. Set salah satu konfigurasi berikut:
  - `TOOLS_DOKUMEN_SPREADSHEET_ID` (disarankan), atau
  - `TOOLS_DOKUMEN_SPREADSHEET_NAME`
  - Jika hanya `TOOLS_DOKUMEN_SPREADSHEET_NAME` yang dipakai dan spreadsheet belum ada, aplikasi akan mencoba membuat spreadsheet baru otomatis.

Catatan: saat `GOOGLE_SERVICE_ACCOUNT_JSON` tersedia, aplikasi akan otomatis membuat `static/credentials.json` saat runtime.

Contoh PowerShell:

```powershell
$env:TOOLS_DOKUMEN_SPREADSHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz"
streamlit run app.py
```

Saat login berhasil, aplikasi akan:
- menambah/memperbarui data user di sheet `users`
- mencatat aktivitas login di sheet `access_log`
