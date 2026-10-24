#!/usr/bin/env python3
"""
AutoKetik.py - Simulasi pengetikan ala manusia (versi dengan format dokumen).

Fitur:
  * Ambil teks + FORMAT dari Google Docs (link publik) atau file .html hasil
    "Download > Web Page" dari Docs. File .txt / clipboard = teks polos.
  * Format yang ditiru: heading (H1-H6), rata teks (kiri/tengah/kanan/rata
    kiri-kanan), ukuran font, bold/italic/underline, indentasi baris pertama,
    indentasi kiri, dan daftar (bullet / nomor).
  * WPM bergelombang di antara dua nilai: cepat -> PERLAHAN melambat ->
    PERLAHAN cepat lagi (gelombang cosinus), contoh: --wpm 40-75
  * Frekuensi typo bisa berupa satu angka atau rentang (ikut gelombang kecepatan:
    makin cepat makin banyak typo) dan bisa diubah LIVE lewat hotkey.
  * Spasi baris (mis. 1.5) dan spasi sebelum/sesudah paragraf ikut disalin
    lewat dialog "Custom spacing" Docs (diotomatisasi).
  * ISTIRAHAT: setelah N bab (heading) program berhenti total sampai kamu
    menekan F9 secara manual. Contoh: --break-every 3  atau  --break-every 2-4
  * Hotkey: ESC = berhenti | F9 = pause/lanjut (juga untuk lanjut dari istirahat)
            F10 / F11 = typo naik / turun (1% per tekan)
            F8  / F7  = WPM naik / turun (5 per tekan)

Instalasi:
    pip install pynput requests pyperclip

Contoh:
    python AutoKetik.py --url "https://docs.google.com/document/d/XXXX/edit" --wpm 40-75
    python AutoKetik.py --url "..." --typo-rate 0.01-0.06 --wave-period 180
    python AutoKetik.py --file naskah.html --preview      # cek hasil parsing saja
    python AutoKetik.py --file naskah.txt --wpm 55 --typo-rate 0.02
    python AutoKetik.py --url "..." --no-format           # teks polos saja
    python AutoKetik.py --url "..." --break-every 3       # istirahat tiap 3 bab
    python AutoKetik.py --test-spacing --file x.txt       # tes otomatisasi spasi saja

Setelah script jalan ada hitung mundur. Klik dokumen tujuan (Google Docs kosong)
sebelum hitungan habis. Pastikan dokumen tujuan masih kosong & kursor di awal.
"""

import argparse
import math
import random
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser

try:
    from pynput import keyboard
    from pynput.keyboard import Controller, Key
except ModuleNotFoundError:
    keyboard = None
    Controller = None
    Key = None


def require_pynput():
    if keyboard is None or Controller is None or Key is None:
        raise RuntimeError(
            "Paket pynput belum terinstal. Jalankan: python -m pip install pynput requests pyperclip"
        )

# --------------------------------------------------------------------------
# Data pendukung
# --------------------------------------------------------------------------


def _build_neighbors():
    rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    offsets = [0.0, 0.25, 0.75]
    pos = {}
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            pos[ch] = (c + offsets[r], r)
    neighbors = {}
    for a, (ax, ay) in pos.items():
        neighbors[a] = [
            b
            for b, (bx, by) in pos.items()
            if b != a and ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 < 1.6
        ]
    return neighbors


NEIGHBORS = _build_neighbors()

FAST_BIGRAMS = set(
    "th he in er an re on at en nd ti es or te of ed is it al ar st to nt ng "
    "se ha as ou io le ve co me de hi ri ro ic ne ea ra ce li ch ll be ma si "
    "om ur ka an ng da ya me ber ter kan nya ang yan men per".split()
)

HARD_CHARS = set('!?@#$%^&*()_+{}|:"<>~')

# Daftar ukuran font preset Google Docs (dipakai Ctrl+Shift+. / Ctrl+Shift+,)
SIZES = [6, 7, 8, 9, 10, 11, 12, 14, 18, 24, 30, 36, 48, 60, 72, 96]
ALIGN_KEYS = {"left": "l", "center": "e", "right": "r", "justify": "j"}
INDENT_STEP = 36.0  # pt per tekan Tab / Ctrl+]


def snap_size(sz: float) -> int:
    return min(SIZES, key=lambda s: abs(s - sz))


class StopTyping(Exception):
    pass


