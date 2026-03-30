# Panduan Keamanan Aplikasi Tools Dokumen

Dokumen ini menjelaskan fitur keamanan yang sudah diterapkan pada aplikasi ini, dengan bahasa sederhana agar mudah dipahami pengguna non-teknis.

---

## 1) Ringkasan singkat (versi awam)

Di website/aplikasi ini, keamanan dilakukan di beberapa lapis:

1. **Akses user dijaga dengan login**.
2. **Password user tidak disimpan dalam bentuk asli** (disimpan sebagai hash kuat).
3. **Upload file dibatasi dan disaring** untuk mengurangi risiko file berbahaya.
4. **Dokumen sensitif bisa dikunci dengan enkripsi** lewat fitur File Locker.
5. **Chatbot memakai DLP** (Data Leakage Prevention) untuk mencegah kebocoran informasi sensitif.
6. **Sesi login punya batas waktu** (auto logout jika tidak aktif).

Ibaratnya, aplikasi ini memakai pagar berlapis: pintu login, pemeriksaan barang bawaan (file upload), lemari besi (enkripsi), dan petugas sensor informasi (DLP chatbot).

---

## 2) Keamanan Login & Akun

### a) Login per user
- Akses aplikasi memakai username + password user masing-masing.
- User baru didaftarkan dari form registrasi.

### b) Password tidak disimpan mentah
- Password user disimpan sebagai **hash salted PBKDF2-SHA256**.
- Artinya password asli tidak tersimpan di spreadsheet.
- Sistem masih kompatibel dengan hash lama (legacy), tetapi user baru otomatis memakai metode yang lebih aman.

### c) Password policy kuat saat registrasi
Password wajib:
- minimal 10 karakter,
- ada huruf besar,
- ada huruf kecil,
- ada angka,
- ada simbol.

### d) Anti brute-force
- Jika gagal login berulang, akun/sesi login akan **dikunci sementara**.
- Saat ini: **5 kali gagal** → lock **10 menit**.

### e) Session timeout
- Jika tidak ada aktivitas, sesi akan berakhir otomatis (auto logout).
- Ini mencegah akun tetap terbuka saat perangkat ditinggal.

---

## 3) Keamanan Upload File

Semua fitur yang menerima upload (Locker, Kompresi, Konversi, Watermark, Split/Merge) sudah melalui validasi keamanan:

1. **Batas jumlah file per proses**.
2. **Batas ukuran per file**.
3. **Batas total ukuran upload per proses**.
4. **Blokir ekstensi berisiko** (contoh: `.exe`, `.dll`, `.bat`, `.ps1`, dll).
5. **Validasi tipe file sesuai fitur** (misal watermark hanya PDF/PNG sesuai mode).

Tujuannya:
- mengurangi risiko upload file berbahaya,
- mencegah overload resource server,
- menekan peluang penyalahgunaan input file.

---

## 4) Keamanan Dokumen (Enkripsi)

### Fitur File Locker
Aplikasi menyediakan enkripsi dokumen berbasis password.

- **File non-PDF**: dikunci menjadi format `.encrypted`.
- **File PDF**: tetap PDF, tetapi diproteksi password.
- Nama output dibuat generik (tidak menampilkan nama asli file di hasil akhir).

### Teknologi enkripsi yang dipakai
- Derivasi kunci: **PBKDF2-HMAC-SHA256** (iterasi tinggi).
- Enkripsi data non-PDF: **Fernet** (simetris terautentikasi).

Manfaat praktis:
- Dokumen tidak bisa dibuka tanpa password.
- Jika file berpindah tangan, isi tetap terlindungi selama password tidak bocor.

---

## 5) Keamanan Chatbot (DLP)

Chatbot sudah diberi lapisan DLP (Data Leakage Prevention):

### a) Blokir pertanyaan berisiko
Contoh yang dibatasi:
- meminta dump teks mentah full dokumen,
- meminta kredensial, token, API key, password, secret.

### b) Redaksi otomatis informasi sensitif
Sistem menyamarkan data sensitif pada output chatbot, misalnya:
- email,
- nomor telepon,
- NIK,
- NPWP,
- pola API key/token tertentu,
- nomor panjang tertentu.

### c) Path sumber diringkas
Referensi dokumen tetap ditampilkan, namun label path disederhanakan agar tidak terlalu membocorkan struktur internal folder.

---

## 6) Keamanan Proses Internal

### a) Pemrosesan file sementara
- Beberapa fitur konversi memakai file sementara (temporary file) di sistem.
- File sementara dikelola lewat mekanisme temporary directory dan dibersihkan otomatis setelah proses selesai.

### b) Tidak ada penyimpanan dokumen permanen oleh aplikasi utama
- Alur normal fitur memproses file dari upload lalu mengembalikan hasil ke user.
- Aplikasi tidak didesain sebagai penyimpanan dokumen permanen pengguna.

> Catatan: tetap ikuti kebijakan infrastruktur/server organisasi (backup, logging, endpoint protection, akses OS, dsb), karena itu berada di luar kode aplikasi.

---

## 7) Konfigurasi Keamanan via `.env`

Anda bisa mengatur limit keamanan tambahan melalui environment variable:

```dotenv
TOOLS_DOKUMEN_MAX_FILES=25
TOOLS_DOKUMEN_MAX_FILE_MB=50
TOOLS_DOKUMEN_MAX_TOTAL_MB=250
TOOLS_DOKUMEN_DLP_ENABLED=true
```

Arti singkat:
- `MAX_FILES`: maksimum jumlah file per proses.
- `MAX_FILE_MB`: maksimum ukuran satu file.
- `MAX_TOTAL_MB`: maksimum total ukuran semua file dalam satu proses.
- `DLP_ENABLED`: aktif/nonaktifkan proteksi DLP chatbot.

---

## 8) Batasan & Tanggung Jawab Pengguna

Walau keamanan sudah diperkuat, pengguna tetap wajib:

1. Jangan membagikan password akun.
2. Jangan memakai password yang sama di banyak sistem.
3. Gunakan fitur File Locker untuk dokumen sensitif.
4. Jangan memasukkan data rahasia yang tidak perlu ke chatbot.
5. Logout setelah selesai, terutama di perangkat bersama.

---

## 9) Rekomendasi tambahan (opsional, untuk level enterprise)

Jika ingin lebih ketat lagi, berikut tahap lanjutan yang direkomendasikan:

1. Integrasi SSO/LDAP/AD (tanpa password lokal).
2. MFA (multi-factor authentication).
3. Rate-limit berbasis IP/proxy di level reverse proxy.
4. Audit log keamanan terpusat (SIEM).
5. Secret manager untuk API key (jangan simpan plaintext di file lokal).
6. Antivirus scanning untuk file upload di gateway.
7. Enkripsi disk dan hardening OS server.

---

## 10) Status implementasi saat ini

Fitur pada dokumen ini sudah sesuai implementasi kode aplikasi saat ini dan diperbarui per Maret 2026.
