# Web_Chatbot

Aplikasi chatbot regulasi yang terpisah dari aplikasi tools utama.

## Jalankan

Masuk ke folder Web_Chatbot lalu jalankan:

- `streamlit run app.py`

## Konfigurasi (2 versi)

### 1) Versi Local

1. Copy `.env.example` menjadi `.env`
2. Isi nilai environment yang dibutuhkan
3. Siapkan kredensial Google dengan salah satu cara:
	- simpan file service account di `static/credentials.json`, atau
	- isi `GOOGLE_SERVICE_ACCOUNT_JSON` di `.env` (opsional)

### 2) Versi Streamlit Cloud

1. Buka **App Settings > Secrets**
2. Paste isi secrets sesuai contoh di `.streamlit/secrets.toml.example`

- `credentials.json` **tidak perlu di-commit**.
- App akan otomatis membuat `static/credentials.json` saat runtime dari `GOOGLE_SERVICE_ACCOUNT_JSON`.

## Data yang dipakai (lokal Web_Chatbot)

- Dokumen RAG: `Web_Chatbot/static/data/structured_docs`
- Service account Google: `Web_Chatbot/static/credentials.json`

## Catatan

- Login/registrasi tetap pakai spreadsheet yang sama dengan aplikasi utama.
- User status `pending` tetap menunggu approval admin.
- Aplikasi chatbot ini dibuat standalone di dalam folder `Web_Chatbot`.