@dataclass
class Config:
    wpm: tuple = (60.0, 60.0)           # (min, max)
    typo_rate: tuple = (0.03, 0.03)     # (min, max)
    wave_period: float = 120.0          # detik untuk 1 siklus cepat-lambat-cepat
    start_fast: bool = True
    think_every: tuple = (8, 25)        # setiap N kata, berhenti sejenak
    think_pause: tuple = (1.5, 6.0)     # detik
    sentence_pause: tuple = (0.4, 1.4)
    para_pause: tuple = (1.0, 3.5)
    comma_pause: tuple = (0.15, 0.5)
    notice_pause: tuple = (0.2, 0.8)    # jeda "sadar ada typo" sebelum backspace
    mac: bool = False
    spacing_menu: str = "Custom spacing"  # teks pencarian menu Docs (sesuaikan bahasa UI)
    decimal_comma: bool = False           # True jika Docs memakai koma desimal (1,5)
    resume_delay: int = 5                 # hitung mundur setelah lanjut dari istirahat
    apply_tabs: int = 2                   # jumlah Tab dari field 'After' ke tombol Apply (After -> Cancel -> Apply)


# --------------------------------------------------------------------------
# Model dokumen + parser HTML Google Docs
# --------------------------------------------------------------------------


@dataclass
class Run:
    text: str
    b: bool = False
    i: bool = False
    u: bool = False
    size: float = 0.0  # 0 = tidak diketahui / jangan diubah


@dataclass
class Block:
    heading: int = 0          # 0 = teks normal, 1..6 = Heading
    align: str = "left"
    first: float = 0.0        # indentasi baris pertama (pt)
    left: float = 0.0         # indentasi kiri (pt)
    lst: str = ""            # "", "ul", "ol"
    depth: int = 0            # kedalaman list
    line: float = 0.0         # spasi baris (1.15, 1.5, 2 ...), 0 = tidak diketahui
    before: float = 0.0       # spasi sebelum paragraf (pt)
    after: float = 0.0        # spasi sesudah paragraf (pt)
    runs: list = field(default_factory=list)

    @property
    def text(self):
        return "".join(r.text for r in self.runs)


def _pt(v):
    m = re.match(r"\s*(-?[\d.]+)\s*(pt|px|in|cm)?", v or "")
    if not m:
        return 0.0
    try:
        x = float(m.group(1))
    except ValueError:
        return 0.0
    return x * {"pt": 1, "px": 0.75, "in": 72, "cm": 28.35}[m.group(2) or "pt"]


def _line(v):
    v = (v or "").strip()
    try:
        if v.endswith("%"):
            return float(v[:-1]) / 100
        if v.endswith("pt") or v.endswith("px"):
            return 0.0
        return float(v)
    except ValueError:
        return 0.0


def parse_css(html: str) -> dict:
    css = {}
    for style in re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I):
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
            props = {}
            for kv in body.split(";"):
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    props[k.strip().lower()] = v.strip().lower()
            for s in sel.split(","):
                m = re.fullmatch(r"\.([\w-]+)", s.strip())
                if m:
                    css.setdefault(m.group(1), {}).update(props)
    return css


