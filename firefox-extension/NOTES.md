# AutoKetik – ekstensi Firefox: temuan pengetikan di Google Docs

## Konteks

- Proyek: AutoKetik, skrip Python yang mengetik teks ke Google Docs. Versi ekstensi Firefox ada di
  folder `firefox-extension/` (branch `feat/add-firefox-extension`): Manifest V3, `background.scripts`,
  `content_scripts` dengan `all_frames: true`, popup, dan sidebar.
- Target: mengetik dengan simulasi manusia (WPM, typo + koreksi, jeda) ke kolom teks biasa dan ke Google Docs.
- Semua tes di bawah dijalankan manual di Firefox, dari Console halaman Docs (konteks halaman).

## Struktur editor Google Docs

- Input diterima lewat iframe tersembunyi `iframe.docs-texteventtarget-iframe` (`src="javascript:undefined"`).
  Iframe itu satu origin, jadi `contentDocument` bisa diakses.
- `document.activeElement` di dalam iframe adalah sebuah `DIV` (contenteditable), bukan `BODY`.
- Content script ikut disuntikkan ke dalam iframe itu sendiri (log: `frame utama: false`). Akibatnya frame utama
  dan frame iframe bisa sama-sama mengetik -> ketikan ganda, kecuali salah satu mengalah.

## Hasil uji: cara input yang diterima / ditolak Docs

| Cara                                                                          | Hasil                                                                            |
| ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `doc.execCommand("insertText")` pada dokumen iframe                           | mengembalikan `true`, tetapi teks TIDAK muncul                                   |
| `ClipboardEvent("paste")` buatan                                              | Firefox mengabaikan `clipboardData` di konstruktor (string kosong); tidak muncul |
| `InputEvent("beforeinput", insertText)`                                       | tidak muncul                                                                     |
| **`compositionstart` -> `compositionupdate{data}` -> `compositionend{data}`** | **berhasil, teks muncul**                                                        |
| Enter lewat komposisi dengan `data: "\n"`                                     | berhasil (baris baru)                                                            |
| Enter lewat `keydown`+`keypress`+`keyup` (`key:"Enter"`, `keyCode:13`)        | berhasil (baris baru)                                                            |
| Enter lewat `beforeinput insertParagraph`                                     | tidak berhasil                                                                   |
| Backspace lewat `keydown`+`keypress`+`keyup` (`key:"Backspace"`, `keyCode:8`) | berhasil, menghapus 1 karakter                                                   |
| Backspace lewat `beforeinput deleteContentBackward`                           | tidak berhasil                                                                   |
| Membatalkan komposisi (`update` dengan `data:""` lalu `end` dengan `data:""`) | tidak meninggalkan teks sisa                                                     |

Hasil tes akhir di dokumen: `[1]` / `[2]` / `[3][4]abcde123` (lihat urutan tes untuk pembacaannya).

## Kesimpulan desain

- Di Docs: karakter biasa HARUS lewat event komposisi; Enter dan Backspace lewat event keyboard buatan
  (keydown, keypress, keyup). `execCommand`, paste buatan, dan `beforeinput` jangan dipakai.
- Event keyboard buatan untuk huruf biasa tidak berpengaruh, jadi tidak dipakai di mode Docs.
- Di kolom biasa (`input`, `textarea`, `contenteditable`) `document.execCommand` dari ownerDocument elemen tetap dipakai.
- Frame utama harus mengalah bila iframe sudah punya content script yang mengetik (pakai `postMessage` "claimed").
- Docs tidak memberi umpan balik: hasil tidak bisa diverifikasi dari kode, hanya dengan melihat dokumen.

## Status `content.js` (versi terbaru)

- Mode Docs: komposisi per karakter, Enter dan Backspace lewat event keyboard (`DOCS_ENTER = "key"`),
  typo aktif kembali, frame utama mengalah ke iframe.
- Perbaikan umum: memakai `ownerDocument`/`defaultView` target, event `input` buatan hanya saat fallback,
  `sleep()` sadar jeda, `range()` menangani string kosong, seed dipulihkan setelah run, error dilaporkan ke UI,
  `DEBUG` log lewat `console.debug`.
- Diuji di jsdom (urutan event dan koreksi typo benar), tetapi BELUM diuji dari ekstensi di Docs sungguhan.

## Risiko / hal yang belum terbukti

- Semua tes dijalankan dari konteks halaman. Content script berjalan di dunia content script (Firefox Xray),
  dan event buatannya bisa berperilaku berbeda. Bila teks tidak muncul dari ekstensi padahal tes Console berhasil,
  jalankan bagian pengetikan di dunia halaman: `"world": "MAIN"` pada `content_scripts` (Firefox 128+).
- Izin host MV3 di Firefox bisa belum aktif: cek `about:addons` -> AutoKetik -> Izin.
- Perilaku Enter lewat keyboard di daftar berpoin atau paragraf berformat belum diuji.
- Impor HTML dan hasil ekspor Google Docs diparse di content script (jangan kirim HTML mentah sebagai teks ketikan). Parser membaca style inline/CSS class, paragraf, heading, `<br>`, alignment, dan indentasi dasar.
- Sidebar tidak memiliki tombol `openSidebar`; handler popup-only harus opsional agar error null tidak menghentikan pemasangan handler tombol lainnya.
- Shortcut alignment dan indentasi tetap perlu diuji di Docs nyata. Spacing sebelum/sesudah paragraf dan line spacing juga belum diterapkan.
- Sumber HTML yang dimuat ditampilkan sebagai pratinjau dokumen terisolasi di popup dan sidebar; tombol “Lihat sumber HTML” membuka teks sumber bila perlu. HTML asli tetap menjadi payload untuk pengetikan.
- Statistik impor HTML menghitung teks pada paragraf, heading, dan item daftar saja; panjang CSS/markup tidak dilaporkan sebagai karakter isi. Progress pengetikan menggunakan panjang teks hasil parser.
- Folder `icons/` belum terkonfirmasi ada.

## Noise di Console yang bisa diabaikan

`NS_ERROR_DOM_NETWORK_ERR` ke `play.google.com/log`, "Error in parsing value ... KixCss_ltr.css",
"Attempt to set a forbidden header: Connection", "Empty string passed to getElementById()", XHR `NS_BINDING_ABORTED`.
Semuanya dari kode Docs sendiri.
