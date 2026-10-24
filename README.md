# AutoKetik

AutoKetik adalah skrip Python yang mengambil teks dari file, clipboard, atau Google Docs yang bisa diakses publik, lalu mengetikkannya satu per satu ke aplikasi yang sedang aktif. File HTML hasil unduhan Google Docs dapat dibaca dengan format seperti heading, alignment, ukuran font, dan daftar.

> Gunakan hanya pada dokumen yang Anda miliki atau berhak mengedit. Skrip mengendalikan keyboard dan akan mengetik ke jendela yang aktif.

## Persyaratan

- Python 3.14.4
- Windows, macOS, atau Linux dengan akses keyboard yang diizinkan untuk aplikasi terminal/Python
- Paket Python: `pynput`, `requests`, dan `pyperclip`

Instal paket:

```powershell
python -m pip install -r requirements.txt
```

## Menjalankan

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
``

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