class DocParser(HTMLParser):
    BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"}
    INLINE = {"span", "a", "b", "strong", "i", "em", "u"}

    def __init__(self, css):
        super().__init__(convert_charrefs=True)
        self.css = css
        self.blocks = []
        self.cur = None
        self.stack = []
        self.lists = []
        self.skip = 0

    def _props(self, attrs):
        a = dict(attrs)
        d = {}
        for c in (a.get("class") or "").split():
            d.update(self.css.get(c, {}))
        for kv in (a.get("style") or "").split(";"):
            if ":" in kv:
                k, v = kv.split(":", 1)
                d[k.strip().lower()] = v.strip().lower()
        return d

    def end_block(self):
        if self.cur is not None:
            self.blocks.append(self.cur)
            self.cur = None
            self.stack = []

    def add(self, s):
        if self.cur is None or not s:
            return
        eff = {}
        for _, d in self.stack:
            eff.update(d)
        w = eff.get("font-weight", "400")
        bold = w in ("bold", "bolder") or (w.isdigit() and int(w) >= 600)
        ital = eff.get("font-style") == "italic"
        und = "underline" in eff.get("text-decoration", "")
        sz = _pt(eff.get("font-size"))
        runs = self.cur.runs
        if runs and (runs[-1].b, runs[-1].i, runs[-1].u, runs[-1].size) == (bold, ital, und, sz):
            runs[-1].text += s
        else:
            runs.append(Run(s, bold, ital, und, sz))

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "title"):
            self.skip += 1
            return
        if tag in ("ul", "ol"):
            self.end_block()
            self.lists.append(tag)
            return
        if tag in self.BLOCKS:
            if tag == "p" and self.cur is not None and self.cur.lst:
                return  # <p> di dalam <li>: tetap satu item
            self.end_block()
            d = self._props(attrs)
            b = Block()
            if tag[0] == "h" and len(tag) == 2:
                b.heading = int(tag[1])
            al = d.get("text-align", "left")
            b.align = al if al in ALIGN_KEYS else "left"
            b.first = _pt(d.get("text-indent"))
            b.line = _line(d.get("line-height"))
            b.before = _pt(d.get("padding-top"))
            b.after = _pt(d.get("padding-bottom"))
            if tag == "li":
                b.lst = self.lists[-1] if self.lists else "ul"
                b.depth = max(1, len(self.lists))
            else:
                b.left = _pt(d.get("margin-left"))
            self.cur = b
            return
        if tag == "br":
            self.add("\v")
            return
        if tag in self.INLINE:
            d = self._props(attrs)
            if tag in ("b", "strong"):
                d["font-weight"] = "700"
            if tag in ("i", "em"):
                d["font-style"] = "italic"
            if tag == "u":
                d["text-decoration"] = "underline"
            self.stack.append((tag, d))

    def handle_endtag(self, tag):
        if tag in ("style", "script", "title"):
            self.skip = max(0, self.skip - 1)
            return
        if tag in ("ul", "ol"):
            self.end_block()
            if self.lists:
                self.lists.pop()
            return
        if tag in self.BLOCKS:
            if tag == "p" and self.cur is not None and self.cur.lst:
                return
            self.end_block()
            return
        if tag in self.INLINE:
            for k in range(len(self.stack) - 1, -1, -1):
                if self.stack[k][0] == tag:
                    del self.stack[k]
                    break

    def handle_data(self, data):
        if self.skip:
            return
        self.add(data.replace("\xa0", " ").replace("\n", " "))


def parse_html(html: str):
    p = DocParser(parse_css(html))
    p.feed(html)
    p.end_block()
    blocks = p.blocks
    while blocks and not blocks[0].text.strip():
        blocks.pop(0)
    while blocks and not blocks[-1].text.strip():
        blocks.pop()
    return blocks


# --------------------------------------------------------------------------
# Perencana: ubah blok dokumen -> urutan aksi (ketik teks / hotkey format)
# --------------------------------------------------------------------------


