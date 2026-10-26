# AutoKetik

AutoKetik adalah skrip Python yang mengambil teks dari file, clipboard, atau Google Docs yang bisa diakses publik, lalu mengetikkannya satu per satu ke aplikasi yang sedang aktif. File HTML hasil unduhan Google Docs dapat dibaca dengan format seperti heading, alignment, ukuran font, dan daftar.

> Gunakan hanya pada dokumen yang Anda miliki atau berhak mengedit. Skrip mengendalikan keyboard dan akan mengetik ke jendela yang aktif.

## Persyaratan

- Python 3.14.4
- Windows, macOS, atau Linux dengan akses keyboard yang diizinkan untuk aplikasi terminal/Python
- Paket Python: `pynput`, `requests`, `pyperclip`, dan `customtkinter` (untuk GUI)

Instal paket:

```powershell
python -m pip install -r requirements.txt
```

## Menjalankan Antarmuka Grafis (GUI)

Anda bisa membuka aplikasi dengan salah satu cara berikut:
1. **Klik 2x file [`Buka_AutoKetik.bat`](file:///e:/Project/Script/AutoKetik/Buka_AutoKetik.bat)** (Paling cepat dan bersih, tanpa jendela terminal hitam di background).
2. Atau jalankan via terminal:

```powershell
python AutoKetikGUI.py
```

Fitur pada GUI:
- Pilihan sumber dokumen interaktif (File browser `.txt`/`.html`, Clipboard dengan tombol preview, atau link Google Docs).
- Penggeser (slider) kecepatan WPM dan simulasi typo real-time dengan preset siap pakai (Santai, Normal, Cepat).
- Live progress bar dan indikator metrik pengetikan (karakter tersisa, kecepatan WPM aktif, estimasi waktu).
- Tombol Preview untuk memeriksa hasil parsing dokumen sebelum mulai mengetik.
- Otomatis minimize jendela GUI saat hitung mundur dimulai agar jendela tujuan langsung aktif.
- Kontrol keyboard darurat tetap berfungsi penuh (`Esc` berhenti, `F9` pause/lanjut).

## Menjalankan via Terminal (CLI)

Buka terminal di folder proyek, lalu jalankan perintah yang sesuai.

### Mengetik file teks

```powershell
python AutoKetik.py --file "naskah.txt"
```

### Mengetik file HTML

File HTML dapat mempertahankan format yang dikenali parser:

```powershell
python AutoKetik.py --file "naskah.html"
```

### Mengambil teks dari clipboard

Salin teks terlebih dahulu, lalu jalankan:

```powershell
python AutoKetik.py --clipboard
```

### Mengambil teks dari Google Docs

Dokumen sumber harus disetel ke **Anyone with the link / Siapa saja yang memiliki link – Viewer**:

```powershell
python AutoKetik.py --url "https://docs.google.com/document/d/ID_DOKUMEN/edit"
```

Secara default, sumber Google Docs diambil sebagai HTML agar format yang didukung dapat dipertahankan. Gunakan `--no-format` untuk mengambil teks polos.

## Alur penggunaan

1. Siapkan dokumen tujuan dan letakkan kursor di posisi pengetikan.
2. Jalankan perintah AutoKetik.
3. Selama hitung mundur (default 8 detik), pindah ke jendela dokumen tujuan.
4. Biarkan jendela tujuan aktif saat skrip mengetik.
5. Tekan **Esc** untuk menghentikan proses kapan saja.

Untuk memeriksa hasil pembacaan tanpa mengetik, tambahkan `--preview`:

```powershell
python AutoKetik.py --file "naskah.html" --preview
```

## Pengaturan umum

| Opsi | Kegunaan | Contoh |
|---|---|---|
| `--wpm` | Kecepatan mengetik dalam kata per menit; menerima angka atau rentang | `--wpm 55` atau `--wpm 40-75` |
| `--typo-rate` | Frekuensi simulasi typo; `0` menonaktifkannya | `--typo-rate 0` atau `--typo-rate 0.01-0.04` |
| `--typo-words` | Rentang jumlah kata yang terus diketik sebelum sadar ada typo lalu menghapusnya | `--typo-words 1-3` atau `--typo-words 0-2` |
| `--typo-delay` | Jeda "sadar ada typo" sebelum mulai membenarkan typo, dalam detik | `--typo-delay 0.8-2.0` |
| `--shift-delay` | Jeda tambahan saat mengetik karakter spesial yang memerlukan kombinasi Shift (detik) | `--shift-delay 0.12-0.3` |
| `--delay` | Hitung mundur sebelum mulai, dalam detik | `--delay 12` |
| `--no-format` | Abaikan format dan ketik sebagai teks polos | `--url "..." --no-format` |
| `--wave-period` | Durasi siklus perubahan kecepatan, dalam detik | `--wave-period 180` |
| `--start` | Mulai dari kecepatan maksimum (`fast`) atau minimum (`slow`) | `--start slow` |
| `--think-every` | Rentang jumlah kata di antara jeda berpikir | `--think-every 8-25` |
| `--think-pause` | Rentang durasi jeda berpikir, dalam detik | `--think-pause 1.5-6` |
| `--break-every` | Istirahat setelah sejumlah heading bab pada sumber HTML/Google Docs berformat; lanjutkan dengan F9 | `--break-every 3` atau `--break-every 2-4` |
| `--preview` | Tampilkan hasil pembacaan/parsing tanpa mengetik | `--file "naskah.html" --preview` |

Contoh konfigurasi:

```powershell
python AutoKetik.py --file "naskah.html" --wpm 40-75 --typo-rate 0.01-0.04 --wave-period 180
```

Daftar lengkap opsi tersedia melalui:

```powershell
python AutoKetik.py --help
```

## Tombol pintas

| Tombol | Fungsi |
|---|---|
| `Esc` | Berhenti |
| `F9` | Jeda atau lanjut; juga melanjutkan setelah istirahat bab |
| `F10` / `F11` | Naikkan / turunkan frekuensi typo sebesar 1% |
| `F8` / `F7` | Naikkan / turunkan kecepatan sebesar 5 WPM |

## Catatan

- `--url` memerlukan koneksi internet dan akses Viewer publik pada dokumen sumber. Jika tidak bisa dibagikan secara publik, unduh dokumen sebagai HTML atau salin teks ke clipboard.
- Format hanya diterapkan saat sumber dibaca sebagai HTML dan opsi `--no-format` tidak digunakan. Hasil format dapat bergantung pada bahasa dan konfigurasi Google Docs.
- Pada macOS, skrip memilih tombol pintas Command secara otomatis. Opsi `--mac` tersedia untuk mengaktifkannya secara manual.
- Jika sistem operasi meminta izin aksesibilitas/keyboard untuk `pynput`, berikan izin tersebut kepada aplikasi terminal atau Python yang menjalankan skrip.

## Struktur Proyek

Proyek ini telah diorganisasi secara modular:

```text
AutoKetik/
│
├── autoketik/                  # Paket Python modular
│   ├── __init__.py             # Public API & ekspor modul
│   ├── config.py               # Data class (Config, Block, Run) & konstanta keyboard
│   ├── parser.py               # Parser HTML Google Docs & fetcher URL
│   ├── planner.py              # Perencana urutan pengetikan dan formatting
│   ├── engine.py               # Mesin utama (Typist & GUITypist)
│   ├── cli.py                  # Antarmuka CLI & argparser
│   └── gui.py                  # Antarmuka GUI CustomTkinter
│
├── AutoKetik.py                # Entry point utama untuk mode CLI
├── AutoKetikGUI.py             # Entry point utama untuk mode GUI
├── Buka_AutoKetik.bat          # Launcher Windows 1-klik tanpa terminal hitam
├── requirements.txt            # Dependensi paket Python
├── README.md                   # Panduan dokumentasi
├── LICENSE                     # Lisensi proyek
└── .gitignore                  # Berkas yang diabaikan Git
```
