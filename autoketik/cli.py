"""
autoketik.cli - Antarmuka baris perintah (CLI) untuk AutoKetik.
"""

import argparse
import random
import re
import sys
import time

from .config import Config, StopTyping, require_pynput, Key, keyboard
from .parser import parse_html, fetch_gdoc, normalize
from .planner import plan, parse_range
from .engine import Typist


def print_preview(blocks):
    for k, b in enumerate(blocks, 1):
        tag = f"H{b.heading}" if b.heading else ("LI" if b.lst else "P")
        sizes = sorted({r.size for r in b.runs if r.size})
        flags = "".join(
            f for f, on in (("B", any(r.b for r in b.runs)),
                            ("I", any(r.i for r in b.runs)),
                            ("U", any(r.u for r in b.runs))) if on
        )
        snippet = b.text.replace("\v", " / ")[:50]
        print(
            f"{k:3}. [{tag:<3} {b.align:<7} first={b.first:g} left={b.left:g} "
            f"line={b.line:g} sp={b.before:g}/{b.after:g} "
            f"size={sizes or '-'} {flags or '-'}] {snippet!r}"
        )


def main():
    ap = argparse.ArgumentParser(description="Simulasi pengetikan ala manusia")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="Link / ID Google Docs (harus bisa diakses publik)")
    src.add_argument("--file", help="Path file .txt atau .html (hasil download Docs)")
    src.add_argument("--clipboard", action="store_true", help="Ambil teks dari clipboard")

    ap.add_argument("--wpm", default="60",
                    help="WPM tunggal ('60') atau rentang ('40-75') yang bergelombang")
    ap.add_argument("--wave-period", type=float, default=120,
                    help="Detik per siklus cepat->lambat->cepat, default 120")
    ap.add_argument("--start", choices=["fast", "slow"], default="fast",
                    help="Mulai dari kecepatan maksimum (fast) atau minimum (slow)")
    ap.add_argument("--typo-rate", default="0.03",
                    help="Peluang typo per huruf: '0.03' atau rentang '0.01-0.06' "
                         "(ikut gelombang: cepat = lebih banyak typo). 0 = mati")
    ap.add_argument("--typo-delay", default="0.8-2.0",
                    help="Jeda 'sadar ada typo' sebelum mulai membenarkan typo (detik), mis. '0.8-2.0'")
    ap.add_argument("--typo-words", default="1-3",
                    help="Rentang jumlah kata yang terus diketik sebelum sadar typo lalu menghapusnya (mis. '1-3' atau '0-2')")
    ap.add_argument("--shift-delay", default="0.12-0.3",
                    help="Jeda tambahan saat mengetik karakter spesial berkombinasi Shift (detik), mis. '0.1-0.25'")
    ap.add_argument("--think-every", default="8-25", help="Jeda berpikir tiap N kata")
    ap.add_argument("--think-pause", default="1.5-6", help="Lama jeda berpikir (detik)")
    ap.add_argument("--delay", type=int, default=8, help="Hitung mundur sebelum mulai (detik)")
    ap.add_argument("--seed", type=int, help="Seed acak (opsional)")
    ap.add_argument("--no-format", action="store_true", help="Abaikan format, ketik teks polos")
    ap.add_argument("--base-size", type=float, default=11,
                    help="Ukuran font default dokumen tujuan (pt), default 11")
    ap.add_argument("--mac", action="store_true", default=sys.platform == "darwin",
                    help="Pakai Cmd/Option, bukan Ctrl/Alt (otomatis di macOS)")
    ap.add_argument("--base-spacing", default="1.15,0,0",
                    help="Spasi default dokumen tujuan: baris,sebelum,sesudah (default 1.15,0,0)")
    ap.add_argument("--spacing-menu", default="Custom spacing",
                    help="Teks menu Docs untuk dialog spasi kustom; sesuaikan bahasa UI "
                         "(mis. 'Spasi kustom')")
    ap.add_argument("--decimal-comma", action="store_true",
                    help="Pakai koma desimal saat mengisi dialog (1,5) bila Docs-mu begitu "
                         "(otomatis aktif jika --spacing-menu mengandung 'kustom')")
    ap.add_argument("--apply-tabs", type=int, default=2,
                    help="Jumlah Tab dari field 'After' ke tombol Apply (default 2: Cancel lalu Apply). "
                         "0 = langsung Enter di field")
    ap.add_argument("--test-spacing", action="store_true",
                    help="Hanya tes otomatisasi spasi (1.5 / sesudah 10pt) di dokumen kosong")
    ap.add_argument("--break-every", default=None,
                    help="Istirahat (tunggu F9) setiap N bab, mis. '3' atau rentang acak '2-4'")
    ap.add_argument("--break-level", type=int, default=1,
                    help="Heading level 1..N dianggap bab (default 1 = hanya H1)")
    ap.add_argument("--chapter-regex", default=None,
                    help="Regex tambahan penanda bab, mis. '^BAB\\b'")
    ap.add_argument("--resume-delay", type=int, default=5,
                    help="Hitung mundur setelah lanjut dari istirahat (detik)")
    ap.add_argument("--preview", action="store_true",
                    help="Tampilkan hasil parsing format lalu keluar (tidak mengetik)")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    blocks = None
    plain = None
    if args.url:
        if args.no_format:
            plain = fetch_gdoc(args.url, "txt")
        else:
            blocks = parse_html(fetch_gdoc(args.url, "html"))
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            raw = f.read()
        if args.file.lower().endswith((".html", ".htm")) and not args.no_format:
            blocks = parse_html(raw)
        else:
            plain = raw
    else:
        import pyperclip
        plain = pyperclip.paste()

    if blocks is not None:
        if not blocks:
            sys.exit("Teks kosong.")
        if args.preview:
            print_preview(blocks)
            return
        try:
            bs = tuple(float(x) for x in args.base_spacing.replace(";", ",").split(","))
            assert len(bs) == 3
        except Exception:
            sys.exit("--base-spacing harus 3 angka, mis. 1.15,0,0")
        require_pynput()
        brk = parse_range(args.break_every, int) if args.break_every else None
        creg = re.compile(args.chapter_regex, re.I) if args.chapter_regex else None
        actions = plan(blocks, args.base_size, args.mac, bs, brk, args.break_level, creg)
    else:
        plain = normalize(plain or "")
        if not plain:
            sys.exit("Teks kosong.")
        if args.preview:
            print("(teks polos, tidak ada format)\n" + plain[:500])
            return
        actions = [("text", plain)]

    cfg = Config(
        wpm=parse_range(args.wpm, float),
        typo_rate=parse_range(args.typo_rate, float),
        wave_period=args.wave_period,
        start_fast=args.start == "fast",
        think_every=parse_range(args.think_every, int),
        think_pause=parse_range(args.think_pause, float),
        notice_pause=parse_range(args.typo_delay, float),
        shift_delay=parse_range(args.shift_delay, float),
        typo_words=parse_range(args.typo_words, int),
        mac=args.mac,
        spacing_menu=args.spacing_menu,
        decimal_comma=args.decimal_comma or "kustom" in args.spacing_menu.lower(),
        resume_delay=args.resume_delay,
        apply_tabs=args.apply_tabs,
    )
    if args.test_spacing:
        actions = [("spacing", 1.5, 0.0, 10.0)]

    total_chars = sum(len(a[1]) for a in actions if a[0] == "text")
    n_fmt = sum(1 for a in actions if a[0] in ("hot", "spacing"))
    n_brk = sum(1 for a in actions if a[0] == "break")
    avg_wpm = sum(cfg.wpm) / 2
    print(f"Teks: {total_chars} karakter | aksi format: {n_fmt} | titik istirahat: {n_brk}")
    print(f"WPM: {cfg.wpm[0]:g}-{cfg.wpm[1]:g} (siklus {cfg.wave_period:g}s, mulai {args.start}) "
          f"| typo: {cfg.typo_rate[0]*100:.1f}%-{cfg.typo_rate[1]*100:.1f}%")
    print(f"Shift delay: {cfg.shift_delay[0]:g}-{cfg.shift_delay[1]:g}s "
          f"| jeda sadar typo: {cfg.notice_pause[0]:g}-{cfg.notice_pause[1]:g}s "
          f"| ketik sebelum sadar: {cfg.typo_words[0]}-{cfg.typo_words[1]} kata")
    print(f"Estimasi (belum termasuk jeda): ~{total_chars / (avg_wpm * 5):.1f} menit")
    print("Hotkey: ESC berhenti | F9 pause | F10/F11 typo +/- | F8/F7 WPM +/-")

    typist = Typist(cfg)

    def on_press(key):
        if key == Key.esc:
            typist.stop.set()
            return False
        if key == Key.f9:
            if typist.paused.is_set():
                typist.paused.clear()
                print("\n[lanjut]")
            else:
                typist.paused.set()
                print("\n[pause]")
        elif key == Key.f10:
            typist.typo_adj += 0.01
            print(f"\n[typo sekarang ~{typist.cur_typo()*100:.1f}%]")
        elif key == Key.f11:
            typist.typo_adj -= 0.01
            print(f"\n[typo sekarang ~{typist.cur_typo()*100:.1f}%]")
        elif key == Key.f8:
            typist.wpm_adj += 5
            print(f"\n[WPM sekarang ~{typist.cur_wpm():.0f}]")
        elif key == Key.f7:
            typist.wpm_adj -= 5
            print(f"\n[WPM sekarang ~{typist.cur_wpm():.0f}]")

    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()

    for s in range(args.delay, 0, -1):
        print(f"Mulai dalam {s}... (klik dokumen tujuan sekarang)", end="\r", flush=True)
        time.sleep(1)
    print(" " * 60, end="\r")

    try:
        typist.run(actions)
        print("Selesai.")
    except StopTyping:
        print("Dihentikan (ESC).")
    except KeyboardInterrupt:
        print("Dihentikan (Ctrl+C).")