def plan(blocks, base_size: float, mac: bool, base_spacing=(1.15, 0.0, 0.0),
         break_every=None, break_level=1, chapter_re=None):
    """Hasil: list aksi ("text", str) atau ("hot", (modifier...), tombol)."""
    M = Key.cmd if mac else Key.ctrl
    base = snap_size(base_size)
    st = dict(style=0, align="left", size=base, b=False, i=False, u=False, first=0, left=0,
              spc=tuple(base_spacing))
    out = []

    def hot(mods, key, n=1):
        for _ in range(n):
            out.append(("hot", tuple(mods), key))

    def text(s):
        if not s:
            return
        if out and out[-1][0] == "text":
            out[-1] = ("text", out[-1][1] + s)
        else:
            out.append(("text", s))

    list_kind = ""
    list_depth = 0
    n = len(blocks)
    chapters_seen = 0
    next_break = random.randint(*break_every) if break_every else None

    for idx, b in enumerate(blocks):
        nxt = blocks[idx + 1] if idx + 1 < n else None
        empty = not b.text.strip()

        # ---------- istirahat setelah N bab ----------
        if break_every and not empty and not b.lst:
            is_chapter = (1 <= b.heading <= break_level) or bool(
                chapter_re and chapter_re.search(b.text.strip()))
            if is_chapter:
                if chapters_seen == next_break:
                    out.append(("break", chapters_seen))
                    next_break += random.randint(*break_every)
                chapters_seen += 1

        # ---------- item list ----------
        if b.lst and not empty:
            if list_kind != b.lst:
                if st["style"] != 0:
                    hot((M, Key.alt), "0")
                    st["style"], st["size"] = 0, base
                text("- " if b.lst == "ul" else "1. ")  # autoformat Docs -> bullet/nomor
                list_kind, list_depth = b.lst, 1
            if b.depth > list_depth:
                hot((), Key.tab, b.depth - list_depth)
            elif b.depth < list_depth:
                hot((Key.shift,), Key.tab, list_depth - b.depth)
            list_depth = b.depth
        # ---------- paragraf biasa ----------
        elif not empty:
            list_kind = ""
            if b.heading != st["style"]:
                hot((M, Key.alt), str(b.heading))  # Ctrl+Alt+0..6
                st["style"] = b.heading
                st["size"] = base
                st["spc"] = None  # spasi bisa ikut berubah mengikuti style
            # Spasi diatur DULUAN (dialog bisa mengganggu Tab); indentasi paling akhir
            tgt = (round(b.line or base_spacing[0], 2), round(b.before, 1), round(b.after, 1))
            if st["spc"] != tgt:
                out.append(("spacing",) + tgt)
                st["spc"] = tgt
            if b.align != st["align"]:
                hot((M, Key.shift), ALIGN_KEYS[b.align])
                st["align"] = b.align
            tl = int(b.left / INDENT_STEP + 0.5)
            tf = int(b.first / INDENT_STEP + 0.5)
            if tl != st["left"]:
                hot((M,), "]" if tl > st["left"] else "[", abs(tl - st["left"]))
                st["left"] = tl
            if tf:
                hot((), Key.tab, tf)
            st["first"] = tf

        # ---------- isi (run) ----------
        for r in b.runs:
            if not r.text:
                continue
            for k, want in (("b", r.b), ("i", r.i), ("u", r.u)):
                if st[k] != want:
                    hot((M,), k)
                    st[k] = want
            if b.heading == 0 and r.size:
                target = snap_size(r.size)
                if target != st["size"]:
                    steps = SIZES.index(target) - SIZES.index(st["size"])
                    hot((M, Key.shift), "." if steps > 0 else ",", abs(steps))
                    st["size"] = target
            text(r.text)

        # ---------- akhir blok ----------
        if b.lst and not empty:
            if nxt is None:
                pass
            elif nxt.lst == b.lst and nxt.text.strip():
                text("\n")
            else:
                text("\n" * (1 + list_depth))  # keluar dari list
                list_kind, list_depth = "", 0
                st["first"] = st["left"] = 0
                st["style"] = 0
        elif nxt is not None:
            text("\n")
            if b.heading:  # setelah Enter, Docs kembali ke teks normal
                st["style"] = 0
                st["size"] = base
                st["spc"] = None
    return out


# --------------------------------------------------------------------------
# Sumber teks
# --------------------------------------------------------------------------


def fetch_gdoc(url_or_id: str, fmt: str = "html") -> str:
    import requests

    m = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url_or_id)
    doc_id = m.group(1) if m else url_or_id.strip()
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format={fmt}"
    r = requests.get(export_url, timeout=30)
    if r.status_code != 200 or "accounts.google.com" in r.url:
        raise RuntimeError(
            "Gagal membaca Google Docs. Pastikan sharing diatur ke "
            "'Anyone with the link' (Viewer), atau pakai --file / --clipboard."
        )
    r.encoding = "utf-8"
    return r.text


def normalize(text: str) -> str:
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip("\n")


# --------------------------------------------------------------------------
# Mesin pengetikan
# --------------------------------------------------------------------------


class Typist:
    def __init__(self, cfg: Config):
        require_pynput()
        self.cfg = cfg
        self.kb = Controller()
        self.stop = threading.Event()
        self.paused = threading.Event()
        self.speed = 1.0     # pengali delay acak (momentum): <1 cepat, >1 lambat
        self.clock = 0.0     # waktu "aktif" (detik) untuk gelombang WPM
        self.wpm_adj = 0.0   # penyesuaian live (hotkey)
        self.typo_adj = 0.0
        self.prev = ""
        self.words_since_think = 0
        self.next_think = random.randint(*cfg.think_every)

    # ---- kontrol dasar ---------------------------------------------------

    def sleep(self, secs: float):
        self.clock += secs
        end = time.monotonic() + secs
        while True:
            if self.stop.is_set():
                raise StopTyping
            if self.paused.is_set():
                time.sleep(0.1)
                end += 0.1  # waktu pause tidak dihitung
                continue
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.05, remaining))

    def press(self, key):
        self.kb.press(key)
        self.kb.release(key)

    def hotkey(self, mods, key):
        for m in mods:
            self.kb.press(m)
        try:
            self.press(key)
        finally:
            for m in reversed(mods):
                self.kb.release(m)

    def type_char(self, ch: str):
        if ch == "\n":
            self.press(Key.enter)
        elif ch == "\v":  # line break dalam paragraf
            self.hotkey((Key.shift,), Key.enter)
        elif ch == "\t":
            self.press(Key.tab)
        else:
            try:
                self.kb.type(ch)
            except Exception:
                self._paste_fallback(ch)

    def _paste_fallback(self, ch: str):
        try:
            import pyperclip

            pyperclip.copy(ch)
            mod = Key.cmd if sys.platform == "darwin" else Key.ctrl
            with self.kb.pressed(mod):
                self.kb.press("v")
                self.kb.release("v")
        except Exception:
            pass  # karakter tak bisa diketik, lewati

    def backspace(self, n: int):
        for _ in range(n):
            self.sleep(random.uniform(0.04, 0.09))
            self.press(Key.backspace)

    # ---- gelombang WPM & typo -------------------------------------------

    def wave(self) -> float:
        """0..1. 1 = paling cepat, 0 = paling lambat. Halus (cosinus)."""
        phase = 2 * math.pi * self.clock / max(1.0, self.cfg.wave_period)
        if not self.cfg.start_fast:
            phase += math.pi
        return (1 + math.cos(phase)) / 2

    def cur_wpm(self) -> float:
        lo, hi = self.cfg.wpm
        return max(5.0, lo + (hi - lo) * self.wave() + self.wpm_adj)

    def cur_typo(self) -> float:
        lo, hi = self.cfg.typo_rate
        return max(0.0, lo + (hi - lo) * self.wave() + self.typo_adj)

    # ---- model tempo -----------------------------------------------------

    def char_delay(self, prev: str, ch: str) -> float:
        base = 60.0 / (self.cur_wpm() * 5)
        d = base * self.speed * random.lognormvariate(0, 0.28)
        if ch == " ":
            d *= 0.9
        if ch.isupper() or ch in HARD_CHARS:
            d *= 1.35
        if prev and (prev + ch).lower() in FAST_BIGRAMS:
            d *= 0.78
        return max(0.015, d)

    def drift(self):
        """Variasi acak kecil antar kata (momentum), di atas gelombang WPM."""
        self.speed *= random.uniform(0.92, 1.08)
        self.speed += (1.0 - self.speed) * 0.12  # tarik balik ke normal
        self.speed = min(1.25, max(0.8, self.speed))

    # ---- typo ------------------------------------------------------------

    def typo_prob(self) -> float:
        return self.cur_typo() * (1.5 if self.speed < 0.9 else 1.0)

    @staticmethod
    def make_typo(text: str, i: int):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        kind = random.choices(
            ["neighbor", "transpose", "double", "skip"], [55, 15, 15, 15]
        )[0]
        if kind == "transpose" and not (nxt.isalpha() and nxt.lower() != ch.lower()):
            kind = "neighbor"
        if kind == "neighbor" and ch.lower() not in NEIGHBORS:
            kind = "double"

        if kind == "neighbor":
            w = random.choice(NEIGHBORS[ch.lower()])
            return (w.upper() if ch.isupper() else w), 1, kind
        if kind == "transpose":
            return nxt + ch, 2, kind
        if kind == "double":
            return ch * 2, 1, kind
        return "", 1, "skip"

    # ---- mengetik teks ---------------------------------------------------

    def type_text(self, text: str):
        cfg = self.cfg
        n = len(text)
        i = 0
        no_typo_at = -1

        while i < n:
            ch = text[i]

            # ---------- typo + koreksi ----------
            if i != no_typo_at and ch.isalpha() and random.random() < self.typo_prob():
                wrong, consumed, kind = self.make_typo(text, i)
                k = random.choices([0, 1, 2, 3], [30, 30, 25, 15])[0]
                if kind == "skip":
                    k = max(k, 1)
                tail = text[i + consumed : i + consumed + k]
                for sep in ("\n", "\v"):
                    if sep in tail:
                        tail = tail.split(sep)[0]

                if len(wrong) + len(tail) == 0:
                    no_typo_at = i
                    continue

                p = self.prev
                for c in wrong + tail:
                    self.sleep(self.char_delay(p, c))
                    self.type_char(c)
                    p = c

                self.sleep(random.uniform(*cfg.notice_pause))
                self.backspace(len(wrong) + len(tail))
                self.sleep(random.uniform(0.1, 0.3))
                no_typo_at = i
                continue  # ketik ulang karakter yang benar dari i

            # ---------- karakter normal ----------
            self.sleep(self.char_delay(self.prev, ch))
            self.type_char(ch)

            nxt = text[i + 1] if i + 1 < n else "\n"
            if ch == "\n":
                self.sleep(random.uniform(*cfg.para_pause))
            elif ch in ".!?" and nxt.isspace():
                self.sleep(random.uniform(*cfg.sentence_pause))
            elif ch in ",;:" and random.random() < 0.5:
                self.sleep(random.uniform(*cfg.comma_pause))

            # batas kata
            if ch in (" ", "\n") and self.prev not in (" ", "\n", ""):
                self.words_since_think += 1
                self.drift()
                if random.random() < 0.02:  # ragu sebentar
                    self.sleep(random.uniform(0.5, 1.2))
                if self.words_since_think >= self.next_think:
                    pause = random.uniform(*cfg.think_pause)
                    if random.random() < 0.15:
                        pause *= 2  # sesekali mikir lebih lama
                    self.sleep(pause)
                    self.words_since_think = 0
                    self.next_think = random.randint(*cfg.think_every)

            self.prev = ch
            i += 1

    # ---- spasi baris/paragraf (dialog Custom spacing) -------------------

    def apply_spacing(self, line, before, after):
        M = Key.cmd if self.cfg.mac else Key.ctrl

        def num(v):
            t = f"{v:g}"
            return t.replace(".", ",") if self.cfg.decimal_comma else t

        self.sleep(random.uniform(0.5, 1.0))
        self.hotkey((Key.alt,), "/")                      # Alt+/ = cari menu
        self.sleep(random.uniform(0.7, 1.1))
        self.kb.type(self.cfg.spacing_menu)
        self.sleep(random.uniform(0.8, 1.2))
        self.press(Key.enter)
        self.sleep(random.uniform(1.0, 1.6))              # tunggu dialog muncul
        for k, val in enumerate((line, before, after)):   # Line | Before | After
            self.hotkey((M,), "a")
            self.sleep(0.1)
            self.kb.type(num(val))
            self.sleep(random.uniform(0.3, 0.5))
            if k < 2:
                self.press(Key.tab)
                self.sleep(random.uniform(0.25, 0.45))
        self.sleep(random.uniform(0.6, 0.9))              # beri waktu Docs memvalidasi input
        # Enter di dalam field TIDAK menekan Apply -> pindah fokus ke tombol Apply dulu
        for _ in range(self.cfg.apply_tabs):
            self.press(Key.tab)
            self.sleep(random.uniform(0.15, 0.3))
        self.press(Key.enter)                             # tekan Apply
        self.sleep(random.uniform(0.8, 1.2))

    # ---- istirahat (menunggu F9 manual) ---------------------------------

    def take_break(self, chapters_done):
        print(f"\n[ISTIRAHAT] {chapters_done} bab selesai. Tekan F9 untuk melanjutkan.\a")
        self.paused.set()
        self.sleep(0.1)  # tertahan di sini sampai F9 ditekan (atau ESC)
        for s in range(self.cfg.resume_delay, 0, -1):
            print(f"Lanjut dalam {s}... (klik dokumen tujuan)  ", end="\r", flush=True)
            self.sleep(1)
        print(" " * 60, end="\r")
        if self.cfg.mac:
            self.hotkey((Key.cmd,), Key.down)   # ke akhir dokumen
        else:
            self.hotkey((Key.ctrl,), Key.end)
        self.sleep(random.uniform(0.3, 0.8))

    # ---- loop utama ------------------------------------------------------

    def run(self, actions):
        for act in actions:
            if act[0] == "text":
                self.type_text(act[1])
            elif act[0] == "spacing":
                self.apply_spacing(*act[1:])
            elif act[0] == "break":
                self.take_break(act[1])
            else:
                _, mods, key = act
                self.sleep(random.uniform(0.25, 0.7))  # "mencari" tombol/shortcut
                self.hotkey(mods, key)
                self.sleep(random.uniform(0.1, 0.3))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_range(s, cast=float):
    """'60' -> (60,60) ; '40-75' -> (40,75)."""
    vals = [cast(p) for p in str(s).split("-") if p.strip() != ""]
    if not vals:
        raise ValueError("rentang kosong")
    if len(vals) == 1:
        vals = vals * 2
    return (min(vals), max(vals))


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

    # ---- ambil sumber -> aksi ----
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
        mac=args.mac,
        spacing_menu=args.spacing_menu,
        # Otomatis pakai koma desimal bila UI Docs berbahasa Indonesia ("Spasi kustom")
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


if __name__ == "__main__":
    main()